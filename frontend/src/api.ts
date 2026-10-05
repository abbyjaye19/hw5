import type { AgentEvent, CashPosition, Draft, PaymentRequest, RunInfo, Ticket } from './types'

export const API_BASE = 'http://localhost:8000'

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  })
  const text = await res.text()
  const body = text ? JSON.parse(text) : null
  if (!res.ok) throw new Error((body && (body.detail || body.error)) || `HTTP ${res.status}`)
  return body as T
}

export const api = {
  health: () => call<{ ok: boolean; model: string; team_ready: boolean }>('/api/health'),
  tickets: () => call<{ tickets: Ticket[] }>('/api/tickets').then((r) => r.tickets),
  runTicket: (id: number) => call<RunInfo>(`/api/tickets/${id}/run`, { method: 'POST' }),
  run: (runId: string) => call<RunInfo>(`/api/runs/${runId}`),
  events: (since = -1, limit = 1000) =>
    call<{ events: AgentEvent[]; last_id: number }>(`/api/events?since=${since}&limit=${limit}`),
  payments: () => call<{ requests: PaymentRequest[] }>('/api/payments').then((r) => r.requests),
  approve: (id: number, approvedBy: string) =>
    call<{ ok: boolean; new_balance: number }>(`/api/payments/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ approved_by: approvedBy }),
    }),
  reject: (id: number, decidedBy: string, reason: string) =>
    call<{ ok: boolean }>(`/api/payments/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ decided_by: decidedBy, reason }),
    }),
  cash: () => call<CashPosition>('/api/cash'),
  drafts: () => call<{ drafts: Draft[] }>('/api/drafts').then((r) => r.drafts),
  reset: () => call<{ ok: boolean }>('/api/reset', { method: 'POST' }),
}
