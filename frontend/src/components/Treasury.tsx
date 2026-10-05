import { useEffect, useRef, useState } from 'react'
import { AGENTS } from '../agents'
import type { AgentName, CashPosition, PaymentRequest } from '../types'

const usd = (n: number) => n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

const ONES = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve',
  'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
const TENS = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
function words(n: number): string {
  if (n < 20) return ONES[n]
  if (n < 100) return TENS[Math.floor(n / 10)] + (n % 10 ? '-' + ONES[n % 10] : '')
  if (n < 1000) return ONES[Math.floor(n / 100)] + ' Hundred' + (n % 100 ? ' ' + words(n % 100) : '')
  return words(Math.floor(n / 1000)) + ' Thousand' + (n % 1000 ? ' ' + words(n % 1000) : '')
}
const amountInWords = (amt: number) => {
  const dollars = Math.floor(amt)
  const cents = Math.round((amt - dollars) * 100)
  return `${words(dollars) || 'Zero'} and ${String(cents).padStart(2, '0')}/100 Dollars`
}

const KIND: Record<string, string> = { invoice: 'Vendor invoice', rent: 'Rent', purchase_order: 'Purchase order' }

/** Smoothly count from the old balance to the new one so a payment visibly "drains" the account. */
function useCountUp(target: number) {
  const [shown, setShown] = useState(target)
  const from = useRef(target)
  useEffect(() => {
    const start = performance.now()
    const a = from.current
    let raf = 0
    const tick = (t: number) => {
      const k = Math.min(1, (t - start) / 900)
      const eased = 1 - Math.pow(1 - k, 3)
      setShown(a + (target - a) * eased)
      if (k < 1) raf = requestAnimationFrame(tick)
      else from.current = target
    }
    raf = requestAnimationFrame(tick)
    // Guarantee the final figure even where animation frames are paused (background tabs).
    const settle = setTimeout(() => {
      setShown(target)
      from.current = target
    }, 1000)
    return () => {
      cancelAnimationFrame(raf)
      clearTimeout(settle)
    }
  }, [target])
  return shown
}

interface Props {
  cash: CashPosition | null
  requests: PaymentRequest[]
  signer: string
  onSigner: (s: string) => void
  onApprove: (id: number) => Promise<void>
  onReject: (id: number) => Promise<void>
  notices: Record<number, string>
}

export function Treasury({ cash, requests, signer, onSigner, onApprove, onReject, notices }: Props) {
  const balance = cash?.balance ?? 0
  const shown = useCountUp(balance)
  const [dropped, setDropped] = useState(false)
  const prev = useRef(balance)
  useEffect(() => {
    if (balance < prev.current) {
      setDropped(true)
      const t = setTimeout(() => setDropped(false), 1600)
      prev.current = balance
      return () => clearTimeout(t)
    }
    prev.current = balance
  }, [balance])

  const paid = requests.filter((r) => r.status === 'paid').sort((a, b) => (a.payment_id ?? 0) - (b.payment_id ?? 0))
  const pending = requests.filter((r) => r.status === 'pending')
  const declined = requests.filter((r) => r.status === 'rejected')

  // Rebuild the ledger: opening balance = current + everything paid (cash only goes out).
  const opening = balance + paid.reduce((s, r) => s + r.amount, 0)
  let running = opening
  const ledger = paid.map((r) => {
    running -= r.amount
    return { ...r, after: running }
  })
  const points = [opening, ...ledger.map((l) => l.after)]
  const max = Math.max(opening, 1)

  return (
    <aside className="panel treasury" aria-label="Treasury">
      <header className="panel-head">
        <span className="eyebrow">The Treasury</span>
        <h2>Checking Account</h2>
      </header>

      <div className={`balance${dropped ? ' dropped' : ''}`}>
        <span className="balance-label">Balance as of {cash?.as_of ?? '—'}</span>
        <span className="balance-figure">{usd(shown)}</span>
        {cash && cash.pending_total > 0 && (
          <span className="balance-pending">
            {usd(cash.pending_total)} awaiting signature · {usd(cash.balance_if_all_pending_paid)} if all signed
          </span>
        )}
      </div>

      <div className="flow-chart" aria-label="Cash flow">
        <svg viewBox="0 0 100 40" preserveAspectRatio="none">
          {[10, 20, 30].map((y) => (
            <line key={y} x1="0" x2="100" y1={y} y2={y} className="rule" />
          ))}
          <polyline
            className="flow-line"
            points={points
              .map((v, i) => {
                const x = points.length === 1 ? 100 : (i / (points.length - 1)) * 100
                return `${x},${38 - (v / max) * 34}`
              })
              .join(' ')}
          />
        </svg>
        <span className="flow-caption">Cash flow · outflows only</span>
      </div>

      <div className="ledger">
        <div className="ledger-row head">
          <span>Entry</span>
          <span>Debit</span>
          <span>Balance</span>
        </div>
        <div className="ledger-row opening">
          <span>Opening balance</span>
          <span />
          <span>{usd(opening)}</span>
        </div>
        {ledger.map((l) => (
          <div key={l.id} className="ledger-row">
            <span>
              {KIND[l.kind]} · {l.payee}
              <small>signed by {l.decided_by}</small>
            </span>
            <span className="debit">({usd(l.amount)})</span>
            <span>{usd(l.after)}</span>
          </div>
        ))}
      </div>

      <div className="signature-setup">
        <label htmlFor="signer">Authorised signatory</label>
        <input
          id="signer"
          value={signer}
          onChange={(e) => onSigner(e.target.value)}
          placeholder="Your full name"
          autoComplete="name"
        />
      </div>

      <h3 className="cheques-title">
        Cheques awaiting signature <span className="count">{pending.length}</span>
      </h3>
      {pending.length === 0 && <p className="muted">No payments are waiting for approval.</p>}
      {pending.map((r) => (
        <article key={r.id} className="cheque">
          <div className="cheque-top">
            <span className="cheque-bank">Campus Customs · Checking</span>
            <span className="cheque-no">No. {String(r.id).padStart(4, '0')}</span>
          </div>
          <div className="cheque-pay">
            <span className="cheque-label">Pay to the order of</span>
            <span className="cheque-payee">{r.payee}</span>
            <span className="cheque-amount">{usd(r.amount)}</span>
          </div>
          <div className="cheque-words">{amountInWords(r.amount)}</div>
          <div className="cheque-memo">
            <span>
              <b>Memo</b> {KIND[r.kind]}
              {r.ticket_id ? ` · matter ${r.ticket_id}` : ''}
              {r.kind === 'purchase_order' ? ` · ${r.qty} × ${r.sku} ${r.size}` : ''}
            </span>
            <span className="cheque-reason">{r.reason}</span>
            <span className="cheque-prep">Prepared by {AGENTS[r.requested_by as AgentName]?.title ?? r.requested_by}</span>
          </div>
          {notices[r.id] && <p className="cheque-notice">{notices[r.id]}</p>}
          <div className="cheque-sign">
            <span className="sig-line">{signer || <em>signature</em>}</span>
            <button className="btn gold" disabled={signer.trim().length < 2} onClick={() => onApprove(r.id)}>
              Sign &amp; approve
            </button>
            <button className="btn ghost" disabled={signer.trim().length < 2} onClick={() => onReject(r.id)}>
              Decline
            </button>
          </div>
        </article>
      ))}

      {declined.length > 0 && (
        <p className="muted small">
          Declined: {declined.map((d) => `#${d.id} ${d.payee} ${usd(d.amount)}`).join(' · ')}
        </p>
      )}
    </aside>
  )
}
