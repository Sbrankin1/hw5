"""FastAPI backend — multi-agent operations team.

Routes (all under /api):
    GET  /health                       server + DB check
    GET  /tickets                      the desk tickets, each marked open or resolved
    GET  /tickets/{id}                 one ticket with its approvals, drafts and stock holds
    POST /tickets/{id}/run             run the agent team on one ticket (background); ?fresh=true resets the DB first
    POST /desk/run                     run the team on every open ticket; ?fresh=true (default) resets the DB first
    GET  /runs                         runs started since the server came up
    GET  /runs/{run_id}                one run's status and final output
    GET  /runs/{run_id}/events         every agent event: what they said and what they did (?after_seq= to poll)
    GET  /approvals                    the approval queue (?status=pending|awaiting_signoff|open|approved|rejected|all)
    POST /approvals/{id}/approve       a HUMAN approves: only now is a payment / PO executed
    POST /approvals/{id}/reject        a HUMAN rejects
    GET  /cash                         checking balance from cash_accounts
    POST /reset                        copy data/campus_customs.db over data/campus_customs_new.db

Agents only *prepare* payments (queued approvals). Money moves only in /approvals/{id}/approve,
which calls the human-only `decide_approval` MCP tool with the approver's name.

Start from the backend folder:
    cd backend && ../.venv/bin/uvicorn main:app --reload --port 8000
"""

import asyncio
import json
import os
import shutil
import sqlite3
import sys
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:  # `uvicorn main:app` runs from backend/; make `backend.*` and the MCP server importable
    sys.path.insert(0, str(ROOT))
if str(ROOT / "mcp_server") not in sys.path:
    sys.path.insert(0, str(ROOT / "mcp_server"))

from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastmcp import Client  # noqa: E402

import server as mcp_server  # noqa: E402  (mcp_server/server.py, used in-process for human decisions)
from backend.agents import PERSONAS, AuditLog, Team  # noqa: E402
from backend.models import (  # noqa: E402
    AgentEventView,
    AuditEvent,
    CashView,
    DecisionBody,
    ResetResult,
    RunInfo,
    TicketDetail,
    TicketSummary,
)

DB_PATH: Path = mcp_server.DB_PATH                       # data/campus_customs_new.db (working copy)
ORIGINAL_DB = ROOT / "data" / "campus_customs.db"       # never written
AUDIT_PATH = Path(os.getenv("CAMPUS_AUDIT_PATH", ROOT / "output" / "audit_trail.json"))

app = FastAPI(title="Campus Customs operations desk", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173",   # the Vite board (npm run dev)
                   "http://localhost:4173", "http://127.0.0.1:4173"],  # vite preview
    allow_methods=["*"],
    allow_headers=["*"],
)

# One team run at a time: they all write the same working DB.
RUN_LOCK = asyncio.Lock()
RUNS: dict[str, dict[str, Any]] = {}          # run_id -> {"info": RunInfo, "events": [AuditEvent]}
LAST_RUN_FOR_TICKET: dict[int, str] = {}
AUDIT = AuditLog(AUDIT_PATH)


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:  # e.g. a CAMPUS_DB_PATH outside the project
        return str(path)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _db() -> sqlite3.Connection:
    """The same connection the MCP server uses (it also creates approvals/drafts/stock_holds if missing)."""
    try:
        return mcp_server._connect()
    except FileNotFoundError as exc:
        raise HTTPException(503, str(exc)) from exc


# ── Tickets ───────────────────────────────────────────────────────────

def _ticket_rows(conn: sqlite3.Connection, ticket_id: int | None = None) -> list[TicketSummary]:
    sql = (
        "SELECT t.*, "
        " (SELECT COUNT(*) FROM approvals a WHERE a.ticket_id = t.id AND a.status IN ('awaiting_signoff','pending')) AS open_approvals, "
        " (SELECT COUNT(*) FROM drafts d WHERE d.ticket_id = t.id) AS drafts, "
        " (SELECT COALESCE(SUM(qty),0) FROM stock_holds h WHERE h.ticket_id = t.id AND h.status = 'held') AS stock_held "
        "FROM tickets t"
    )
    params: tuple = ()
    if ticket_id is not None:
        sql, params = sql + " WHERE t.id = ?", (ticket_id,)
    rows = conn.execute(sql + " ORDER BY t.id", params).fetchall()
    return [TicketSummary(**dict(r), state="resolved" if r["status"] == "resolved" else "open") for r in rows]


