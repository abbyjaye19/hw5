import { useEffect, useRef } from 'react'
import { AGENTS, isAgent, isOutputTool, prettyTool } from '../agents'
import type { AgentEvent } from '../types'

function time(ts: string) {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function brief(value: unknown, max = 160): string {
  if (value == null) return ''
  if (typeof value === 'string') return value.length > max ? value.slice(0, max) + '…' : value
  if (Array.isArray(value)) return `${value.length} row${value.length === 1 ? '' : 's'}`
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
      .filter(([, v]) => v !== null && typeof v !== 'object')
      .slice(0, 5)
      .map(([k, v]) => `${k}: ${v}`)
    return brief(entries.join(' · '), max)
  }
  return String(value)
}

function argsText(args: unknown): string {
  if (!args) return ''
  const obj = typeof args === 'string' ? safeParse(args) : args
  if (obj && typeof obj === 'object') {
    return Object.entries(obj as Record<string, unknown>)
      .filter(([k]) => !['requested_by', 'author', 'updated_by'].includes(k))
      .map(([k, v]) => `${k}=${typeof v === 'string' && v.length > 40 ? v.slice(0, 40) + '…' : v}`)
      .join(', ')
  }
  return String(args)
}

function safeParse(s: string): unknown {
  try {
    return JSON.parse(s)
  } catch {
    return s
  }
}

function who(name: string) {
  return isAgent(name) ? AGENTS[name].title : name
}

/** The minutes: a live, formal record of who said what and which tools were consulted. */
export function Minutes({ events, running }: { events: AgentEvent[]; running: boolean }) {
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => {
    end.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [events.length])

  const shown = events.filter((e) => !['model_request', 'tool_call'].includes(e.event))

  return (
    <section className="panel minutes" aria-label="Meeting minutes">
      <header className="panel-head">
        <span className="eyebrow">Minutes of the Meeting</span>
        <h2>Proceedings</h2>
        {running && <span className="recording">● Recording</span>}
      </header>
      <div className="minutes-scroll">
        {shown.length === 0 && (
          <p className="minutes-empty">
            No proceedings yet. Select a matter from the docket and convene the team. Every word and every tool the
            agents consult will be recorded here.
          </p>
        )}
        {shown.map((e) => {
          const voice = isAgent(e.agent) ? AGENTS[e.agent].voice : 'voice-human'
          const indent = Math.min(e.depth ?? 0, 2)
          return (
            <article key={e.id} className={`entry ${e.event} ${voice} indent-${indent}`}>
              <div className="entry-meta">
                <span className="entry-time">{time(e.ts)}</span>
                <span className="entry-who">{who(e.agent)}</span>
              </div>
              <div className="entry-body">
                {e.event === 'run_start' && (
                  <p className="entry-line">
                    <em>{e.agent === 'boss' ? 'opens the matter.' : 'takes the brief:'}</em>{' '}
                    {e.agent !== 'boss' && <span className="quote">“{brief(e.task, 260)}”</span>}
                  </p>
                )}
                {e.event === 'model_response' && (
                  <>
                    {e.said && <p className="entry-line said">{e.said}</p>}
                    {e.tool_calls && e.tool_calls.length > 0 && (
                      <div className="chips">
                        {e.tool_calls.map((c, i) =>
                          c.tool === 'delegate' || isOutputTool(c.tool) ? null : (
                            <span key={i} className="chip" title={argsText(c.args)}>
                              ⚙ {prettyTool(c.tool)}
                              <small>{argsText(c.args)}</small>
                            </span>
                          ),
                        )}
                      </div>
                    )}
                  </>
                )}
                {e.event === 'tool_result' && (
                  <p className="entry-line result">
                    <span className="result-tool">↳ {prettyTool(e.tool || '')}</span> {brief(e.result)}
                  </p>
                )}
                {e.event === 'delegation' && (
                  <p className="entry-line delegation">
                    <span className="baton">⟶ {who(e.to_agent || '')}</span>
                    <span className="quote">“{brief(e.task, 260)}”</span>
                  </p>
                )}
                {e.event === 'run_end' && (
                  <p className="entry-line filed">
                    <strong>Report filed.</strong> {brief(String(e.output?.summary ?? e.output?.decision ?? ''), 400)}
                  </p>
                )}
                {(e.event === 'guard_block' || e.event === 'error') && (
                  <p className="entry-line blocked">
                    <strong>{e.event === 'error' ? 'Error' : 'Guardrail'}:</strong>{' '}
                    {brief(String(e.details?.reason ?? e.details?.error ?? ''), 300)}
                  </p>
                )}
                {(e.event === 'human_approval' || e.event === 'human_rejection') && (
                  <p className="entry-line human">
                    <strong>{e.event === 'human_approval' ? 'Signed' : 'Declined'}</strong> request #
                    {String(e.details?.request_id)} · {brief((e.details?.result as Record<string, unknown>)?.error ?? 'recorded')}
                  </p>
                )}
                {e.event === 'db_reset' && <p className="entry-line human">The books were reset to the opening ledger.</p>}
              </div>
            </article>
          )
        })}
        <div ref={end} />
      </div>
    </section>
  )
}
