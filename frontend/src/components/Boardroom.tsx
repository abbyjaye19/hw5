import { AGENTS, type AgentActivity } from '../agents'
import type { AgentName } from '../types'

// Seat positions (percent of the room) around an oval table seen from above.
const SEATS: Record<AgentName, { x: number; y: number }> = {
  boss: { x: 50, y: 13 },
  inventory: { x: 14, y: 45 },
  accounting: { x: 86, y: 45 },
  facilities: { x: 26, y: 84 },
  customer_service: { x: 74, y: 84 },
}

interface Props {
  activity: Record<AgentName, AgentActivity>
  live: { from: AgentName; to: AgentName }[]
  past: { from: AgentName; to: AgentName }[]
  inSession: boolean
  ticketLabel: string
}

/** The boardroom: Boss at the head, specialists around the table. Gold lines show delegations. */
export function Boardroom({ activity, live, past, inSession, ticketLabel }: Props) {
  const key = (d: { from: AgentName; to: AgentName }) => `${d.from}-${d.to}`
  const liveKeys = new Set(live.map(key))
  const pastUnique = [...new Map(past.map((d) => [key(d), d])).values()]

  return (
    <section className="panel boardroom" aria-label="Agent boardroom">
      <header className="panel-head">
        <span className="eyebrow">The Boardroom</span>
        <h2>{inSession ? 'In Session' : 'Adjourned'}</h2>
        <span className={`session-light${inSession ? ' on' : ''}`} aria-hidden />
      </header>

      <div className="room">
        <svg className="room-svg" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden>
          <defs>
            <radialGradient id="tableWood" cx="50%" cy="40%" r="70%">
              <stop offset="0%" stopColor="#173a66" />
              <stop offset="100%" stopColor="#0e2848" />
            </radialGradient>
            <linearGradient id="goldLine" x1="0" x2="1">
              <stop offset="0%" stopColor="#e7cf8a" />
              <stop offset="100%" stopColor="#b08a33" />
            </linearGradient>
          </defs>
          <ellipse cx="50" cy="50" rx="30" ry="25" fill="url(#tableWood)" stroke="#c9a54b" strokeWidth="0.5" />
          <ellipse cx="50" cy="50" rx="27.5" ry="22.5" fill="none" stroke="#c9a54b" strokeOpacity="0.35" strokeWidth="0.25" />
          {pastUnique.map((d) => {
            const a = SEATS[d.from]
            const b = SEATS[d.to]
            const isLive = liveKeys.has(key(d))
            return (
              <line
                key={key(d)}
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                className={`wire${isLive ? ' live' : ''}`}
                vectorEffect="non-scaling-stroke"
              />
            )
          })}
        </svg>

        <div className="table-centre">
          <span className="crest">CC</span>
          <span className="table-caption">{ticketLabel}</span>
        </div>

        {(Object.keys(SEATS) as AgentName[]).map((name) => {
          const meta = AGENTS[name]
          const act = activity[name]
          const seat = SEATS[name]
          return (
            <div
              key={name}
              className={`seat ${act.state} ${name === 'boss' ? 'chair' : ''}`}
              style={{ left: `${seat.x}%`, top: `${seat.y}%` }}
            >
              <div className="nameplate">
                <span className="monogram">{meta.monogram}</span>
                <span className="plate-text">
                  <strong>{meta.title}</strong>
                  <small>{meta.role}</small>
                </span>
                {act.state === 'working' && <span className="quill" aria-label="working" />}
                {act.state === 'done' && <span className="tick" aria-label="done">✓</span>}
                {act.state === 'alert' && <span className="alert-dot" aria-label="alert">!</span>}
              </div>
              {act.line && act.state !== 'idle' && <p className={`speech ${meta.voice}`}>{act.line}</p>}
            </div>
          )
        })}
      </div>
    </section>
  )
}