@app.get("/api/health")
def health() -> dict:
    with closing(_db()) as conn:
        today = conn.execute("SELECT date_today FROM desk").fetchone()["date_today"]
    return {"ok": True, "db": _rel(DB_PATH), "shop_today": today, "run_in_progress": RUN_LOCK.locked()}


@app.get("/api/tickets", response_model=list[TicketSummary])
def list_tickets() -> list[TicketSummary]:
    """Every desk ticket (101, 102, 103) and whether it is open or resolved."""
    with closing(_db()) as conn:
        return _ticket_rows(conn)


@app.get("/api/tickets/{ticket_id}", response_model=TicketDetail)
def get_ticket(ticket_id: int) -> TicketDetail:
    with closing(_db()) as conn:
        rows = _ticket_rows(conn, ticket_id)
        if not rows:
            raise HTTPException(404, f"No ticket {ticket_id}.")
        approvals = [dict(r) for r in conn.execute("SELECT * FROM approvals WHERE ticket_id = ? ORDER BY id", (ticket_id,))]
        drafts = [dict(r) for r in conn.execute("SELECT * FROM drafts WHERE ticket_id = ? ORDER BY id", (ticket_id,))]
        holds = [dict(r) for r in conn.execute("SELECT * FROM stock_holds WHERE ticket_id = ? ORDER BY id", (ticket_id,))]
    return TicketDetail(**rows[0].model_dump(), approvals=approvals, draft_messages=drafts, stock_holds=holds,
                        last_run_id=LAST_RUN_FOR_TICKET.get(ticket_id))


# ── Running the team ──────────────────────────────────────────────────

def _reset_db() -> None:
    if not ORIGINAL_DB.exists():
        raise HTTPException(500, f"Original DB missing at {ORIGINAL_DB}.")
    shutil.copyfile(ORIGINAL_DB, DB_PATH)


async def _execute(run_id: str, ticket_ids: list[int] | None, fresh: bool) -> None:
    record = RUNS[run_id]
    info: RunInfo = record["info"]

    def sink(event: AuditEvent) -> None:  # every event: to the audit file and to this run's live list
        AUDIT(event)
        record["events"].append(event)
        info.events = len(record["events"])

    try:
        result = await Team(audit=sink).run(ticket_ids, run_id=run_id, fresh=fresh)
        info.status, info.output = "done", result.model_dump(mode="json")["output"]
    except Exception as exc:  # the run_end / agent_error events already hold the details
        info.status, info.error = "error", f"{type(exc).__name__}: {exc}"
    finally:
        info.finished_at = _now()
        RUN_LOCK.release()


async def _start(ticket_ids: list[int] | None, fresh: bool) -> RunInfo:
    if RUN_LOCK.locked():
        raise HTTPException(409, "A team run is already in progress. Wait for it to finish.")
    await RUN_LOCK.acquire()
    try:
        if fresh:
            _reset_db()
        run_id = uuid.uuid4().hex[:12]
        info = RunInfo(run_id=run_id, ticket_ids=ticket_ids or [], status="running", fresh_db=fresh, started_at=_now())
        RUNS[run_id] = {"info": info, "events": []}
        for t in ticket_ids or []:
            LAST_RUN_FOR_TICKET[t] = run_id
        asyncio.create_task(_execute(run_id, ticket_ids, fresh))
        return info
    except BaseException:
        RUN_LOCK.release()
        raise


