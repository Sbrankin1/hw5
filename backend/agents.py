"""Campus Customs agent team: Boss + four specialists on a Portkey-served model, wired to the MCP server.

The team are Transformers: Optimus Prime (boss), Ratchet (inventory), Megatron
(accounting), Ironhide (facilities) and Bumblebee (customer service). Each persona
lives in its prompt file; the code only uses role names. Every run starts with
Optimus saying "Autobots, roll out!" out loud (macOS `say`; set ROLL_OUT_AUDIO=0 to mute).

Every agent can delegate to every other agent (full connectivity) through one
`delegate(to, task)` tool. Each delegation is a nested agent run that shares the
caller's usage counter and audit trail. Two guards stop loops:
  * no delegating to an agent already in the current chain (boss -> accounting -> boss)
  * at most MAX_DEPTH agents deep

Agents reach the database only through MCP tools (mcp_server/server.py), each agent
seeing just the tools its job needs. `decide_approval` is never given to an agent:
only a human, via the backend, can approve money or prices.

Every step of every agent loop is appended to output/audit_trail.json the moment it
happens (see AuditLog), so a crashed or interrupted run still leaves its trail.

Run from the hw5 root:
    .venv/bin/python -m backend.agents            # whole desk
    .venv/bin/python -m backend.agents 102        # one ticket
"""

import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import replace
from pathlib import Path
from collections.abc import Callable
from typing import Any

