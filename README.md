# hw5 · Campus Customs Operations Desk

A multi-agent operations desk for Campus Customs. The team is five Pydantic AI agents built as Transformers. They work the shop's open tickets through an MCP server over the shop database, and every payment, purchase order and discount waits for a human to approve it.

| Role | Agent | Job |
|---|---|---|
| `boss` | **Optimus Prime** | Reads the whole desk, routes tickets, settles arguments, steps in himself when needed. Opens every run by saying "Autobots, roll out!" out loud |
| `inventory` | **Ratchet** | Stock by SKU/size, restock vendors, lead times, purchase-order drafts |
| `accounting` | **Megatron** | Cash, invoices, margins, payment and discount requests. Pushes back on Prime when the shop is running out of money |
| `facilities` | **Ironhide** | The Chapel Street lease, the landlord, rent |
| `customer_service` | **Bumblebee** | Every message to customers, clubs and the landlord. Talks only in famous quotes, and messages are drafts only |

Any agent can delegate to any other (`delegate(to, task)`). Loop guards stop cycles: no delegating to anyone already in the chain, at most 4 deep, and 120 model requests per run.

## Layout
```
hw5/
├── AI_prompts.md              every prompt, word for word, under its ## Problem N heading
├── requirements.txt           Python dependencies (MCP server, agents, backend)
├── .env.example               PORTKEY_API_KEY, MODEL_NAME, PORTKEY_BASE_URL, DB paths (no real keys)
├── .gitignore
├── .mcp.json                  registers the MCP server as `campus-customs` (for Claude Code)
├── README.md
├── data/
│   ├── campus_customs.db      the original: never written
│   └── campus_customs_new.db  the working copy the agents read and write
├── mcp_server/
│   ├── server.py              the 14 MCP tools over the working DB
│   └── README.md
├── frontend/                  React + Vite + TypeScript board (Transformers × Yale)
├── backend/
│   ├── main.py                FastAPI routes: tickets, runs, live agent events, human approvals, cash, reset
│   ├── models.py              data types: AgentReport, DeskReport, TicketResolution, AuditEvent, API models
│   ├── agents.py              the agent team: model, MCP connection, delegation, agent loops, guardrails, audit
│   └── prompts/
│       ├── boss.md            Optimus Prime
│       ├── inventory.md       Ratchet
│       ├── accounting.md      Megatron
│       ├── facilities.md      Ironhide
│       └── customer_service.md  Bumblebee
└── output/
    ├── harness.md             tables, tools, the five agents, MCP, API routes, dashboard, safety rules
    ├── mcp_smoke.json         Problem 4 smoke test of the MCP tools
    ├── desk_tickets.html      expected vs. actual per ticket, plus Cash and Reflections (double-click to open)
    ├── design.md              the dashboard's layout and design decisions
    ├── resolved_tickets.json  per ticket: outcome, final status, each agent's contribution, human approvals
    ├── resolved_board.html    screenshots of each resolved ticket on the dashboard (double-click to open)
    ├── audit_trail.json       every agent loop step of the real runs
    └── github_url.txt         this repository's URL
```

## Setup (once)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then put your PORTKEY_API_KEY in .env
cd frontend && npm install && cd ..
```
The model is `MODEL_NAME=gpt-5.6-luna` via Portkey. All commands below run from the `hw5/` folder unless they say `cd`.

## Running it

### 1. Copy the original DB to the working copy (whenever you need a clean run)
```bash
cp data/campus_customs.db data/campus_customs_new.db
```
`data/campus_customs.db` is never written to. Everything (agents, MCP tools, the backend) uses `data/campus_customs_new.db`.

### 2. Start the MCP server
```bash
.venv/bin/python mcp_server/server.py
```
It runs over stdio and serves the 14 tools on the working DB. You can start it on its own like this to check it runs, or use it from Claude Code, where `.mcp.json` registers it as `campus-customs`. For agent runs you don't need to keep it open: the agent team launches its own copy of `mcp_server/server.py` over stdio for every run.

### 3. Start the FastAPI backend
```bash
cd backend
uvicorn main:app --reload --port 8000
```
With the `.venv` active. Open http://localhost:8000/docs to try every route; the route list is in [output/harness.md](output/harness.md#backend-routes-backendmainpy).

### 4. Start the React board (second terminal)
```bash
cd frontend
npm run dev
```
Open http://localhost:5173. Pick a ticket, press **Autobots, roll out ▸**, watch the team work, and approve or reject on the right. Then press **Continue the mission ▸** so the team can close the ticket out. The board calls the backend at `http://localhost:8000` (set `VITE_API_URL` to change it), and the backend's CORS allows the Vite origin.

### 5. Reset the DB before a full three-ticket run
Use step 1's `cp` command, the **⟲ Reset DB** button on the board, or `POST /api/reset`. `POST /api/desk/run` runs all three tickets as a fresh run, resetting the DB first. Run 101 and 102 before 103, so their bills are already queued when Megatron weighs the hoodie restock.

**Without the board:** `.venv/bin/python -m backend.agents` runs the whole desk from the terminal, or add ticket ids (e.g. `… backend.agents 102`). Set `ROLL_OUT_AUDIO=0` to mute Optimus's "Autobots, roll out!".

