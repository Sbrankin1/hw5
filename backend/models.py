"""Pydantic models shared by the backend and agents."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
AGENT_NAMES: tuple[AgentName, ...] = ("boss", "inventory", "accounting", "facilities", "customer_service")

# The team is the Autobots (plus one Decepticon who keeps the books).
PERSONAS: dict[AgentName, str] = {
    "boss": "Optimus Prime",
    "inventory": "Ratchet",
    "accounting": "Megatron",
    "facilities": "Ironhide",
    "customer_service": "Bumblebee",
}

TicketStatus = Literal["open", "in_progress", "awaiting_approval", "blocked", "resolved"]


# ── What each agent hands back ────────────────────────────────────────

class AgentReport(BaseModel):
    """A specialist's answer to one delegated task."""

    agent: AgentName
    ticket_ids: list[int] = Field(description="Tickets this report covers.")
    in_character: str = Field(
        description="What you SAY out loud to whoever asked you: 1-3 sentences fully in your character's "
        "voice (this is what the board shows as your speech). Any number you mention must be exact.",
    )
    summary: str = Field(description="Two or three plain sentences for the record: what you found and what you did.")
    facts: list[str] = Field(
        default_factory=list,
        description="Numbers you relied on, each with the tool it came from, e.g. "
        "'CC-HOOD-NAVY M: 8 on hand (check_stock)'.",
    )
    approvals_requested: list[int] = Field(default_factory=list, description="approval_id values you queued.")
    drafts_created: list[int] = Field(default_factory=list, description="draft_id values you saved.")
    blockers: list[str] = Field(default_factory=list, description="Anything stopping the ticket from closing.")
    pushback: list[str] = Field(
        default_factory=list,
        description="Where you disagree with the plan you were handed, with the numbers behind it.",
    )
    next_steps: list[str] = Field(default_factory=list, description="What still has to happen, and who owns it.")


class TicketResolution(BaseModel):
    """The Boss's final word on one ticket."""

    ticket_id: int
    status: TicketStatus
    owner_agents: list[AgentName] = Field(description="Agents that worked the ticket, in order.")
    summary: str
    decision: str = Field(description="What the shop will do and why, in plain words.")
    approvals_requested: list[int] = Field(default_factory=list)
    drafts_created: list[int] = Field(default_factory=list)
    customer_eta: str | None = Field(default=None, description="Promised date (YYYY-MM-DD), if any.")
    blockers: list[str] = Field(default_factory=list)


class DeskReport(BaseModel):
    """The Boss's output for a run: every ticket it was given, plus the cross-ticket picture."""

    tickets: list[TicketResolution]
    cross_ticket_notes: list[str] = Field(
        default_factory=list,
        description="Dependencies between tickets: shared vendors/invoices, cash conflicts, ordering.",
    )
    cash_now: float
    cash_if_all_pending_approved: float
    approvals_waiting_on_human: list[int] = Field(default_factory=list)
    disagreements_settled: list[str] = Field(
        default_factory=list,
        description="Where a teammate (usually Megatron) pushed back, and what you decided and why.",
    )
    message_to_the_team: str = Field(description="Optimus Prime's closing words to the Autobots, in his voice.")


# ── Run bookkeeping ───────────────────────────────────────────────────

AuditEventKind = Literal[
    "run_start",        # a desk run begins: prompt, model, DB, tickets
    "agent_start",      # one agent loop begins: who, task, prompt file hash, allowed tools
    "model_request",    # loop step N: what goes to the model (tool results returned, retry errors)
    "model_response",   # loop step N: what came back (text, tool calls, finish reason, tokens, latency)
    "tool_call",        # an MCP tool is called with these args
    "tool_result",      # ...and returned this (status ok / refused / error, latency)
    "delegate",         # agent hands a task to a teammate
    "delegate_refused", # the loop guards blocked a hand-off
    "report",           # the teammate's report comes back
    "guardrail",        # a guardrail blocked something (ungrounded fact, outbound contact)
    "agent_end",        # one agent loop finished: output, steps, usage so far
    "agent_error",      # one agent loop raised
    "run_end",          # the desk run finished (or failed): final output, total usage, duration
]


