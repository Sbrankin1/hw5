# Design · Campus Customs Autobot Operations Desk

The board in `frontend/` (React + Vite + TypeScript) is how a human watches the agent team work the three desk tickets, and how they approve the money. Start it with `npm run dev` (http://localhost:5173). It calls the FastAPI routes from Problem 7 on `http://localhost:8000`; the backend's CORS allows the Vite origin.

## The brief
- **Transformers × Yale.** The look should be unmistakably both: the Autobots running a Yale merch shop.
- **Very visual conversations.** It should be obvious *who is speaking to whom* at every moment, with the agents' ID cards moving and showing them speak.
- **A team synergy / happiness level** that changes live with what the team does.
- **A dramatic stalemate** when Megatron pushes back on Optimus: two forces of nature, locked.
- **The basics:** list the 3 tickets, start the team on one, show what every agent says and does, mark a ticket resolved with a green check, summarize each agent's work, let a human approve or reject payments and purchases, and show a live checking balance.

## Visual language

| Element | Choice | Why |
|---|---|---|
| Canvas | **A Yale-blue band across the top** (`#00356b` → `#286dc0`, with a faint Autobot-red glow at the top right) **that blends into a white page** by about 560px. The header, ticket title and stats sit on the blue; everything else sits on white | Yale blue is the brand without being overwhelming. The earlier all-dark-blue version was too heavy, and the light board is easier to read in class or on a projector. |
| Panels | **White cards** with soft navy shadows, and HUD corner brackets: Yale blue top-left, Autobot red bottom-right | The brackets keep the command-console feel on a light theme. |
| Faction colors | **Autobot red** `#d6202b` · **Decepticon violet** `#7a4fd6` · **Bumblebee gold** `#c99700` (bright `#f5c518` for highlights) · status green `#1f9d57`. These are darkened slightly from the dark theme so text stays readable on white | Each color has one meaning everywhere: red = Prime / Autobots, violet = Megatron, yellow = Bumblebee and "needs you", green = done. |
| Agent colors | Optimus red, Megatron violet, Bumblebee gold, Ratchet green `#3f9a35`, Ironhide orange `#c25a22` | Every beam, bubble border, log line and debrief card uses its speaker's color, so you can follow a conversation by color alone. |
| Type | **Orbitron** for machine labels (IDs, headings, numbers) · **EB Garamond** for the Yale wordmark and big titles · **Inter** for reading text | Orbitron reads as Cybertronian; Garamond is the Yale/collegiate voice; Inter keeps long agent messages readable. |
| Brand mark | A Yale shield with a mechanical chrome "Y" (`Insignia` in `src/agents.tsx`) | One mark that is both Yale and robot, drawn in SVG. |
| Portraits | **Character cut-outs** from wallpapers.com (transparent PNG, 512×512 head-and-shoulders crops in `public/agents/`): Optimus, Megatron, Bumblebee (background removed by an edge flood-fill), and a "medical bot" stand-in for Ratchet. Ironhide has no source image, so he keeps the original drawn SVG portrait (`Avatar`). The source license requires attribution, so credits are in the footer and in `public/agents/CREDITS.md`. | Real character faces make it unmistakably Transformers. The drawn portraits remain the fallback, so a missing image never breaks a card. |

Layout cues reused from earlier work: the **three-column dashboard** (navigation rail · main stage · status column) and **rounded cards with uppercase eyebrow labels** from the HW4 Campus Customs site; the **Yale-blue + serif headline** pairing from the HW4 and final-project themes; the **expected-vs-actual tab** idea from `desk_tickets.html`, which became the debrief.

## Layout

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ [Y-shield] Campus Customs at Yale / AUTOBOT OPERATIONS DESK   shop day · ● online · ⟲ Reset DB │
├───────────────┬──────────────────────────────────────────────────┬───────────────────┤
│ DESK TICKETS  │ COMMAND BRIDGE  #101 · Bulldog tee               │ CHECKING  $3,400  │
│ #101 ✔ / ◌    │        ┌─ Optimus ─┐                             │ pending · if-all  │
│ #102          │  Ratchet   ⬡ #101 ⬡   Megatron                   │ ledger of payments│
│ #103          │  Bumblebee            Ironhide                   │ TEAM SYNERGY gauge│
│ [reset first] │  beams + speech bubbles                          │ mood · sparkline  │
│ [ROLL OUT ▸]  │ COMMS LOG  Optimus ➜ Megatron …                  │ HUMAN APPROVALS   │
├───────────────┴──────────────────────────────────────────────────┴───────────────────┤
│ MISSION DEBRIEF · one card per agent · "not needed on this ticket" · Bumblebee's drafts │
└──────────────────────────────────────────────────────────────────────────────────────┘
```
Below 1280px the right column drops under the stage as a three-up row; below 900px everything stacks.

## The command bridge (who is talking to whom)
The stage is a light hologram table: a white-to-pale-blue panel with a faint Yale-blue grid, and the ticket hexagon in solid Yale blue (green when resolved). Only the full-screen moments, the **stalemate** and the **roll-out splash**, stay dark, so they land as dramatic interruptions.

- **The briefing table.** A hexagon in the middle shows the ticket on the table and its state ("Mission in progress", or a green **✔ Mission complete**).
- **ID cards around the table.** Each agent has a card: faction strip, ID code (YCC-001 …), portrait, name, role and a status LED. Optimus sits at the head, specialists around him.
- **Card states tell the story:**
  - *Standby*: dimmed and grayed. This also shows which specialists a ticket **doesn't** need.
  - *In the room*: full color with a blue LED.
  - *Speaking*: scales up with a glow ring in the agent's color and a blinking LED, and the portrait bobs as if talking.
  - *Listening*: a white pulsing outline.
  - *Working*: a `⚙ tool_name` chip pops on the card.
  - *Signed off*: green LED. *Alert*: red border and a shake.
- **Movement.** When an agent hands work to a teammate or reports back, **their card slides about a quarter of the way toward the listener**, then returns.
- **Energy beams.** An animated dashed beam in the speaker's color runs from speaker to listener, with a glowing pulse travelling along it. Reports use a finer dash than hand-offs, and alerts turn red. Faint spokes join every agent who's in the room to the table.
- **Speech bubbles.** A white bubble on the speaker carries what they said, labelled "to Megatron" or "reports to Optimus". Bumblebee's bubbles start with 📻.
- **Pacing.** Events arrive in bursts, so the board **plays them back** at a readable pace: hand-offs and reports hold for about 2 seconds, tool calls for under one. A backlog speeds it up, and **Skip to now ⏭** fast-forwards.

## Comms log
Under the stage, every line shows **speaker ➜ listener** in their colors, with a portrait, timestamp and message. Tool use is a compact line with the tool name. Refusals and guardrail hits are red. Megatron's pushback gets a violet-to-red line with the ⚡ objections, and joins and sign-offs are quiet system lines. It auto-scrolls and shows a blinking **LIVE** marker during a run.

## Team synergy
- **Gauge.** A half-moon gauge running red → yellow → green, with a needle, a percentage, a mood label and a sparkline of the run so far.
- **Moods:** Unstoppable, In sync, Steady, Grinding gears, Sparks flying, Stalemate.
- **Start.** Every run starts at **72%**, and each event nudges it:

| Event | Change |
|---|---|
| Hand-off to a teammate | +3 |
| Clean report back | +5 |
| A tool call that works | +1 |
| An agent finishes | +2 |
| Run finishes cleanly | +10, **+8 per disagreement Prime settled** |
| Tool refused | −4 |
| Hand-off blocked by the loop guard | −5 |
| Asked to fix an answer (retry) | −3 |
| Guardrail tripped | −8 (−12 if it stays unverified) |
| **Megatron's pushback** | **−22** (other pushback −8) |
| Agent error | −15 |
| Run fails | −25 |

So a stalemate visibly drags the team down. When Optimus settles it, the run ends higher than it started. Below 45% the panel pulses red.

## The stalemate (Megatron vs. Optimus)
This triggers when a report from Megatron carries `pushback`. The playback **pauses** and a full-screen showdown takes over:
- **The scene.** The screen splits: Autobot red on the left, Decepticon violet on the right. The two halves shove against each other in a loop, and white flashes burst from the center.
- **The title.** **STALEMATE** in huge chrome Orbitron with a glitch shake, under the kicker "Megatron pushes back" and the line *"The energon reserves can't fund both visions."*
- **The fighters.** Big portraits of Optimus and Megatron, each glowing in their faction color, lean into each other. A flickering lightning bolt sits between them, with one line each: *"We serve the people who come to us."* / *"The ledger does not bend, Prime."*
- **The tug-of-war.** A bar whose red/violet split and glowing knot swing back and forth: neither side is winning.
- **The numbers.** Megatron's actual objections from the run (e.g. *"$3,400 − $840 − $2,400 − $8 = $152 … twelve more hoodies cost $264"*) appear one by one.
- **The countdown.** "Optimus weighs the numbers… 9s". Click anywhere or **Let Prime rule** to continue.
- **Prime's ruling.** When Optimus finishes, a red-to-blue **Prime's ruling** banner rises from the bottom with his `disagreements_settled`.

## Approvals and cash
- **Human approvals.** This is the human's desk; nothing here is automatic.
  - Each queued item shows its kind (invoice / rent / purchase order / discount), ticket, amount, details and who prepared it.
  - Items waiting on a human glow yellow, and the whole panel pulses "Your call".
  - Discounts still waiting on Megatron show as dashed with "⏳ Waiting on Megatron's sign-off", with no buttons.
  - **Approve / Reject** need the approver's name, which is remembered and written to `payments.approved_by`. The buttons lock while a run is in progress.
  - When the last approval on a ticket is decided, a toast says the ticket is back with the team, and the button changes to **Continue the mission ▸**.
- **Checking.** A large chrome figure from `/api/cash` that **counts down** when a payment lands, with a red "−$840.00" delta chip.
  - Underneath: a bar of what's left if every pending approval goes through (red if that would go negative), the pending total, and a ledger of payments made (kind, ticket, approver, amount).
  - It refreshes every 2 seconds, so it moves the moment a human approves.

## Tickets and "resolved"
- **Rail cards.** Each ticket card shows its ID, type icon, subject, requester and status pill, plus small counters for open approvals ⏳, drafts 📻 and held stock 📦.
- **Resolved.** A resolved ticket turns green with a glowing **✔** that pops in. The table hexagon turns green with "✔ Mission complete", and the launch button reads "✔ Mission complete".
- **Launch area.** Shows the ticket's note, an optional **Reset the DB to its original values first** checkbox (a fresh run), and the gradient **AUTOBOTS, ROLL OUT ▸** button.
- **Roll-out splash.** Pressing the button flashes a 2.6-second **"AUTOBOTS, ROLL OUT!"** over speed streaks. The backend's spoken roll-out plays on the Mac at the same moment.

## Mission debrief (what each agent did)
Below the board, one card per agent who took part, built from the run's `agent_end` reports and tool calls:
- their summary, and Optimus's message to the team as a serif quote;
- Megatron's pushback, or the disagreements Prime settled;
- chips for every MCP tool they used, who they handed work to, the approvals they queued and the drafts they wrote.

A grayed **"Not needed on this ticket"** card shows the specialists who stayed on standby, so it's clear that not everyone is sent on every ticket. **Bumblebee's transmissions** shows his drafts in full on yellow radio cards, marked "drafts only, never sent".

## How it talks to the backend
| Board feature | Route |
|---|---|
| Ticket rail (every 2.5 s) | `GET /api/tickets`, `GET /api/tickets/{id}` |
| Roll out / continue | `POST /api/tickets/{id}/run?fresh=` |
| Bridge, comms log, synergy, stalemate, debrief | `GET /api/runs/{run_id}` + `GET /api/runs/{run_id}/events?after_seq=&detail=true` (polled every 1.2 s while running) |
| Approvals + cash (every 2 s) | `GET /api/approvals?status=all` (includes the cash picture) |
| Approve / reject | `POST /api/approvals/{id}/approve` · `/reject` |
| Checking balance | `GET /api/cash` (via the approvals call) |
| Reset DB | `POST /api/reset` |
| Online / run-in-progress indicator | `GET /api/health` |

The API base comes from `VITE_API_URL` (default `http://localhost:8000`). The last run for each ticket is remembered in `localStorage`, so a refresh replays it.

## Accessibility and polish
- Color is never the only signal: every state also has a text label (Speaking / Listening / Signed off, status pills, ✔/✕).
- `prefers-reduced-motion` turns the animations off.
- Buttons have visible focus rings in Bumblebee yellow.
- If the backend is down, a red banner explains how to start it.