## MCP tools

| Tool | Who can use it | Tables (R = read, **W** = write) | What it does |
|---|---|---|---|
| `check_stock` | Optimus, Ratchet, Megatron, Bumblebee | R `inventory`, `pricing` | Units on hand for a SKU/size, shortfall vs. qty needed, unit cost, list price |
| `vendor_status` | Optimus, Ratchet, Megatron, Bumblebee | R `vendors`, `invoices`, `desk` | Lead days, open invoices with days overdue, `can_ship` |
| `lease_and_cash_status` | Optimus, Megatron, Ironhide | R `leases`, `cash_accounts`, `desk` | Rent, due date, days until due, whether cash covers it |
| `get_ticket` | everyone | R `tickets`, `approvals`, `drafts`, `desk` | One ticket plus approvals and drafts filed against it |
| `list_open_tickets` | Optimus | R `tickets` | Every ticket that isn't resolved |
| `list_approvals` | Optimus, Megatron | R `approvals`, `cash_accounts` | The approval queue, cash now, and cash if everything pending is approved |
| `update_ticket` | Optimus | **W** `tickets` | Sets the status and appends a dated note; won't mark a ticket resolved with an approval pending |
| `request_payment` | Optimus, Megatron | R `invoices`/`leases`, `cash_accounts`; **W** `approvals` | Queues an invoice or rent payment for a human. Amount comes from the DB; refuses if cash would go negative |
| `request_discount` | Optimus, Megatron, Bumblebee | R `pricing`; **W** `approvals` | Suggests a bulk price; refuses at or below unit cost. Anyone but Megatron → waits for his sign-off, then the human |
| `draft_purchase_order` | Optimus, Ratchet | R `vendors`, `pricing`, `inventory`, `invoices`; **W** `approvals` | Queues a restock PO (cost + ETA); flagged while the vendor has an open invoice |
| `draft_message` | Optimus, Bumblebee | **W** `drafts` | Saves a message as a draft on the board. **Never sent** |
| `hold_stock` | Optimus, Ratchet | **W** `stock_holds` | Reserves units for a ticket, pending dispatch. `check_stock` then shows them as held |
| `sign_off_discount` | **Megatron only** | **W** `approvals` | Signs off (or rejects) a discount someone else suggested, sending it on to the human |
| `decide_approval` | **humans only** (backend) | **W** `approvals`, `payments`, `cash_accounts`, `invoices`, `leases` | Approve or reject a queued item; refuses negative cash, and refuses a PO to a vendor with an open invoice |
| `delegate` *(agent tool, not MCP)* | everyone | none | Hand a task to a teammate and get their report back |

The full agent → tool → table map is in [output/harness.md](output/harness.md#agents-tools-and-tables).

## Guardrails
- **No made-up information.** Tools return `found: false` instead of guessing. Every agent's report is checked before it's accepted: approval/draft ids, dollar amounts and dates must trace back to a tool result in the run (or simple arithmetic on those). Unsourced items are sent back to the agent; if they're still unsourced after 3 retries, they reach the human stamped `UNVERIFIED`.
- **No emails, texts or calls.** No tool sends anything. Tools whose names look like outbound contact are blocked, and reports that claim something was "sent", "emailed" or "called" are rejected. Messages stay as drafts for a human.
- **Money needs a human.** Agents only queue approvals; only `decide_approval` (never given to an agent) moves cash.

Details are in [output/harness.md](output/harness.md#guardrails).

## Audit trail
Every step of every agent loop (model request, model response, tool call and result, delegation, report, guardrail hit, start/end) is appended to `output/audit_trail.json` as it happens, with run/agent ids, the delegation chain, the step number, latency, tokens and full details. The file stays valid JSON after every write, so an interrupted run still leaves its trail. The format is in [output/harness.md](output/harness.md#audit-trail-outputaudit_trailjson).

## Backend routes
| Method | URL | What it does |
|---|---|---|
| GET | `/api/health` | Server/DB check, shop today, whether a run is in progress |
| GET | `/api/tickets` | The 3 tickets, each `open` or `resolved` |
| GET | `/api/tickets/{id}` | One ticket with its approvals, drafts and stock holds |
| POST | `/api/tickets/{id}/run` | Run the agents on that ticket (background); `?fresh=true` resets the DB first |
| POST | `/api/desk/run` | Fresh run of every open ticket (resets the DB first) |
| GET | `/api/runs` · `/api/runs/{run_id}` | Run status and the Boss's final report |
| GET | `/api/runs/{run_id}/events` | Every agent event: what they said and what they did (`?after_seq=` to poll) |
| GET | `/api/approvals` | The approval queue and the cash picture |
| POST | `/api/approvals/{id}/approve` · `/reject` | A human decides (`{"approved_by": "Name"}`). Only approval moves money |
| GET | `/api/cash` | Checking balance from `cash_accounts` |
| POST | `/api/reset` | Reset the working DB to its original values |

Details are in [output/harness.md](output/harness.md#backend-routes-backendmainpy).

