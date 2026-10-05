import type { Ticket } from '../types'

const TYPE_LABEL: Record<string, string> = {
  customer_order: 'Customer Order',
  rent_notice: 'Rent Notice',
  price_override: 'Price Override',
}

interface Props {
  tickets: Ticket[]
  selectedId: number | null
  runningId: number | null
  onSelect: (id: number) => void
}

function detail(t: Ticket): string {
  if (t.sku) return `${t.qty ?? '?'} × ${t.sku} · size ${t.size}`
  if (t.lease_id) return `Lease #${t.lease_id}`
  if (t.invoice_id) return `Invoice #${t.invoice_id}`
  return ''
}

/** The case docket: each ticket is a filed folder; resolved ones get a gold seal. */
export function Docket({ tickets, selectedId, runningId, onSelect }: Props) {
  return (
    <section className="panel docket" aria-label="Ticket docket">
      <header className="panel-head">
        <span className="eyebrow">The Docket</span>
        <h2>Open Matters</h2>
      </header>
      <ol className="docket-list">
        {tickets.map((t) => {
          const running = runningId === t.id
          const state = running ? 'running' : t.state
          return (
            <li key={t.id}>
              <button
                className={`folder ${state}${selectedId === t.id ? ' selected' : ''}`}
                onClick={() => onSelect(t.id)}
                aria-pressed={selectedId === t.id}
              >
                <span className="folder-tab">No. {t.id}</span>
                <span className="folder-body">
                  <span className="folder-type">{TYPE_LABEL[t.type] ?? t.type}</span>
                  <span className="folder-subject">{t.subject}</span>
                  <span className="folder-from">{t.requester}</span>
                  <span className="folder-detail">{detail(t)}</span>
                </span>
                <span className={`seal ${state}`} aria-label={state}>
                  {state === 'resolved' ? (
                    <svg viewBox="0 0 60 60" aria-hidden>
                      <circle cx="30" cy="30" r="27" className="seal-ring" />
                      <circle cx="30" cy="30" r="21" className="seal-inner" />
                      <path d="M20 31 l7 7 l14 -16" className="seal-check" />
                    </svg>
                  ) : (
                    <span className="seal-text">{state === 'running' ? 'In session' : 'Open'}</span>
                  )}
                </span>
              </button>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
