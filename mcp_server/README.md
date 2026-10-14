# Campus Customs MCP server

**What it's for:** the agent team (Boss, Inventory, Accounting, Facilities and Customer Service) reads the shop's database only through this server. The tools return only what is in the database. If something isn't there, the tool returns `found: false` with an error instead of a guess. "Today" always comes from `desk.date_today`, never the computer's clock.

**Database:** `data/campus_customs_new.db`, the working copy. You can override it with `CAMPUS_DB_PATH` in `.env`. The original `data/campus_customs.db` is never opened. To reset:
`cp data/campus_customs.db data/campus_customs_new.db`

**Run** (from the `hw5/` root):
```bash
.venv/bin/python mcp_server/server.py
```
It uses stdio transport and is built with FastMCP (`fastmcp` package). `.mcp.json` registers it as `campus-customs`.

## Tools

### Read
| Tool | Arguments | Reads | Returns |
|---|---|---|---|
| `check_stock` | `sku`, `size`, `qty_needed` (optional) | `inventory`, `pricing` | Units on hand, aisle, unit cost, list price, and the shortfall vs. `qty_needed` |
| `vendor_status` | `vendor_id` or `specialty` (optional) | `vendors`, `invoices`, `desk` | Lead days, open invoices with days overdue, open balance, and `can_ship` (false while any invoice is open) |
| `lease_and_cash_status` | `lease_id` | `leases`, `cash_accounts`, `desk` | Rent, next due date, days until due, cash on hand, and whether cash covers the rent |
| `get_ticket` | `ticket_id` | `tickets`, `approvals`, `drafts` | The ticket plus any approvals and drafts already filed against it |
| `list_open_tickets` | none | `tickets` | Every ticket that isn't resolved |
| `list_approvals` | `status` (default `pending`) | `approvals`, `cash_accounts` | The queue, plus cash now and cash if every pending item is approved |

### Request (agents queue work, and no money moves)
| Tool | What it does | Refuses when |
|---|---|---|
| `request_payment` | Queues an invoice or rent payment. The amount is read from the DB. One pending request per bill | The bill is already paid, or cash would go below 0 |
| `request_discount` | Suggests a bulk price and reports the margin. From accounting it goes straight to the human; from anyone else it waits for Megatron's sign-off | The price is at or below `unit_cost` |
| `draft_purchase_order` | Queues a restock PO (qty × unit_cost, ETA = today + `lead_days`) | Unknown vendor or SKU. It is flagged `vendor_can_ship: false` while the vendor has an open invoice |
| `draft_message` | Saves a message to a customer, landlord, or club as a draft on the board. **Never sent** | n/a |
| `update_ticket` | Sets the status and appends a dated note | Marking a ticket `resolved` while it has a pending approval |
| `hold_stock` | Reserves units for a ticket, pending dispatch (`stock_holds`). `check_stock` then shows `qty_held` / `qty_available` | Holding more than is available |

### Sign-off (Megatron only)
| Tool | What it does |
|---|---|
| `sign_off_discount` | Signs off or rejects a discount suggested by anyone other than accounting. Signing off moves it from `awaiting_signoff` to `pending` (the human's queue). Refuses any caller but `accounting` |

### Human only
| Tool | What it does |
|---|---|
| `decide_approval` | Approve or reject a queued item with a person's name. Approving a payment/PO writes `payments` (`approved_by` = that person), debits checking, and marks the invoice `paid` or moves the lease `next_due` forward one month. Refuses if cash would go below 0, or if a PO's vendor still has an open invoice. **No agent is given this tool**; the backend calls it when someone clicks approve on the board. |

The request tools add three tables to the **working copy only**: `approvals`, `drafts` and `stock_holds`. They are created on first connect, and the reset command above clears them.
