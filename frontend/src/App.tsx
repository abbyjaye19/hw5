import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { activityByAgent, allDelegations, liveDelegations } from './agents'
import { api } from './api'
import { Boardroom } from './components/Boardroom'
import { Docket } from './components/Docket'
import { Minutes } from './components/Minutes'
import { Summary } from './components/Summary'
import { Treasury } from './components/Treasury'
import type { AgentEvent, CashPosition, Draft, PaymentRequest, RunInfo, Ticket, TicketOutcome } from './types'

const POLL_MS = 1200

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [cash, setCash] = useState<CashPosition | null>(null)
  const [requests, setRequests] = useState<PaymentRequest[]>([])
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [runs, setRuns] = useState<Record<number, RunInfo>>({})
  // ?ticket=101 opens the board on that ticket (used for screenshots / sharing a link).
  const [selectedId, setSelectedId] = useState<number | null>(() => {
    const t = Number(new URLSearchParams(window.location.search).get('ticket'))
    return Number.isFinite(t) && t > 0 ? t : null
  })
  const [signer, setSigner] = useState(() => localStorage.getItem('cc-signer') || '')
  const [notices, setNotices] = useState<Record<number, string>>({})
  const [banner, setBanner] = useState<string | null>(null)
  const [online, setOnline] = useState<boolean | null>(null)
  const [model, setModel] = useState('')
  const lastId = useRef(-1)

  const refreshBoard = useCallback(async () => {
    const [t, c, p, d] = await Promise.all([api.tickets(), api.cash(), api.payments(), api.drafts()])
    setTickets(t)
    setCash(c)
    setRequests(p)
    setDrafts(d)
  }, [])

  const pullEvents = useCallback(async () => {
    const r = await api.events(lastId.current)
    if (r.events.length) {
      lastId.current = r.events[r.events.length - 1].id
      // De-duplicate by id: overlapping polls (e.g. React StrictMode's double effect) can fetch the same events.
      setEvents((prev) => {
        const seen = new Set(prev.map((e) => e.id))
        return [...prev, ...r.events.filter((e) => !seen.has(e.id))]
      })
    } else if (r.last_id < lastId.current) {
      lastId.current = r.last_id // audit file replaced; resync
    }
  }, [])

  // First load.
  useEffect(() => {
    ;(async () => {
      try {
        const h = await api.health()
        setOnline(true)
        setModel(h.model)
        await Promise.all([refreshBoard(), pullEvents()])
      } catch {
        setOnline(false)
      }
    })()
  }, [refreshBoard, pullEvents])

  useEffect(() => {
    if (selectedId === null && tickets.length) setSelectedId(tickets.find((t) => t.state === 'open')?.id ?? tickets[0].id)
  }, [tickets, selectedId])

  const activeRun = useMemo(
    () => Object.values(runs).find((r) => r.status === 'queued' || r.status === 'running') ?? null,
    [runs],
  )

  // Live polling while a run is in progress.
  useEffect(() => {
    if (!activeRun) return
    let alive = true
    const id = setInterval(async () => {
      try {
        const [run] = await Promise.all([api.run(activeRun.run_id), pullEvents()])
        if (!alive) return
        setRuns((r) => ({ ...r, [run.ticket_id]: run }))
        const [c, p] = await Promise.all([api.cash(), api.payments()])
        setCash(c)
        setRequests(p)
        if (run.status === 'done' || run.status === 'error') {
          await refreshBoard()
          await pullEvents()
          if (run.status === 'error') setBanner(`Matter ${run.ticket_id}: ${run.error}`)
        }
      } catch (err) {
        setBanner(String(err))
      }
    }, POLL_MS)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [activeRun, pullEvents, refreshBoard])

  // Events since the most recent books reset only.
  const resetAfter = useMemo(() => {
    const r = [...events].reverse().find((e) => e.event === 'db_reset')
    return r ? r.id : -1
  }, [events])

  const selected = tickets.find((t) => t.id === selectedId) ?? null

  const currentRunId = useMemo(() => {
    if (selectedId === null) return null
    if (runs[selectedId]) return runs[selectedId].run_id
    const mine = events.filter((e) => e.id > resetAfter && e.ticket_id === selectedId)
    return mine.length ? mine[mine.length - 1].run_id : null
  }, [events, runs, selectedId, resetAfter])

  const runEvents = useMemo(
    () => (currentRunId ? events.filter((e) => e.run_id === currentRunId) : []),
    [events, currentRunId],
  )
  const activity = useMemo(() => activityByAgent(runEvents), [runEvents])
  const live = useMemo(() => liveDelegations(runEvents), [runEvents])
  const past = useMemo(() => allDelegations(runEvents), [runEvents])

  const runForSummary: RunInfo | null = useMemo(() => {
    if (selectedId === null) return null
    const r = runs[selectedId]
    if (r) return r
    const bossEnd = [...runEvents].reverse().find((e) => e.agent === 'boss' && e.event === 'run_end')
    if (!bossEnd) return null
    return {
      run_id: bossEnd.run_id,
      ticket_id: selectedId,
      status: 'done',
      started_at: runEvents[0]?.ts ?? '',
      finished_at: bossEnd.ts,
      outcome: bossEnd.output as unknown as TicketOutcome,
      error: null,
    }
  }, [runs, runEvents, selectedId])

  const inSession = !!activeRun && activeRun.ticket_id === selectedId

  async function convene() {
    if (!selected) return
    setBanner(null)
    try {
      const run = await api.runTicket(selected.id)
      setRuns((r) => ({ ...r, [selected.id]: run }))
    } catch (err) {
      setBanner(String(err))
    }
  }

  async function approve(id: number) {
    setNotices((n) => ({ ...n, [id]: '' }))
    try {
      await api.approve(id, signer.trim())
    } catch (err) {
      setNotices((n) => ({ ...n, [id]: `Refused: ${err instanceof Error ? err.message : err}` }))
    }
    await Promise.all([refreshBoard(), pullEvents()])
  }

  async function reject(id: number) {
    try {
      await api.reject(id, signer.trim(), 'Declined at the desk')
    } catch (err) {
      setNotices((n) => ({ ...n, [id]: String(err) }))
    }
    await Promise.all([refreshBoard(), pullEvents()])
  }

  async function resetBooks() {
    if (!confirm('Reset the books? This restores the original database (the audit trail is kept).')) return
    try {
      await api.reset()
      setRuns({})
      setNotices({})
      setBanner(null)
      await Promise.all([refreshBoard(), pullEvents()])
    } catch (err) {
      setBanner(String(err))
    }
  }

  function onSigner(s: string) {
    setSigner(s)
    localStorage.setItem('cc-signer', s)
  }

  const ticketDrafts = drafts.filter((d) => d.ticket_id === selectedId)

  return (
    <div className="desk">
      <header className="masthead">
        <div className="brand">
          <span className="crest large">CC</span>
          <div>
            <span className="eyebrow">Est. on Chapel Street</span>
            <h1>Campus Customs</h1>
            <span className="tagline">Operations Desk · Multi-Agent Board</span>
          </div>
        </div>
        <div className="masthead-right">
          <span className="desk-date">
            Desk date <b>{cash?.as_of ?? '—'}</b>
          </span>
          <span className={`status-pill ${online ? 'ok' : online === false ? 'bad' : ''}`}>
            {online === null ? 'Connecting…' : online ? `Backend online · ${model}` : 'Backend offline (start uvicorn on :8000)'}
          </span>
          <button className="btn silver" onClick={resetBooks} disabled={!!activeRun}>
            Reset the books
          </button>
        </div>
      </header>

      {banner && (
        <div className="banner" role="alert">
          {banner}
          <button onClick={() => setBanner(null)} aria-label="Dismiss">
            ×
          </button>
        </div>
      )}

      <main className="layout">
        <Docket tickets={tickets} selectedId={selectedId} runningId={activeRun?.ticket_id ?? null} onSelect={setSelectedId} />

        <div className="centre">
          {selected && (
            <div className="matter">
              <div>
                <span className="eyebrow">Matter before the board</span>
                <h2>
                  No. {selected.id} · {selected.subject}
                </h2>
                <p className="matter-notes">{selected.notes?.split('\n')[0]}</p>
              </div>
              <button
                className="btn gold large"
                onClick={convene}
                disabled={!!activeRun || selected.state === 'resolved'}
                title={selected.state === 'resolved' ? 'Resolved; reset the books to run it again' : ''}
              >
                {inSession ? 'In session…' : selected.state === 'resolved' ? 'Resolved' : 'Convene the team'}
              </button>
            </div>
          )}
          <Boardroom
            activity={activity}
            live={live}
            past={past}
            inSession={inSession}
            ticketLabel={selected ? `Matter No. ${selected.id}` : ''}
          />
          <Minutes events={runEvents} running={inSession} />
          <Summary ticket={selected} run={inSession ? null : runForSummary} activity={activity} drafts={ticketDrafts} />
        </div>

        <Treasury
          cash={cash}
          requests={requests}
          signer={signer}
          onSigner={onSigner}
          onApprove={approve}
          onReject={reject}
          notices={notices}
        />
      </main>

      <footer className="colophon">
        Agents prepare · humans sign · every step recorded in the audit trail
      </footer>
    </div>
  )
}