from dotenv import load_dotenv
from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport
from pydantic_ai import Agent, ModelRetry, RunContext, UsageLimits
from pydantic_ai.mcp import CallToolFunc, MCPToolset
from pydantic_ai.messages import (
    RetryPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import RunUsage

from backend.models import (
    AGENT_NAMES,
    AgentName,
    PERSONAS,
    AgentReport,
    AuditEvent,
    DeskReport,
    TeamDeps,
    TeamRun,
)

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = Path(__file__).resolve().parent / "prompts"
load_dotenv(ROOT / ".env")
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

MODEL_NAME = os.getenv("MODEL_NAME", "gpt-5.6-luna")
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")
MODEL_TIMEOUT_S = float(os.getenv("MODEL_TIMEOUT_S", "180"))  # one model call; the Boss can think for a while
MAX_DEPTH = 4                                   # boss + three levels of hand-offs
RUN_LIMITS = UsageLimits(request_limit=120)     # whole run, shared across every nested agent
AUDIT_PATH = ROOT / "output" / "audit_trail.json"

# Which MCP tools each agent may call. decide_approval is deliberately absent.
READ = {"get_ticket"}
AGENT_TOOLS: dict[AgentName, set[str]] = {
    # Optimus leads from the front: he can do any specialist's job himself when he has to.
    # He can't sign off discounts: that's Megatron's job.
    "boss": READ | {"list_open_tickets", "update_ticket", "list_approvals",
                    "check_stock", "vendor_status", "lease_and_cash_status",
                    "request_payment", "request_discount", "draft_purchase_order", "draft_message",
                    "hold_stock"},
    "inventory": READ | {"check_stock", "vendor_status", "draft_purchase_order", "hold_stock"},
    # Megatron signs discounts off but never prices them: only Bumblebee (or Prime) suggests one.
    "accounting": READ | {"check_stock", "vendor_status", "lease_and_cash_status",
                          "request_payment", "list_approvals", "sign_off_discount"},
    "facilities": READ | {"lease_and_cash_status"},
    # Bumblebee suggests discounts; they wait for Megatron's sign-off.
    "customer_service": READ | {"check_stock", "vendor_status", "draft_message", "request_discount"},
}
# Arguments the server uses to record who did something. Filled from the run, not the model.
AUTHOR_ARGS = ("requested_by", "author", "signed_off_by")


# ── Audit trail ───────────────────────────────────────────────────────

class AuditLog:
    """Appends events to output/audit_trail.json as they happen.

    The file is one JSON array, one event per line, kept valid after every write: each
    append replaces the closing `]`. Runs accumulate (append-only); filter by run_id.
    """

    def __init__(self, path: Path = AUDIT_PATH):
        self.path = path
        self._lock = threading.Lock()
        self._seq = 0

    def _prepare(self) -> None:
        try:
            existing = json.loads(self.path.read_text()) if self.path.exists() else None
        except json.JSONDecodeError:
            existing = None
        if not isinstance(existing, list):  # missing, "{}", or corrupt: start a fresh array
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("[\n]\n")

    def __call__(self, event: AuditEvent) -> None:
        line = event.model_dump_json()
        with self._lock:
            if self._seq == 0:
                self._prepare()
            self._seq += 1
            with self.path.open("r+b") as f:
                f.seek(0, os.SEEK_END)
                pos = f.tell()
                while pos > 0:  # step back over trailing whitespace and the closing bracket
                    pos -= 1
                    f.seek(pos)
                    if f.read(1) == b"]":
                        break
                f.seek(pos)
                f.truncate()
                f.seek(0)
                empty = f.read(pos).strip() == b"["
                f.seek(pos)
                f.write((("" if empty else ",") + "\n" + line + "\n]\n").encode())
                f.flush()
                os.fsync(f.fileno())


def _clip(value: Any, limit: int = 8000) -> Any:
    """Keep audit lines readable: full data for anything normal-sized, a marked cut otherwise."""
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    if len(text) <= limit:
        return value
    return text[:limit] + f"... [clipped {len(text) - limit} chars]"


def _event(deps: TeamDeps, event: str, agent: AgentName, *, target: str | None = None,
           status: str | None = None, duration_ms: int | None = None, detail: Any = None,
           step: int | None = None) -> None:
    record = AuditEvent(
        run_id=deps.run_id,
        seq=len(deps.trace) + 1,
        event=event,
        agent=agent,
        persona=PERSONAS.get(agent),
        agent_run_id=deps.agent_run_id,
        parent_agent_run_id=deps.parent_agent_run_id,
        chain=list(deps.chain),
        step=deps.step if step is None else step,
        target=target,
        status=status,
        duration_ms=duration_ms,
        detail=_clip(detail),
    )
    deps.trace.append(record)
    if deps.sink:
        deps.sink(record)


def _ms(since: float) -> int:
    return int((time.perf_counter() - since) * 1000)


def _tool_status(result: Any) -> str:
    """MCP tools never invent data: a refusal comes back as found=False / queued=False / an error key."""
    if isinstance(result, dict) and (result.get("found") is False or result.get("error")
                                     or result.get("queued") is False or result.get("updated") is False
                                     or result.get("decided") is False):
        return "refused"
    if isinstance(result, list) and result and isinstance(result[0], dict) and result[0].get("found") is False:
        return "refused"
    return "ok"


def _describe_request(request) -> dict:
    """What this loop step sends to the model: the task, tool results coming back, retry errors."""
    out: dict[str, Any] = {"parts": []}
    for part in request.parts:
        if isinstance(part, UserPromptPart):
            out["parts"].append({"type": "user_prompt", "content": part.content})
        elif isinstance(part, ToolReturnPart):
            out["parts"].append({"type": "tool_return", "tool": part.tool_name, "tool_call_id": part.tool_call_id})
        elif isinstance(part, RetryPromptPart):
            out["parts"].append({"type": "retry", "tool": part.tool_name, "error": part.model_response()})
        else:
            out["parts"].append({"type": type(part).__name__})
    return out


def _describe_response(response) -> dict:
    """What the model decided on this step: its words, the tools it chose and why it stopped."""
    parts = []
    for part in response.parts:
        if isinstance(part, TextPart):
            parts.append({"type": "text", "content": part.content})
        elif isinstance(part, ToolCallPart):
            parts.append({"type": "tool_call", "tool": part.tool_name, "tool_call_id": part.tool_call_id,
                          "args": part.args_as_dict()})
        elif isinstance(part, ThinkingPart):
            parts.append({"type": "thinking", "content": part.content})
        else:
            parts.append({"type": type(part).__name__})
    usage = response.usage
    return {
        "model": response.model_name,
        "finish_reason": response.finish_reason,
        "parts": parts,
        "usage": {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens},
    }


def _usage(usage) -> dict:
    return {"requests": usage.requests, "tool_calls": usage.tool_calls,
            "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens}


def roll_out() -> None:
    """Optimus opens every run. Plays in the background so it never slows the agents down."""
    print("Optimus Prime: Autobots, roll out!", file=sys.stderr)
    if os.getenv("ROLL_OUT_AUDIO", "1") != "0" and shutil.which("say"):
        subprocess.Popen(["say", "-v", "Ralph", "-r", "140", "[[pbas 20]] Autobots... roll out!"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ── Guardrails ────────────────────────────────────────────────────────
# 1. No outbound contact: the team has no tool that sends email, texts or calls anyone,
#    and _audit_tool_call refuses any tool whose name looks like one, even if one were added.
# 2. No made-up information: every agent's final report is checked by _grounding_check before
#    it is accepted. Approval/draft ids, dollar amounts and dates must trace back to a tool
#    result in this run (or simple arithmetic on them); otherwise the agent is told exactly
#    what has no source and must try again.

OUTBOUND_TOOL = re.compile(
    r"(?:^|_)(?:send|email|e_mail|mail|sms|text|call|phone|dial|notify|post|tweet|webhook|http|fax)(?:_|s?$)", re.I)
SENT_CLAIM = re.compile(
    r"\b(?:i|we|i've|we've|i have|we have|has been|have been|was|were|i've already|already)\s+"
    r"(?:sent|emailed|e-mailed|called|phoned|rang|texted|mailed|faxed)\b"
    r"(?!\s+(?:to\s+(?:a\s+|the\s+)?(?:human|board|desk)|for\s+(?:human\s+)?approval))",
    re.I,
)
MONEY = re.compile(r"\$\s?(-?\d(?:[\d,]*\d)?(?:\.\d+)?)")
ISO_DATE = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")
# Tool fields that hold dollars, and fields that hold unit counts / day counts.
MONEY_KEYS = {"amount", "balance", "monthly_rent", "unit_cost", "list_price", "total_cash", "cash_after_rent",
              "open_balance", "cash_now", "pending_cash_out_total", "cash_if_all_pending_approved",
              "margin_per_unit", "order_total", "unit_price"}
QTY_KEYS = {"qty", "qty_on_hand", "qty_needed", "shortfall"}
DAY_KEYS = {"lead_days", "days_until_due", "days_overdue"}


def _walk(value: Any, key: str | None = None):
    """Yield (key, value) for every scalar inside nested dicts/lists (list items keep the list's key)."""
    if isinstance(value, dict):
        for k, v in value.items():
            yield from _walk(v, k)
    elif isinstance(value, list):
        for v in value:
            yield from _walk(v, key)
    else:
        yield key, value


def _evidence(deps: TeamDeps) -> dict[str, set]:
    """Everything the team has actually seen from tools (and teammates' checked reports) this run."""
    money: set[float] = set()
    qtys: set[float] = set()
    days: set[int] = set()
    dates: set[str] = set()
    approval_ids: set[int] = set()
    draft_ids: set[int] = set()
    for e in deps.trace:
        if e.event not in ("tool_result", "report"):
            continue
        detail = e.detail if isinstance(e.detail, dict) else {"text": e.detail}
        for key, v in _walk(detail):
            if isinstance(v, bool) or v is None:
                continue
            if isinstance(v, (int, float)):
                if key in MONEY_KEYS:
                    money.add(round(float(v), 2))
                elif key in QTY_KEYS:
                    qtys.add(float(v))
                elif key in DAY_KEYS:
                    days.add(int(v))
            elif isinstance(v, str):
                dates.update(ISO_DATE.findall(v))
                for m in MONEY.findall(v):  # "$2,400" inside tool details or teammates' checked reports
                    money.add(round(float(m.replace(",", "")), 2))
            if key == "approval_id" or (key == "approvals_requested" and isinstance(v, int)):
                approval_ids.add(int(v))
            if key == "draft_id":
                draft_ids.add(int(v))
        # list_approvals / get_ticket rows carry their id under "id"
        result = detail.get("result")
        if isinstance(result, dict):
            for row in result.get("approvals", []) or []:
                approval_ids.add(int(row["id"]))
            for row in result.get("drafts", []) or []:
                draft_ids.add(int(row["id"]))
        report = detail.get("report")
        if isinstance(report, dict):
            approval_ids.update(report.get("approvals_requested", []) or [])
            approval_ids.update(report.get("approvals_waiting_on_human", []) or [])
            draft_ids.update(report.get("drafts_created", []) or [])
    return {"money": money, "qtys": qtys, "days": days, "dates": dates,
            "approval_ids": approval_ids, "draft_ids": draft_ids}


def _money_grounded(value: float, ev: dict[str, set]) -> bool:
    """A dollar figure is grounded if a tool returned it, or it is simple arithmetic on tool figures:
    amount x quantity (e.g. 12 x $22), then sums/differences of up to three of those
    (e.g. $840 + $2,400 + $264 = $3,504, or $3,400 - $3,504 = -$104)."""
    base = {round(m, 2) for m in ev["money"]}
    base |= {round(m * q, 2) for m in ev["money"] for q in ev["qtys"]}
    base |= {round((a - b) * q, 2) for a in ev["money"] for b in ev["money"] if a > b for q in ev["qtys"]}
    pairs = {round(a + b, 2) for a in base for b in base} | {round(a - b, 2) for a in base for b in base}
    targets = {round(value, 2), round(-value, 2)}  # "$104 short" is a negative balance said positively
    for t in targets:
        if t in base or t in pairs:
            return True
        if any(round(t - c, 2) in pairs or round(c - t, 2) in pairs for c in base):
            return True
    return False


def _date_grounded(value: str, ev: dict[str, set]) -> bool:
    if value in ev["dates"]:
        return True
    from datetime import date, timedelta
    try:
        target = date.fromisoformat(value)
        return any(date.fromisoformat(d) + timedelta(days=n) == target for d in ev["dates"] for n in ev["days"])
    except ValueError:
        return False


def _grounding_check(ctx: RunContext[TeamDeps], output):
    """Output validator on every agent: refuse a report that cites anything the tools never said."""
    ev = _evidence(ctx.deps)
    data = output.model_dump()
    problems: list[str] = []

    claimed_approvals = set(data.get("approvals_requested", []) or []) | set(data.get("approvals_waiting_on_human", []) or [])
    for t in data.get("tickets", []) or []:
        claimed_approvals |= set(t.get("approvals_requested", []) or [])
    if missing := sorted(claimed_approvals - ev["approval_ids"]):
        problems.append(f"approval id(s) {missing} were never returned by request_payment / request_discount / "
                        "draft_purchase_order / list_approvals / get_ticket in this run")
    claimed_drafts = set(data.get("drafts_created", []) or [])
    for t in data.get("tickets", []) or []:
        claimed_drafts |= set(t.get("drafts_created", []) or [])
    if missing := sorted(claimed_drafts - ev["draft_ids"]):
        problems.append(f"draft id(s) {missing} were never returned by draft_message / get_ticket in this run")

    for key in ("cash_now", "cash_if_all_pending_approved"):
        if key in data and not _money_grounded(round(float(data[key]), 2), ev):
            problems.append(f"{key}={data[key]} does not match any cash figure from the tools")

    for key, text in _walk(data):
        if not isinstance(text, str):
            continue
        for m in MONEY.findall(text):
            amount = round(float(m.replace(",", "")), 2)
            if not _money_grounded(amount, ev):
                problems.append(f"${m} in `{key}` has no source in any tool result")
        for d in ISO_DATE.findall(text):
            if not _date_grounded(d, ev):
                problems.append(f"date {d} in `{key}` is not a tool date (or tool date + lead_days)")
        if hit := SENT_CLAIM.search(text):
            problems.append(f"`{key}` says '{hit.group(0)}'. Nothing is ever sent, emailed or called; "
                            "messages are drafts on the board for a human")

    if problems:
        problems = sorted(set(problems))
        if ctx.retry >= ctx.max_retries:
            # Out of retries: don't crash the desk run. Let the report through, but stamp every
            # unverified item onto it where the human will see it, and record that in the audit.
            _event(ctx.deps, "guardrail", ctx.deps.me, target="grounding_check", status="error",
                   detail={"problems": problems, "action": "accepted with UNVERIFIED flags after final retry"})
            flags = [f"UNVERIFIED (guardrail): {p}" for p in problems]
            if isinstance(output, DeskReport):
                output.cross_ticket_notes.extend(flags)
            else:
                output.blockers.extend(flags)
            return output
        _event(ctx.deps, "guardrail", ctx.deps.me, target="grounding_check", status="refused",
               detail={"problems": problems, "retry": ctx.retry + 1, "max_retries": ctx.max_retries})
        raise ModelRetry("Guardrail: your report cites things no tool returned. Fix these, using only tool "
                         "results (call the tool again if you need the number):\n- " + "\n- ".join(problems))
    return output


# ── Model and MCP connection ──────────────────────────────────────────

def build_model() -> OpenAIChatModel:
    """Portkey-served chat model (same setup as hw4): PORTKEY_API_KEY + MODEL_NAME in .env."""
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is not set. Add it to hw5/.env (see .env.example).")
    from openai import AsyncOpenAI

    client = AsyncOpenAI(base_url=PORTKEY_BASE_URL, api_key=api_key, timeout=MODEL_TIMEOUT_S, max_retries=3)
    return OpenAIChatModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


async def _audit_tool_call(ctx: RunContext[TeamDeps], call_tool: CallToolFunc, name: str, args: dict[str, Any]):
    """Every MCP call goes through here: stamp the real agent name, then log call + result."""
    if OUTBOUND_TOOL.search(name):
        reason = f"`{name}` looks like outbound contact (email/text/call). The team never contacts anyone; use draft_message."
        _event(ctx.deps, "guardrail", ctx.deps.me, target=name, status="refused", detail={"args": args, "reason": reason})
        return {"found": False, "error": reason}
    args = dict(args)
    for key in AUTHOR_ARGS:
        if key in args:
            args[key] = ctx.deps.me
    _event(ctx.deps, "tool_call", ctx.deps.me, target=name, detail={"args": args})
    started = time.perf_counter()
    try:
        result = await call_tool(name, args)
    except Exception as exc:
        _event(ctx.deps, "tool_result", ctx.deps.me, target=name, status="error", duration_ms=_ms(started),
               detail={"error": f"{type(exc).__name__}: {exc}"})
        raise
    _event(ctx.deps, "tool_result", ctx.deps.me, target=name, status=_tool_status(result),
           duration_ms=_ms(started), detail={"result": result})
    return result


def build_toolset() -> MCPToolset:
    """One stdio connection to mcp_server/server.py, pointed at the working DB."""
    db = os.getenv("CAMPUS_DB_PATH", "data/campus_customs_new.db")
    db_path = Path(db) if Path(db).is_absolute() else ROOT / db
    transport = PythonStdioTransport(
        ROOT / "mcp_server" / "server.py",
        env={**os.environ, "CAMPUS_DB_PATH": str(db_path)},
        cwd=str(ROOT),
        python_cmd=sys.executable,
    )
    return MCPToolset(Client(transport), id="campus-customs", process_tool_call=_audit_tool_call)


# ── The team ──────────────────────────────────────────────────────────

class Team:
    """Builds the five agents over one shared MCP toolset."""

    def __init__(self, model: OpenAIChatModel | None = None, toolset: MCPToolset | None = None,
                 audit: Callable[[AuditEvent], None] | None = None):
        self.model = model or build_model()
        self.toolset = toolset or build_toolset()
        self.audit = audit or AuditLog()
        self.agents: dict[AgentName, Agent[TeamDeps, Any]] = {name: self._build(name) for name in AGENT_NAMES}

    def _build(self, name: AgentName) -> Agent[TeamDeps, Any]:
        allowed = AGENT_TOOLS[name]
        agent: Agent[TeamDeps, Any] = Agent(
            self.model,
            name=name,
            deps_type=TeamDeps,
            output_type=DeskReport if name == "boss" else AgentReport,
            instructions=(PROMPTS / f"{name}.md").read_text(),
            toolsets=[self.toolset.filtered(lambda ctx, tool_def: tool_def.name in allowed)],
            retries=3,
            model_settings={"timeout": MODEL_TIMEOUT_S},
        )
        agent.output_validator(_grounding_check)

        @agent.instructions
        def where_am_i(ctx: RunContext[TeamDeps]) -> str:
            others = ", ".join(f"`{n}` ({PERSONAS[n]})" for n in AGENT_NAMES if n != ctx.deps.me)
            chain = " -> ".join(PERSONAS[n] for n in ctx.deps.chain)
            asker = (f"{PERSONAS[ctx.deps.chain[-2]]} handed you this task, so your `in_character` line is spoken "
                     f"TO {PERSONAS[ctx.deps.chain[-2]]}, by name. "
                     if len(ctx.deps.chain) > 1 else "The desk itself handed you this run. ")
            return (f"You are {PERSONAS[ctx.deps.me]} (`{ctx.deps.me}`). Request chain so far: {chain}. {asker}"
                    f"You can delegate to: {others}, but not to anyone already in the chain. "
                    "Use the role name in `delegate(to=...)`.")

        @agent.tool
        async def delegate(ctx: RunContext[TeamDeps], to: AgentName, task: str) -> dict:
            """Hand a task to a teammate and wait for their report.

            Args:
                to: boss, inventory, accounting, facilities or customer_service.
                task: Open with ONE line spoken in your own character's voice, addressed to them by name
                    (this is what the board shows you saying). Then the precise brief: ticket ids,
                    SKU/size/qty or lease/invoice ids, and exactly what you need back.
            """
            return await self.delegate(ctx, to, task)

        return agent

    async def delegate(self, ctx: RunContext[TeamDeps], to: AgentName, task: str) -> dict:
        me, chain = ctx.deps.me, ctx.deps.chain
        refusal = None
        if to == me:
            refusal = "You can't delegate to yourself; do the work with your own tools."
        elif to in chain:
            refusal = (f"{PERSONAS[to]} is already working on this higher up the chain "
                       f"({' -> '.join(PERSONAS[n] for n in chain)}). "
                       "Put what you need from them in your report's blockers or next_steps instead.")
        elif len(chain) >= MAX_DEPTH:
            refusal = f"Delegation depth limit ({MAX_DEPTH}) reached. Finish with what you have."
        if refusal:
            _event(ctx.deps, "delegate_refused", me, target=to, status="refused",
                   detail={"task": task, "reason": refusal})
            return {"delegated": False, "error": refusal}

        _event(ctx.deps, "delegate", me, target=to, detail={"task": task})
        started = time.perf_counter()
        sub_deps = replace(ctx.deps, chain=[*chain, to], parent_agent_run_id=ctx.deps.agent_run_id)
        output = await self._loop(to, task, sub_deps, usage=ctx.usage)
        report = output.model_dump()
        _event(ctx.deps, "report", to, target=me, status="ok", duration_ms=_ms(started), detail={"report": report})
        return {"delegated": True, "from": to, "report": report}

    async def _loop(self, name: AgentName, task: str, deps: TeamDeps, usage=None):
        """One agent loop, stepped node by node so every model request/response is audited live."""
        deps.agent_run_id, deps.step = uuid.uuid4().hex[:12], 0
        agent = self.agents[name]
        prompt_text = (PROMPTS / f"{name}.md").read_text()
        _event(deps, "agent_start", name, detail={
            "task": task,
            "model": MODEL_NAME,
            "prompt_file": f"backend/prompts/{name}.md",
            "prompt_sha256": hashlib.sha256(prompt_text.encode()).hexdigest()[:16],
            "tools": sorted(AGENT_TOOLS[name] | {"delegate"}),
            "output_type": "DeskReport" if name == "boss" else "AgentReport",
        })
        started = time.perf_counter()
        step_started = started
        try:
            async with agent.iter(task, deps=deps, usage=usage, usage_limits=RUN_LIMITS) as run:
                async for node in run:
                    if Agent.is_model_request_node(node):
                        deps.step += 1
                        step_started = time.perf_counter()
                        _event(deps, "model_request", name, detail=_describe_request(node.request))
                    elif Agent.is_call_tools_node(node):
                        _event(deps, "model_response", name, status="ok", duration_ms=_ms(step_started),
                               detail=_describe_response(node.model_response))
            output = run.result.output
        except Exception as exc:
            _event(deps, "agent_error", name, status="error", duration_ms=_ms(started),
                   detail={"error": f"{type(exc).__name__}: {exc}", "usage_so_far": _usage(usage) if usage else None})
            raise
        _event(deps, "agent_end", name, status="ok", duration_ms=_ms(started),
               detail={"steps": deps.step, "output": output.model_dump(), "usage_so_far": _usage(run.usage)})
        return output

    async def run(self, ticket_ids: list[int] | None = None, start: AgentName = "boss",
                  prompt: str | None = None, run_id: str | None = None, fresh: bool = False) -> TeamRun:
        """Run the desk. By default the Boss takes every open ticket; pass ticket ids to narrow it,
        or `start` + `prompt` to hand a task straight to one specialist."""
        if prompt is None:
            prompt = (f"Work tickets {', '.join(map(str, ticket_ids))}. Read every open ticket first so you "
                      "can see cross-ticket dependencies, but only resolve these."
                      if ticket_ids else "Work every open ticket on the desk.")
        deps = TeamDeps(chain=[start], run_id=run_id or uuid.uuid4().hex[:12], sink=self.audit)
        usage = RunUsage()
        if start == "boss":
            roll_out()
        _event(deps, "run_start", start, detail={
            "prompt": prompt, "ticket_ids": ticket_ids or [], "model": MODEL_NAME,
            "db": os.getenv("CAMPUS_DB_PATH", "data/campus_customs_new.db"), "max_depth": MAX_DEPTH,
            "request_limit": RUN_LIMITS.request_limit, "fresh_db": fresh,
        })
        started = time.perf_counter()
        try:
            async with self.toolset:
                output = await self._loop(start, prompt, deps, usage=usage)
        except Exception as exc:
            _event(deps, "run_end", start, status="error", duration_ms=_ms(started),
                   detail={"error": f"{type(exc).__name__}: {exc}", "usage": _usage(usage)})
            raise
        _event(deps, "run_end", start, status="ok", duration_ms=_ms(started),
               detail={"output": output.model_dump(), "usage": _usage(usage)})
        return TeamRun(
            model=MODEL_NAME,
            ticket_ids=ticket_ids or [],
            run_id=deps.run_id,
            output=output,
            trace=deps.trace,
            usage=_usage(usage),
        )


async def run_desk(ticket_ids: list[int] | None = None) -> TeamRun:
    return await Team().run(ticket_ids)


if __name__ == "__main__":
    ids = [int(a) for a in sys.argv[1:]]
    run = asyncio.run(run_desk(ids or None))
    print(json.dumps(run.model_dump(mode="json"), indent=2, default=str))
