import type { AgentEvent, Approval, Cash, RunInfo, Ticket, TicketDetail } from './types'

export const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    })
  } catch {
    throw new ApiError(0, `Can't reach the backend at ${API_URL}. Is uvicorn running on port 8000?`)
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch { /* not JSON */ }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => call<{ ok: boolean; shop_today: string; run_in_progress: boolean; db: string }>('/api/health'),
  tickets: () => call<Ticket[]>('/api/tickets'),
  ticket: (id: number) => call<TicketDetail>(`/api/tickets/${id}`),
  runTicket: (id: number, fresh = false) => call<RunInfo>(`/api/tickets/${id}/run?fresh=${fresh}`, { method: 'POST' }),
  run: (runId: string) => call<RunInfo>(`/api/runs/${runId}`),
  events: (runId: string, afterSeq = 0) =>
    call<AgentEvent[]>(`/api/runs/${runId}/events?after_seq=${afterSeq}&detail=true`),
  approvals: (status = 'all') => call<{ approvals: Approval[]; cash: Cash }>(`/api/approvals?status=${status}`),
  decide: (id: number, decision: 'approve' | 'reject', approvedBy: string) =>
    call<{ status: string; payment_id: number | null; cash: Cash; ticket: Ticket | null }>(
      `/api/approvals/${id}/${decision}`,
      { method: 'POST', body: JSON.stringify({ approved_by: approvedBy }) },
    ),
  cash: () => call<Cash>('/api/cash'),
  reset: () => call<{ reset: boolean; checking_balance: number }>('/api/reset', { method: 'POST' }),
}
