"""Campus Customs MCP server — shop tools over the working DB.

Every agent on the operations team reaches the database through these tools.
Tools only report what is in the database: anything missing comes back as
`found: False` with an error message, never a guessed value.

Read tools: check_stock, vendor_status, lease_and_cash_status, get_ticket, list_open_tickets,
list_approvals.
Request tools (agents): request_payment, request_discount, draft_purchase_order,
draft_message, update_ticket, hold_stock. These only queue or reserve work; no money moves.
Sign-off tool (Megatron/accounting only): sign_off_discount. A discount suggested by anyone
other than accounting waits for his sign-off before it reaches the human queue.
Human-only tool: decide_approval. The backend calls it when a person clicks
approve/reject on the board; it is never handed to an agent.

Run:  .venv/bin/python mcp_server/server.py
"""

import os
import calendar
import sqlite3
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import FastMCP

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

_db_setting = Path(os.getenv("CAMPUS_DB_PATH", "data/campus_customs_new.db"))
DB_PATH = _db_setting if _db_setting.is_absolute() else ROOT / _db_setting

mcp = FastMCP("campus-customs")


def _connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Working DB not found at {DB_PATH}. "
            "Copy data/campus_customs.db to data/campus_customs_new.db first."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure_desk_tables(conn)
    return conn


