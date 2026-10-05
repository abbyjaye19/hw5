import { AGENTS, prettyTool, type AgentActivity } from '../agents'
import type { AgentName, Draft, RunInfo, Ticket } from '../types'

interface Props {
  ticket: Ticket | null
  run: RunInfo | null
  activity: Record<AgentName, AgentActivity>
  drafts: Draft[]
}

/** After a run: the Boss's resolution, a short "what each agent did" brief, and any customer draft. */
export function Summary({ ticket, run, activity, drafts }: Props) {
  const outcome = run?.outcome
  const involved = (Object.keys(AGENTS) as AgentName[]).filter((a) => activity[a].state !== 'idle')

  if (!ticket) return null

  return (
    <section className="panel summary" aria-label="Run summary">
      <header className="panel-head">
        <span className="eyebrow">Resolution · Matter No. {ticket.id}</span>
        <h2>{outcome ? 'The Board Has Decided' : run?.status === 'error' ? 'Session Halted' : 'Awaiting Resolution'}</h2>
      </header>

      {run?.status === 'error' && <p className="halt">{run.error}</p>}

      {outcome && (
        <div className="resolution">
          <p className="resolution-text">“{outcome.decision}”</p>
          <div className="resolution-meta">
            <span>Status filed: <b>{outcome.final_status.replace('_', ' ')}</b></span>
            {outcome.payment_request_ids.length > 0 && (
              <span>Cheques drawn: <b>{outcome.payment_request_ids.map((i) => `#${i}`).join(', ')}</b></span>
            )}
            {outcome.draft_ids.length > 0 && <span>Drafts: <b>{outcome.draft_ids.map((i) => `#${i}`).join(', ')}</b></span>}
          </div>
          {outcome.human_next_steps.length > 0 && (
            <div className="next-steps">
              <h3>For your signature</h3>
              <ol>
                {outcome.human_next_steps.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}

      {involved.length > 0 && (
        <div className="briefs">
          {involved.map((a) => {
            const act = activity[a]
            const tools = Object.entries(act.tools)
            return (
              <article key={a} className={`brief ${AGENTS[a].voice}`}>
                <header>
                  <span className="monogram small">{AGENTS[a].monogram}</span>
                  <strong>{AGENTS[a].title}</strong>
                  <span className={`brief-state ${act.state}`}>{act.state === 'done' ? 'Filed' : act.state}</span>
                </header>
                <p>{act.summary || act.line || '—'}</p>
                <footer>
                  {tools.length > 0 && (
                    <span className="brief-tools">
                      {tools.map(([t, n]) => (
                        <span key={t} className="chip small">
                          {prettyTool(t)}
                          {n > 1 ? ` ×${n}` : ''}
                        </span>
                      ))}
                    </span>
                  )}
                  {act.delegatedTo.length > 0 && (
                    <span className="brief-deleg">
                      Briefed: {act.delegatedTo.map((d) => AGENTS[d as AgentName]?.title ?? d).join(' → ')}
                    </span>
                  )}
                </footer>
              </article>
            )
          })}
        </div>
      )}

      {drafts.map((d) => (
        <article key={d.id} className="letter" aria-label={`Draft ${d.id}`}>
          <div className="letterhead">
            <span className="crest small">CC</span>
            <span>
              <strong>Campus Customs</strong>
              <small>Chapel Street · New Haven</small>
            </span>
            <span className="draft-stamp">Draft · not sent</span>
          </div>
          <p className="letter-to">To: {d.recipient}</p>
          <p className="letter-subject">Re: {d.subject}</p>
          <div className="letter-body">{d.body}</div>
          <p className="letter-foot">Drafted by {AGENTS[d.author as AgentName]?.title ?? d.author} · #{d.id}</p>
        </article>
      ))}
    </section>
  )
}