@app.post("/api/tickets/{ticket_id}/run", response_model=RunInfo, status_code=202)
async def run_ticket(ticket_id: int, fresh: bool = Query(False, description="Reset the DB to the original first")) -> RunInfo:
    """Run the agent team on one ticket. Returns at once; follow /api/runs/{run_id}/events.

    Leave fresh=false to continue a ticket after a human approval (e.g. 101 after #501 is paid).
    """
    with closing(_db()) as conn:
        if not conn.execute("SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)).fetchone():
            raise HTTPException(404, f"No ticket {ticket_id}.")
    return await _start([ticket_id], fresh)


@app.post("/api/desk/run", response_model=RunInfo, status_code=202)
async def run_desk(fresh: bool = Query(True, description="Reset the DB to the original first (a fresh run)")) -> RunInfo:
    """Run the team on every open ticket. A fresh run resets the DB to its original values first."""
    return await _start(None, fresh)


@app.get("/api/runs", response_model=list[RunInfo])
def list_runs() -> list[RunInfo]:
    return [r["info"] for r in RUNS.values()]


@app.get("/api/runs/{run_id}", response_model=RunInfo)
def get_run(run_id: str) -> RunInfo:
    if run_id not in RUNS:
        raise HTTPException(404, f"No run {run_id} since the server started (older runs: /api/runs/{run_id}/events).")
    return RUNS[run_id]["info"]


# ── Agent events: what they said and what they did ────────────────────

def _short(value: Any, limit: int = 300) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text if len(text) <= limit else text[:limit] + "…"


def _name(role: str | None) -> str:
    return PERSONAS.get(role, role or "?")


def _explain(e: AuditEvent) -> tuple[str | None, str | None]:
    d = e.detail if isinstance(e.detail, dict) else {}
    match e.event:
        case "run_start":
            return None, f"Run started: {d.get('prompt')}" + (" (DB reset to original)" if d.get("fresh_db") else "")
        case "agent_start":
            return None, f"Started on: {d.get('task')}"
        case "model_request":
            retries = [p for p in d.get("parts", []) if p.get("type") == "retry"]
            if retries:
                return None, "Asked to fix their answer: " + _short(retries[0].get("error"), 400)
            returned = [p["tool"] for p in d.get("parts", []) if p.get("type") == "tool_return"]
            return None, (f"Thinking, with results from {', '.join(returned)}" if returned else "Thinking")
        case "model_response":
            said = " ".join(p["content"] for p in d.get("parts", []) if p.get("type") == "text").strip() or None
            calls = [p for p in d.get("parts", []) if p.get("type") == "tool_call"]
            did = "; ".join(
                "Submitted their report" if c["tool"] == "final_result"
                else f"Decided to call {c['tool']}({_short(c.get('args'), 160)})" for c in calls
            ) or None
            return said, did
        case "tool_call":
            return None, f"Called {e.target}({_short(d.get('args'), 200)})"
        case "tool_result":
            return None, f"{e.target} → {e.status}: {_short(d.get('result', d.get('error')), 300)}"
        case "delegate":
            return d.get("task"), f"Handed the task to {_name(e.target)}"
        case "delegate_refused":
            return d.get("task"), f"Hand-off to {_name(e.target)} blocked: {d.get('reason')}"
        case "report":
            report = d.get("report", {})
            return report.get("in_character") or report.get("summary"), f"Reported back to {_name(e.target)}" + (
                f" (pushback: {'; '.join(report['pushback'])})" if report.get("pushback") else "")
        case "guardrail":
            return None, f"Guardrail {e.status}: " + "; ".join(d.get("problems", []) or [d.get("reason", "")])
        case "agent_end":
            out = d.get("output", {})
            said = out.get("message_to_the_team") or out.get("in_character") or out.get("summary")
            return said, f"Finished after {d.get('steps')} step(s)"
        case "agent_error":
            return None, f"Failed: {d.get('error')}"
        case "run_end":
            return None, "Run finished" if e.status == "ok" else f"Run failed: {d.get('error')}"
    return None, None


def _view(e: AuditEvent, include_detail: bool) -> AgentEventView:
    said, did = _explain(e)
    return AgentEventView(seq=e.seq, at=e.at, event=e.event, agent=e.agent, persona=e.persona, step=e.step,
                          chain=e.chain, target=e.target, said=said, did=did, status=e.status, duration_ms=e.duration_ms,
                          detail=e.detail if include_detail else None)


def _events_for(run_id: str) -> list[AuditEvent]:
    if run_id in RUNS:
        return list(RUNS[run_id]["events"])
    try:  # a run from before this server started: read it back from the audit trail
        rows = json.loads(AUDIT_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        rows = []
    return [AuditEvent(**r) for r in rows if r.get("run_id") == run_id]


@app.get("/api/runs/{run_id}/events", response_model=list[AgentEventView])
def run_events(run_id: str, after_seq: int = 0, detail: bool = False) -> list[AgentEventView]:
    """Each agent event in order. Poll with after_seq=<last seq you have> while the run is going.
    detail=true adds the full raw event (tool args/results, model output)."""
    events = _events_for(run_id)
    if not events and run_id not in RUNS:
        raise HTTPException(404, f"No events for run {run_id}.")
    return [_view(e, detail) for e in events if e.seq > after_seq]


# ── Human approvals: the only place money moves ───────────────────────

@app.get("/api/approvals")
def list_approvals(status: str = Query("open", description="pending | awaiting_signoff | open | approved | rejected | all")) -> dict:
    with closing(_db()) as conn:
        sql, params = "SELECT * FROM approvals", ()
        if status == "open":
            sql += " WHERE status IN ('awaiting_signoff', 'pending')"
        elif status != "all":
            sql, params = sql + " WHERE status = ?", (status,)
        rows = [dict(r) for r in conn.execute(sql + " ORDER BY id", params)]
    for r in rows:
        r["human_can_decide"] = r["status"] == "pending"   # awaiting_signoff waits for Megatron first
    return {"approvals": rows, "cash": cash().model_dump()}


async def _decide(approval_id: int, decision: str, who: str) -> dict:
    if RUN_LOCK.locked():
        raise HTTPException(409, "A team run is in progress; decide once it finishes.")
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("decide_approval",
                                        {"approval_id": approval_id, "decision": decision, "decided_by": who},
                                        raise_on_error=False)
    data = result.structured_content or {}
    data = data.get("result", data) if set(data) == {"result"} else data
    if not data.get("found", False):
        raise HTTPException(404, data.get("error", "Not found."))
    if not data.get("decided", False):
        raise HTTPException(409, data.get("error", "Not decided."))
    return {**data, "ticket": _after_decision(approval_id, decision, who), "cash": cash().model_dump()}


def _after_decision(approval_id: int, decision: str, who: str) -> dict | None:
    """Once a human has decided every approval on a ticket, hand it back to the team: the ticket
    moves from awaiting_approval to in_progress, and the next run confirms and closes it out."""
    with closing(_db()) as conn:
        a = conn.execute("SELECT ticket_id FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        if a is None or a["ticket_id"] is None:
            return None
        t = conn.execute("SELECT id, status, notes FROM tickets WHERE id = ?", (a["ticket_id"],)).fetchone()
        still_open = conn.execute(
            "SELECT COUNT(*) FROM approvals WHERE ticket_id = ? AND status IN ('awaiting_signoff', 'pending')", (t["id"],)
        ).fetchone()[0]
        if t["status"] == "awaiting_approval" and not still_open:
            today = conn.execute("SELECT date_today FROM desk").fetchone()["date_today"]
            note = f"{t['notes'] or ''}\n[{today}] Human ({who}) decided every approval; rerun the team to close out.".strip()
            with conn:
                conn.execute("UPDATE tickets SET status = 'in_progress', notes = ? WHERE id = ?", (note, t["id"]))
        return _ticket_rows(conn, t["id"])[0].model_dump()


@app.post("/api/approvals/{approval_id}/approve")
async def approve(approval_id: int, body: DecisionBody) -> dict:
    """A human approved. For a payment or PO this writes `payments` (approved_by = the human),
    debits checking, and marks the invoice paid / moves rent forward. Refuses negative cash."""
    return await _decide(approval_id, "approve", body.approved_by.strip())


@app.post("/api/approvals/{approval_id}/reject")
async def reject(approval_id: int, body: DecisionBody) -> dict:
    return await _decide(approval_id, "reject", body.approved_by.strip())


# ── Cash and reset ────────────────────────────────────────────────────

@app.get("/api/cash", response_model=CashView)
def cash() -> CashView:
    """The checking balance from cash_accounts, plus what's waiting to go out."""
    with closing(_db()) as conn:
        acct = conn.execute("SELECT name, balance, date FROM cash_accounts WHERE name = 'checking'").fetchone()
        if acct is None:
            raise HTTPException(404, "No checking account in cash_accounts.")
        pending = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM approvals WHERE status = 'pending'").fetchone()[0]
    return CashView(account=acct["name"], balance=acct["balance"], as_of=acct["date"], pending_cash_out=pending,
                    balance_if_all_pending_approved=acct["balance"] - pending)


@app.post("/api/reset", response_model=ResetResult)
def reset() -> ResetResult:
    """Put the working DB back to its original values (copies data/campus_customs.db over it)."""
    if RUN_LOCK.locked():
        raise HTTPException(409, "A team run is in progress; reset once it finishes.")
    _reset_db()
    with closing(_db()) as conn:
        balance = conn.execute("SELECT balance FROM cash_accounts WHERE name = 'checking'").fetchone()["balance"]
        open_tickets = conn.execute("SELECT COUNT(*) FROM tickets WHERE status != 'resolved'").fetchone()[0]
    LAST_RUN_FOR_TICKET.clear()
    return ResetResult(reset=True, source=_rel(ORIGINAL_DB), target=_rel(DB_PATH),
                       checking_balance=balance, open_tickets=open_tickets)