def _ensure_desk_tables(conn: sqlite3.Connection) -> None:
    """Work-queue tables the team adds to the working copy (the original DB is never touched).

    `approvals` holds every money or price decision waiting for a human.
    `drafts` holds outgoing messages; they stay on the board and are never sent.
    """
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS approvals (
            id INTEGER PRIMARY KEY,
            ticket_id INTEGER,
            kind TEXT NOT NULL,            -- invoice | rent | purchase_order | discount
            ref_id INTEGER,                -- invoices.id / leases.id / vendors.id
            amount REAL NOT NULL,          -- cash out (0 for a discount)
            details TEXT,                  -- what exactly is being approved
            requested_by TEXT NOT NULL,    -- agent name
            status TEXT NOT NULL DEFAULT 'pending',  -- awaiting_signoff | pending | approved | rejected
            signed_off_by TEXT,            -- accounting, for discounts (Megatron's sign-off)
            decided_by TEXT,
            decided_at TEXT,
            payment_id INTEGER,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS stock_holds (
            id INTEGER PRIMARY KEY,
            ticket_id INTEGER,
            sku TEXT NOT NULL,
            size TEXT NOT NULL,
            qty INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'held',   -- held | released | dispatched
            held_by TEXT NOT NULL,
            note TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS drafts (
            id INTEGER PRIMARY KEY,
            ticket_id INTEGER,
            recipient TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            author TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    cols = {r[1] for r in conn.execute("PRAGMA table_info(approvals)")}
    if "signed_off_by" not in cols:  # working copies made before sign-off existed
        conn.execute("ALTER TABLE approvals ADD COLUMN signed_off_by TEXT")
        conn.commit()


OPEN_APPROVAL = ("awaiting_signoff", "pending")


def _held(conn: sqlite3.Connection, sku: str, size: str) -> int:
    return conn.execute(
        "SELECT COALESCE(SUM(qty), 0) FROM stock_holds WHERE sku = ? AND size = ? AND status = 'held'", (sku, size)
    ).fetchone()[0]


def _shop_today(conn: sqlite3.Connection) -> date:
    """The shop's 'today' is desk.date_today, not the system clock."""
    return date.fromisoformat(conn.execute("SELECT date_today FROM desk").fetchone()["date_today"])


@mcp.tool
def check_stock(sku: str, size: str, qty_needed: int = 0) -> dict:
    """Look up units on hand for one SKU and size, plus that SKU's unit cost and list price.

    Pass qty_needed to get the shortfall (units missing to fill the request).
    Use for customer orders and bulk / discount requests.
    """
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT i.sku, i.name, i.size, i.qty, i.location, p.unit_cost, p.list_price "
            "FROM inventory i LEFT JOIN pricing p ON p.sku = i.sku "
            "WHERE i.sku = ? AND i.size = ?",
            (sku, size),
        ).fetchone()
        if row is None:
            sizes = [r["size"] for r in conn.execute("SELECT size FROM inventory WHERE sku = ?", (sku,))]
            return {
                "found": False,
                "error": f"No inventory row for sku={sku!r} size={size!r}.",
                "sizes_on_file_for_sku": sizes,
            }

        held = _held(conn, sku, size)
    on_hand = row["qty"]
    result = {
        "found": True,
        "sku": row["sku"],
        "name": row["name"],
        "size": row["size"],
        "qty_on_hand": on_hand,
        "qty_held": held,
        "qty_available": on_hand - held,
        "location": row["location"],
        "unit_cost": row["unit_cost"],
        "list_price": row["list_price"],
    }
    if qty_needed:
        result["qty_needed"] = qty_needed
        result["shortfall"] = max(qty_needed - (on_hand - held), 0)
        result["can_fill_from_stock"] = on_hand - held >= qty_needed
    return result


@mcp.tool
def vendor_status(vendor_id: int | None = None, specialty: str | None = None) -> list[dict]:
    """Show vendors with their lead time and any unpaid invoices.

    Filter by vendor_id, or by a word in their specialty (e.g. "apparel", "mugs");
    with no filter, all vendors are returned. A vendor with an open invoice will not
    ship new product, so `can_ship` is False until every open invoice is paid.
    Overdue is measured against desk.date_today.
    """
    with closing(_connect()) as conn:
        today = _shop_today(conn)
        sql, params = "SELECT id, name, specialty, lead_days FROM vendors", ()
        if vendor_id is not None:
            sql, params = sql + " WHERE id = ?", (vendor_id,)
        elif specialty:
            sql, params = sql + " WHERE specialty LIKE ?", (f"%{specialty}%",)
        vendors = conn.execute(sql + " ORDER BY id", params).fetchall()
        if not vendors:
            return [{"found": False, "error": f"No vendor matches vendor_id={vendor_id!r} specialty={specialty!r}."}]

        results = []
        for v in vendors:
            invoices = []
            for inv in conn.execute(
                "SELECT id, amount, due_date, status, description FROM invoices "
                "WHERE vendor_id = ? AND status = 'open' ORDER BY due_date",
                (v["id"],),
            ):
                days_overdue = (today - date.fromisoformat(inv["due_date"])).days
                invoices.append({
                    "invoice_id": inv["id"],
                    "amount": inv["amount"],
                    "due_date": inv["due_date"],
                    "status": inv["status"],
                    "description": inv["description"],
                    "days_overdue": max(days_overdue, 0),
                })
            results.append({
                "found": True,
                "vendor_id": v["id"],
                "name": v["name"],
                "specialty": v["specialty"],
                "lead_days": v["lead_days"],
                "shop_today": today.isoformat(),
                "open_invoices": invoices,
                "open_balance": sum(i["amount"] for i in invoices),
                "can_ship": not invoices,
            })
    return results


@mcp.tool
def lease_and_cash_status(lease_id: int) -> dict:
    """Show a lease's rent and next due date, days until due (from desk.date_today),
    and whether the cash accounts currently hold enough to cover that rent.
    """
    with closing(_connect()) as conn:
        today = _shop_today(conn)
        lease = conn.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases WHERE id = ?",
            (lease_id,),
        ).fetchone()
        if lease is None:
            return {"found": False, "error": f"No lease with id={lease_id!r}."}
        accounts = [dict(a) for a in conn.execute("SELECT name, balance, date FROM cash_accounts ORDER BY name")]

    days_until_due = (date.fromisoformat(lease["next_due"]) - today).days
    total_cash = sum(a["balance"] for a in accounts)
    return {
        "found": True,
        "lease_id": lease["id"],
        "space_name": lease["space_name"],
        "landlord": lease["landlord"],
        "monthly_rent": lease["monthly_rent"],
        "next_due": lease["next_due"],
        "notes": lease["notes"],
        "shop_today": today.isoformat(),
        "days_until_due": days_until_due,
        "is_overdue": days_until_due < 0,
        "cash_accounts": accounts,
        "total_cash": total_cash,
        "cash_covers_rent": total_cash >= lease["monthly_rent"],
        "cash_after_rent": total_cash - lease["monthly_rent"],
    }


# ── Tickets ───────────────────────────────────────────────────────────

TICKET_STATUSES = ("open", "in_progress", "awaiting_approval", "blocked", "resolved")


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Show one ticket (type, requester, SKU/size/qty, linked lease or invoice, status, notes),
    plus any approvals and drafts already filed against it."""
    with closing(_connect()) as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row is None:
            return {"found": False, "error": f"No ticket with id={ticket_id!r}."}
        approvals = [dict(a) for a in conn.execute("SELECT * FROM approvals WHERE ticket_id = ? ORDER BY id", (ticket_id,))]
        drafts = [dict(d) for d in conn.execute("SELECT * FROM drafts WHERE ticket_id = ? ORDER BY id", (ticket_id,))]
        holds = [dict(h) for h in conn.execute("SELECT * FROM stock_holds WHERE ticket_id = ? ORDER BY id", (ticket_id,))]
        today = _shop_today(conn).isoformat()
    return {"found": True, **dict(row), "shop_today": today, "approvals": approvals, "drafts": drafts,
            "stock_holds": holds}


@mcp.tool
def list_open_tickets() -> list[dict]:
    """List every ticket that is not resolved, oldest first. Use this to see the whole desk at once."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT id, type, requester, subject, sku, size, qty, lease_id, invoice_id, status, notes "
            "FROM tickets WHERE status != 'resolved' ORDER BY created_at, id"
        ).fetchall()
    return [dict(r) for r in rows]


@mcp.tool
def update_ticket(ticket_id: int, status: str, note: str) -> dict:
    """Set a ticket's status (open, in_progress, awaiting_approval, blocked, resolved) and append a note.

    A ticket cannot be marked resolved while one of its approvals is still pending.
    """
    if status not in TICKET_STATUSES:
        return {"found": False, "error": f"status must be one of {TICKET_STATUSES}."}
    with closing(_connect()) as conn:
        row = conn.execute("SELECT notes FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row is None:
            return {"found": False, "error": f"No ticket with id={ticket_id!r}."}
        pending = conn.execute(
            "SELECT COUNT(*) FROM approvals WHERE ticket_id = ? AND status IN ('awaiting_signoff', 'pending')",
            (ticket_id,),
        ).fetchone()[0]
        if status == "resolved" and pending:
            return {"found": True, "updated": False,
                    "error": f"Ticket {ticket_id} still has {pending} pending approval(s); use awaiting_approval."}
        today = _shop_today(conn).isoformat()
        notes = f"{row['notes'] or ''}\n[{today}] {note}".strip()
        with conn:
            conn.execute("UPDATE tickets SET status = ?, notes = ? WHERE id = ?", (status, notes, ticket_id))
    return {"found": True, "updated": True, "ticket_id": ticket_id, "status": status, "notes": notes}


# ── Approval queue (agents request, a human decides) ─────────────────

def _cash(conn: sqlite3.Connection) -> float:
    return sum(r["balance"] for r in conn.execute("SELECT balance FROM cash_accounts"))


def _pending_cash_out(conn: sqlite3.Connection) -> float:
    return conn.execute("SELECT COALESCE(SUM(amount), 0) FROM approvals WHERE status = 'pending'").fetchone()[0]


def _queue(conn, *, ticket_id, kind, ref_id, amount, details, requested_by, status="pending",
           signed_off_by=None) -> dict:
    today = _shop_today(conn).isoformat()
    # One pending approval per bill: invoice #501 blocks two tickets but is paid once.
    # POs and discounts are per ticket.
    if kind in ("invoice", "rent"):
        dup = conn.execute(
            "SELECT id, amount, details, status FROM approvals WHERE kind = ? AND ref_id = ? "
            "AND status IN ('awaiting_signoff', 'pending')",
            (kind, ref_id),
        ).fetchone()
    else:
        dup = conn.execute(
            "SELECT id, amount, details, status FROM approvals WHERE kind = ? AND ref_id IS ? AND ticket_id IS ? "
            "AND status IN ('awaiting_signoff', 'pending')",
            (kind, ref_id, ticket_id),
        ).fetchone()
    if dup:
        approval_id, amount, details, status = dup["id"], dup["amount"], dup["details"], dup["status"]
        created = False
    else:
        with conn:
            cur = conn.execute(
                "INSERT INTO approvals (ticket_id, kind, ref_id, amount, details, requested_by, status, "
                "signed_off_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ticket_id, kind, ref_id, amount, details, requested_by, status, signed_off_by, today),
            )
        approval_id = cur.lastrowid
        created = True
    cash = _cash(conn)
    pending = _pending_cash_out(conn)
    return {
        "found": True,
        "approval_id": approval_id,
        "created": created,
        "status": status,
        "kind": kind,
        "amount": amount,
        "details": details,
        "cash_now": cash,
        "pending_cash_out_total": pending,
        "cash_if_all_pending_approved": cash - pending,
        "note": ("Waiting for Megatron's (accounting) sign-off, then a human. Nothing has been paid."
                 if status == "awaiting_signoff" else "Queued for human approval. Nothing has been paid."),
    }


@mcp.tool
def request_payment(kind: str, ref_id: int, ticket_id: int, requested_by: str, reason: str) -> dict:
    """Queue a payment for human approval. kind is "invoice" (ref_id = invoices.id) or
    "rent" (ref_id = leases.id). ticket_id is required: the ticket this payment resolves.
    The amount is read from the database, never typed in.

    Refuses if the item is already paid, or if paying it would take cash below zero.
    The reply shows cash left if every pending approval goes through, so conflicts are visible.
    """
    with closing(_connect()) as conn:
        if conn.execute("SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)).fetchone() is None:
            return {"found": False, "error": f"No ticket with id={ticket_id!r}; pass the ticket this payment is for."}
        if kind == "invoice":
            inv = conn.execute("SELECT * FROM invoices WHERE id = ?", (ref_id,)).fetchone()
            if inv is None:
                return {"found": False, "error": f"No invoice with id={ref_id!r}."}
            if inv["status"] != "open":
                return {"found": True, "queued": False, "error": f"Invoice {ref_id} is already {inv['status']}."}
            amount = inv["amount"]
            details = f"Pay invoice #{ref_id} (vendor {inv['vendor_id']}): {inv['description']}. {reason}"
        elif kind == "rent":
            lease = conn.execute("SELECT * FROM leases WHERE id = ?", (ref_id,)).fetchone()
            if lease is None:
                return {"found": False, "error": f"No lease with id={ref_id!r}."}
            amount = lease["monthly_rent"]
            details = f"Pay rent for lease #{ref_id} ({lease['space_name']}) due {lease['next_due']} to {lease['landlord']}. {reason}"
        else:
            return {"found": False, "error": 'kind must be "invoice" or "rent".'}
        if _cash(conn) - amount < 0:
            return {"found": True, "queued": False,
                    "error": f"Paying ${amount:,.2f} would take cash below zero (cash ${_cash(conn):,.2f})."}
        return _queue(conn, ticket_id=ticket_id, kind=kind, ref_id=ref_id, amount=amount,
                      details=details, requested_by=requested_by)


@mcp.tool
def request_discount(ticket_id: int, sku: str, qty: int, unit_price: float, requested_by: str, reason: str) -> dict:
    """Suggest a bulk / custom price. Refuses any unit_price at or below the SKU's unit_cost
    (the shop never sells at a loss) and returns the margin the price leaves.

    From accounting it goes straight to the human queue (his sign-off is implied). From anyone
    else it waits as `awaiting_signoff` until accounting calls sign_off_discount.
    """
    with closing(_connect()) as conn:
        p = conn.execute("SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if p is None:
            return {"found": False, "error": f"No pricing row for sku={sku!r}."}
        if unit_price <= p["unit_cost"]:
            return {"found": True, "queued": False,
                    "error": f"${unit_price:.2f} is at or below unit cost ${p['unit_cost']:.2f}."}
        margin = unit_price - p["unit_cost"]
        details = (f"{qty} x {sku} at ${unit_price:.2f} (list ${p['list_price']:.2f}, "
                   f"{(1 - unit_price / p['list_price']) * 100:.0f}% off; margin ${margin:.2f}/unit, "
                   f"{margin / unit_price * 100:.0f}%). {reason}")
        by_accounting = requested_by == "accounting"
        out = _queue(conn, ticket_id=ticket_id, kind="discount", ref_id=None, amount=0.0,
                     details=details, requested_by=requested_by,
                     status="pending" if by_accounting else "awaiting_signoff",
                     signed_off_by="accounting" if by_accounting else None)
    out.update({"unit_cost": p["unit_cost"], "list_price": p["list_price"], "unit_price": unit_price,
                "margin_per_unit": margin, "order_total": unit_price * qty})
    return out


@mcp.tool
def draft_purchase_order(vendor_id: int, sku: str, size: str, qty: int, ticket_id: int,
                         requested_by: str, reason: str) -> dict:
    """Queue a restock purchase order for human approval. Cost = qty x the SKU's unit_cost.

    The PO is drafted even if the vendor has an open invoice, but it is flagged
    `vendor_can_ship: False` and cannot be approved until that invoice is paid.
    Expected arrival = shop today + vendor lead_days (counted from approval).
    Nothing is sent to the vendor.
    """
    with closing(_connect()) as conn:
        v = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        if v is None:
            return {"found": False, "error": f"No vendor with id={vendor_id!r}."}
        p = conn.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if p is None:
            return {"found": False, "error": f"No pricing row for sku={sku!r}."}
        if conn.execute("SELECT 1 FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone() is None:
            return {"found": False, "error": f"No inventory row for sku={sku!r} size={size!r}."}
        open_inv = [r["id"] for r in conn.execute(
            "SELECT id FROM invoices WHERE vendor_id = ? AND status = 'open'", (vendor_id,))]
        amount = qty * p["unit_cost"]
        arrival = _shop_today(conn) + timedelta(days=v["lead_days"])
        details = (f"PO to {v['name']}: {qty} x {sku} size {size} at ${p['unit_cost']:.2f} = ${amount:,.2f}; "
                   f"lead {v['lead_days']} days, earliest arrival {arrival.isoformat()}. {reason}")
        out = _queue(conn, ticket_id=ticket_id, kind="purchase_order", ref_id=vendor_id, amount=amount,
                     details=details, requested_by=requested_by)
    out.update({"vendor": v["name"], "lead_days": v["lead_days"], "earliest_arrival": arrival.isoformat(),
                "vendor_can_ship": not open_inv, "blocking_invoices": open_inv})
    return out


@mcp.tool
def draft_message(ticket_id: int, recipient: str, subject: str, body: str, author: str) -> dict:
    """Save a draft message (to a customer, landlord or vendor) on the board. It is NEVER sent;
    a human reads and sends it themselves."""
    with closing(_connect()) as conn:
        today = _shop_today(conn).isoformat()
        with conn:
            cur = conn.execute(
                "INSERT INTO drafts (ticket_id, recipient, subject, body, author, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (ticket_id, recipient, subject, body, author, today),
            )
    return {"found": True, "draft_id": cur.lastrowid, "ticket_id": ticket_id, "recipient": recipient,
            "sent": False, "note": "Saved as a draft on the board. Not sent."}


@mcp.tool
def list_approvals(status: str | None = "pending") -> dict:
    """List approvals with current cash and what cash would be if every pending approval went through.

    status: "pending" (default, waiting on a human), "awaiting_signoff" (waiting on Megatron),
    "open" (both), "approved", "rejected", or null for all.
    """
    with closing(_connect()) as conn:
        sql, params = "SELECT * FROM approvals", ()
        if status == "open":
            sql += " WHERE status IN ('awaiting_signoff', 'pending')"
        elif status:
            sql, params = sql + " WHERE status = ?", (status,)
        rows = [dict(r) for r in conn.execute(sql + " ORDER BY id", params)]
        cash, pending = _cash(conn), _pending_cash_out(conn)
    return {"approvals": rows, "cash_now": cash, "pending_cash_out_total": pending,
            "cash_if_all_pending_approved": cash - pending}


@mcp.tool
def sign_off_discount(approval_id: int, decision: str, signed_off_by: str, note: str = "") -> dict:
    """ACCOUNTING (Megatron) ONLY. Sign off or reject a discount someone else suggested.

    decision "sign_off" moves it from awaiting_signoff to pending (the human approves next);
    "reject" closes it. The price was already checked against cost when it was suggested.
    """
    if signed_off_by != "accounting":
        return {"found": False, "error": "Only accounting (Megatron) can sign off discounts."}
    if decision not in ("sign_off", "reject"):
        return {"found": False, "error": 'decision must be "sign_off" or "reject".'}
    with closing(_connect()) as conn:
        a = conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        if a is None:
            return {"found": False, "error": f"No approval with id={approval_id!r}."}
        if a["kind"] != "discount" or a["status"] != "awaiting_signoff":
            return {"found": True, "signed_off": False,
                    "error": f"Approval {approval_id} is a {a['kind']} with status {a['status']}; "
                             "only discounts awaiting sign-off can be signed off."}
        today = _shop_today(conn).isoformat()
        details = f"{a['details']} Megatron: {note}".strip() if note else a["details"]
        with conn:
            if decision == "sign_off":
                conn.execute("UPDATE approvals SET status='pending', signed_off_by=?, details=? WHERE id=?",
                             (signed_off_by, details, approval_id))
            else:
                conn.execute("UPDATE approvals SET status='rejected', decided_by=?, decided_at=?, details=? WHERE id=?",
                             (signed_off_by, today, details, approval_id))
    return {"found": True, "signed_off": decision == "sign_off", "approval_id": approval_id,
            "status": "pending" if decision == "sign_off" else "rejected",
            "note": "Signed off by Megatron; now waiting for a human." if decision == "sign_off"
                    else "Rejected by Megatron."}


@mcp.tool
def hold_stock(ticket_id: int, sku: str, size: str, qty: int, requested_by: str, note: str = "") -> dict:
    """Reserve units on the shelf for a ticket, pending dispatch (e.g. while a customer decides).

    Nothing leaves the shelf: inventory.qty is unchanged, but check_stock shows the units as held
    and no longer available to other orders. Refuses to hold more than is available.
    One hold per ticket + SKU + size; calling again updates its quantity.
    """
    if qty <= 0:
        return {"found": False, "error": "qty must be at least 1."}
    with closing(_connect()) as conn:
        row = conn.execute("SELECT qty, location FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone()
        if row is None:
            return {"found": False, "error": f"No inventory row for sku={sku!r} size={size!r}."}
        existing = conn.execute(
            "SELECT id, qty FROM stock_holds WHERE ticket_id IS ? AND sku = ? AND size = ? AND status = 'held'",
            (ticket_id, sku, size),
        ).fetchone()
        available = row["qty"] - _held(conn, sku, size) + (existing["qty"] if existing else 0)
        if qty > available:
            return {"found": True, "held": False,
                    "error": f"Only {available} of {sku} {size} available to hold (asked for {qty})."}
        today = _shop_today(conn).isoformat()
        with conn:
            if existing:
                conn.execute("UPDATE stock_holds SET qty = ?, note = ? WHERE id = ?", (qty, note, existing["id"]))
                hold_id = existing["id"]
            else:
                cur = conn.execute(
                    "INSERT INTO stock_holds (ticket_id, sku, size, qty, held_by, note, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (ticket_id, sku, size, qty, requested_by, note, today),
                )
                hold_id = cur.lastrowid
    return {"found": True, "held": True, "hold_id": hold_id, "ticket_id": ticket_id, "sku": sku, "size": size,
            "qty_held": qty, "location": row["location"], "status": "held",
            "note": "Reserved, pending dispatch. Nothing has left the shelf."}


def _add_month(d: date) -> date:
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return d.replace(year=year, month=month, day=min(d.day, calendar.monthrange(year, month)[1]))


@mcp.tool
def decide_approval(approval_id: int, decision: str, decided_by: str) -> dict:
    """HUMAN ONLY. Approve or reject one queued item. decided_by must be a person's name.

    Approving a payment or PO writes a `payments` row (approved_by = decided_by), debits
    checking, and updates the source row: invoice -> paid, lease next_due -> +1 month.
    Refuses if cash would go below zero, or if a PO's vendor still has an open invoice.
    """
    if decision not in ("approve", "reject"):
        return {"found": False, "error": 'decision must be "approve" or "reject".'}
    if not decided_by.strip():
        return {"found": False, "error": "decided_by (the human approver) is required."}
    with closing(_connect()) as conn:
        a = conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        if a is None:
            return {"found": False, "error": f"No approval with id={approval_id!r}."}
        if a["status"] != "pending":
            return {"found": True, "decided": False, "error": f"Approval {approval_id} is already {a['status']}."}
        today = _shop_today(conn).isoformat()
        if decision == "reject":
            with conn:
                conn.execute("UPDATE approvals SET status='rejected', decided_by=?, decided_at=? WHERE id=?",
                             (decided_by, today, approval_id))
            return {"found": True, "decided": True, "approval_id": approval_id, "status": "rejected"}

        payment_id = None
        if a["kind"] in ("invoice", "rent", "purchase_order"):
            if a["kind"] == "invoice":
                inv = conn.execute("SELECT status FROM invoices WHERE id = ?", (a["ref_id"],)).fetchone()
                if inv is None or inv["status"] != "open":
                    return {"found": True, "decided": False, "error": f"Invoice {a['ref_id']} is not open."}
            if a["kind"] == "purchase_order":
                blocking = [r["id"] for r in conn.execute(
                    "SELECT id FROM invoices WHERE vendor_id = ? AND status = 'open'", (a["ref_id"],))]
                if blocking:
                    return {"found": True, "decided": False,
                            "error": f"Vendor {a['ref_id']} won't ship until invoice(s) {blocking} are paid."}
            acct = conn.execute("SELECT name, balance FROM cash_accounts WHERE name = 'checking'").fetchone()
            if acct is None or acct["balance"] - a["amount"] < 0:
                bal = acct["balance"] if acct else 0
                return {"found": True, "decided": False,
                        "error": f"Refused: ${a['amount']:,.2f} would take checking (${bal:,.2f}) below zero."}
            with conn:
                cur = conn.execute(
                    "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
                    (a["kind"], a["ref_id"], a["amount"], "checking", today, decided_by),
                )
                payment_id = cur.lastrowid
                conn.execute("UPDATE cash_accounts SET balance = balance - ?, date = ? WHERE name = 'checking'",
                             (a["amount"], today))
                if a["kind"] == "invoice":
                    conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (a["ref_id"],))
                elif a["kind"] == "rent":
                    due = conn.execute("SELECT next_due FROM leases WHERE id = ?", (a["ref_id"],)).fetchone()["next_due"]
                    conn.execute("UPDATE leases SET next_due = ? WHERE id = ?",
                                 (_add_month(date.fromisoformat(due)).isoformat(), a["ref_id"]))
                conn.execute("UPDATE approvals SET status='approved', decided_by=?, decided_at=?, payment_id=? WHERE id=?",
                             (decided_by, today, payment_id, approval_id))
        else:  # discount: approving records the decision only, no cash moves
            with conn:
                conn.execute("UPDATE approvals SET status='approved', decided_by=?, decided_at=? WHERE id=?",
                             (decided_by, today, approval_id))
        cash = _cash(conn)
    return {"found": True, "decided": True, "approval_id": approval_id, "status": "approved",
            "payment_id": payment_id, "cash_now": cash}


if __name__ == "__main__":
    mcp.run(show_banner=False)
