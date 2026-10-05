export type AgentName = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  sku: string | null
  size: string | null
  qty: number | null
  lease_id: number | null
  invoice_id: number | null
  status: string
  notes: string | null
  created_at: string
  is_resolved: boolean
  state: 'open' | 'resolved'
}

export interface CashPosition {
  found: boolean
  account: string
  balance: number
  as_of: string
  pending_requests: { id: number; kind: string; payee: string; amount: number; ticket_id: number | null }[]
  pending_total: number
  balance_if_all_pending_paid: number
}

export interface PaymentRequest {
  id: number
  kind: 'invoice' | 'rent' | 'purchase_order'
  ref_id: number | null
  vendor_id: number | null
  sku: string | null
  size: string | null
  qty: number | null
  payee: string
  amount: number
  ticket_id: number | null
  reason: string | null
  requested_by: string
  status: 'pending' | 'paid' | 'rejected'
  created_on: string
  decided_by: string | null
  decided_on: string | null
  decision_note: string | null
  payment_id: number | null
  expected_arrival: string | null
}

export interface Draft {
  id: number
  ticket_id: number
  recipient: string
  subject: string
  body: string
  author: string
  status: string
  created_on: string
}

export interface AgentEvent {
  id: number
  ts: string
  run_id: string
  ticket_id: number | null
  agent: string
  event: string
  depth?: number
  chain?: string[]
  said?: string | null
  tool_calls?: { tool: string; args: unknown }[]
  model?: string
  usage?: { input_tokens: number; output_tokens: number }
  tool?: string
  args?: unknown
  result?: unknown
  to_agent?: string
  task?: string
  output?: Record<string, unknown> | null
  ticket_usage_so_far?: { requests: number; input_tokens: number; output_tokens: number }
  details?: Record<string, unknown>
}

export interface TicketOutcome {
  ticket_id: number
  decision: string
  final_status: string
  actions_taken: string[]
  payment_request_ids: number[]
  draft_ids: number[]
  human_next_steps: string[]
  risks_or_open_questions: string[]
}

export interface RunInfo {
  run_id: string
  ticket_id: number
  status: 'queued' | 'running' | 'done' | 'error'
  started_at: string
  finished_at: string | null
  outcome: TicketOutcome | null
  error: string | null
}