class AuditEvent(BaseModel):
    """One line of output/audit_trail.json. Enough to replay who did what, when, why and with what data."""

    run_id: str = Field(description="One desk run (one CLI / API call).")
    seq: int = Field(description="Order within the run, starting at 1.")
    at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))
    event: AuditEventKind
    agent: str
    persona: str | None = None
    agent_run_id: str | None = Field(default=None, description="One agent loop; nested delegations get their own.")
    parent_agent_run_id: str | None = Field(default=None, description="The loop that delegated to this one.")
    chain: list[str] = Field(default_factory=list, description="Delegation path, e.g. ['boss', 'accounting'].")
    step: int | None = Field(default=None, description="Model-request number inside this agent loop.")
    target: str | None = Field(default=None, description="Tool name, or the teammate delegated to / reported to.")
    status: Literal["ok", "refused", "error"] | None = None
    duration_ms: int | None = None
    detail: Any = None



@dataclass
class TeamDeps:
    """Passed to every agent run. `chain` is who asked whom (boss -> accounting -> ...).
    `trace` and `sink` are shared by the whole run so every agent writes to one audit trail;
    `agent_run_id` and `step` belong to this agent loop only (delegation makes a fresh copy)."""

    chain: list[AgentName]
    run_id: str = ""
    trace: list[AuditEvent] = field(default_factory=list)
    sink: Callable[[AuditEvent], None] | None = None
    agent_run_id: str | None = None
    parent_agent_run_id: str | None = None
    step: int = 0

    @property
    def me(self) -> AgentName:
        return self.chain[-1]


class TeamRun(BaseModel):
    """What `run_desk` returns: the Boss's report plus how it got there."""

    model: str
    ticket_ids: list[int]
    output: DeskReport | AgentReport
    run_id: str
    trace: list[AuditEvent]
    usage: dict[str, Any]


# ── Backend API (backend/main.py) ─────────────────────────────────────

class TicketSummary(BaseModel):
    """One ticket for the board: its raw status, and the simple open/resolved state."""

    id: int
    type: str
    requester: str
    subject: str
    status: TicketStatus
    state: Literal["open", "resolved"]
    sku: str | None = None
    size: str | None = None
    qty: int | None = None
    lease_id: int | None = None
    invoice_id: int | None = None
    notes: str | None = None
    created_at: str
    open_approvals: int = 0
    drafts: int = 0
    stock_held: int = 0


class TicketDetail(TicketSummary):
    approvals: list[dict[str, Any]] = Field(default_factory=list)
    draft_messages: list[dict[str, Any]] = Field(default_factory=list)
    stock_holds: list[dict[str, Any]] = Field(default_factory=list)
    last_run_id: str | None = None


class RunInfo(BaseModel):
    """A team run started from the API. Poll it (or its events) while status is `running`."""

    run_id: str
    ticket_ids: list[int]
    status: Literal["running", "done", "error"]
    fresh_db: bool = False
    started_at: str
    finished_at: str | None = None
    events: int = 0
    output: dict[str, Any] | None = None
    error: str | None = None


class AgentEventView(BaseModel):
    """One audit event, explained: who it was, what they said, and what they did."""

    seq: int
    at: str
    event: str
    agent: str
    persona: str | None
    step: int | None
    chain: list[str]
    target: str | None = Field(default=None, description="Who they spoke to (a role) or which tool they used.")
    said: str | None = Field(default=None, description="The agent's words: model text, a task handed over, a report summary.")
    did: str | None = Field(default=None, description="The action: tool called and with what, delegation, sign-off, result.")
    status: str | None = None
    duration_ms: int | None = None
    detail: Any = None


class DecisionBody(BaseModel):
    """A human's approve/reject click. `approved_by` is the person's name, written to payments.approved_by."""

    approved_by: str = Field(min_length=1)


class CashView(BaseModel):
    account: str
    balance: float
    as_of: str
    pending_cash_out: float
    balance_if_all_pending_approved: float


class ResetResult(BaseModel):
    reset: bool
    source: str
    target: str
    checking_balance: float
    open_tickets: int
