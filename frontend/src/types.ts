// Mirrors backend/models.py (the API shapes from backend/main.py).

export type Role = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'
export type TicketStatus = 'open' | 'in_progress' | 'awaiting_approval' | 'blocked' | 'resolved'

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  status: TicketStatus
  state: 'open' | 'resolved'
  sku: string | null
  size: string | null
  qty: number | null
  lease_id: number | null
  invoice_id: number | null
  notes: string | null
  created_at: string
  open_approvals: number
  drafts: number
  stock_held: number
}

export interface TicketDetail extends Ticket {
  approvals: Approval[]
  draft_messages: Draft[]
  stock_holds: { id: number; sku: string; size: string; qty: number; status: string; note: string | null }[]
  last_run_id: string | null
}

export interface Draft {
  id: number
  ticket_id: number
  recipient: string
  subject: string
  body: string
  author: string
  created_at: string
}

export interface Approval {
  id: number
  ticket_id: number | null
  kind: 'invoice' | 'rent' | 'purchase_order' | 'discount'
  ref_id: number | null
  amount: number
  details: string
  requested_by: Role
  status: 'awaiting_signoff' | 'pending' | 'approved' | 'rejected'
  signed_off_by: string | null
  decided_by: string | null
  decided_at: string | null
  payment_id: number | null
  created_at: string
  human_can_decide?: boolean
}

export interface Cash {
  account: string
  balance: number
  as_of: string
  pending_cash_out: number
  balance_if_all_pending_approved: number
}

export interface RunInfo {
  run_id: string
  ticket_ids: number[]
  status: 'running' | 'done' | 'error'
  fresh_db: boolean
  started_at: string
  finished_at: string | null
  events: number
  output: DeskReport | null
  error: string | null
}

export interface AgentEvent {
  seq: number
  at: string
  event:
    | 'run_start' | 'agent_start' | 'model_request' | 'model_response' | 'tool_call' | 'tool_result'
    | 'delegate' | 'delegate_refused' | 'report' | 'guardrail' | 'agent_end' | 'agent_error' | 'run_end'
  agent: Role
  persona: string | null
  step: number | null
  chain: Role[]
  target: string | null
  said: string | null
  did: string | null
  status: 'ok' | 'refused' | 'error' | null
  duration_ms: number | null
  detail: any
}

export interface AgentReport {
  agent: Role
  ticket_ids: number[]
  in_character?: string
  summary: string
  facts: string[]
  approvals_requested: number[]
  drafts_created: number[]
  blockers: string[]
  pushback: string[]
  next_steps: string[]
}

export interface TicketResolution {
  ticket_id: number
  status: TicketStatus
  owner_agents: Role[]
  summary: string
  decision: string
  approvals_requested: number[]
  drafts_created: number[]
  customer_eta: string | null
  blockers: string[]
}

export interface DeskReport {
  tickets: TicketResolution[]
  cross_ticket_notes: string[]
  cash_now: number
  cash_if_all_pending_approved: number
  approvals_waiting_on_human: number[]
  disagreements_settled: string[]
  message_to_the_team: string
}
