# AI Prompts Log — Homework 5

## Pre-work set up

### Prompt 1
> Okay I am going to be doing homework 5 now, so lets put us into that folder. Here is a layout of what will need to be delivered, so feel free to include that in the folder set ups right now. Same as homework 4, we should be aiming to get all of this included in the submission.
> Also, include this in AI_prompts.md as "Pre-work set up".
> Also if I make some basic spelling mistakes, or if you see that I have mentioned a file/folder that doesn't appear on here, tell me, put it in big bold red letters or something in your reply so that I can see it very clearly.
>
> *[Attached image: expected file layout]*
> ```
> hw5/
> ├── AI_prompts.md
> ├── requirements.txt
> ├── .env.example
> ├── .gitignore
> ├── .mcp.json
> ├── README.md
> ├── data/
> │   ├── campus_customs.db
> │   └── campus_customs_new.db
> ├── mcp_server/
> │   ├── server.py
> │   └── README.md
> ├── frontend/
> ├── backend/
> │   ├── main.py
> │   ├── models.py
> │   └── prompts/
> │       ├── boss.md
> │       ├── inventory.md
> │       ├── accounting.md
> │       ├── facilities.md
> │       └── customer_service.md
> └── output/
>     ├── harness.md
>     ├── mcp_smoke.json
>     ├── desk_tickets.html
>     ├── design.md
>     ├── resolved_tickets.json
>     ├── resolved_board.html
>     ├── audit_trail.json
>     └── github_url.txt
> ```
> README should explain: copy original DB to the working copy when you need a clean run, start MCP server, start FastAPI backend, start the React board, reset the DB before a full three-ticket run.

## Problem 1: Vibe coder prompts

### Prompt 1
> Now, like with homework 4, we are going to be working for campus customs, we are making a multi-agent operations, it is an agentic team that runs the shop. So much like a regular business, open tickets will land on a board, customer orders, rent, unpaid bills, discount requests, whatever the shop would have to do. We will build three pieces that talk to each other, and mcp server, a fastAPI backend with a multi-agent team, and a react dashboard so that a human can watch the agents at work and approve requests.
>
> The team should have full connectivity, any agent may delegate tasks to another agent for help.
> The assignment should have these agents
>
> Boss - reads the tickets, decides who should work on it and makes the final calls.
> Inventory - Checks stock by SKU and size, spots shortfalls, and figures out which vendor to restock.
> Accounting- watches cash and invoices, checks margins, and prepares payments or purchase orders for human approval. (Extra: Should project cash flow and value the company)
> Facilities - handles shop space side, leases, rents and such.
> Customer Service - draft messages for customers
>
> Rules of the shop:
> The field "desk.date_today" is "today" for the shop. use this to determine what is overdue
> Vendor lead times come from the vendors table
> A vendor will not ship new product while they have an open unpaid invoice
> Human approval is required for any payments. Points will be deducted if this is not done, if a payment is made, make sure to update the relevant table.
> If there is not enough cash, the pay tool must refuse, we cannot have negative cash balances.
> Cash only goes out, we do not model revenue (so maybe don't bother with the cash flow valuation)
> Before a full run to resolve the tickets, make sure to remind me to reset the database to original values.
> DO NOT email or call real vendors, drafts stay on the board.
>
> Problem 1: Vibe coder prompts:
> This should be where we put all of the prompts in AI_prompts.md
> make sure they all go in word for word for each prompt. And any follow up prompts I had to do, and why I had to have a follow up prompt (Include whatever was missing)

*Note: Prompt 1 above and the Pre-work set up prompt were sent as a single message; it is split here between the two sections, with no words changed.*

### Prompt 2
> okay perfect, I have included the folder data 4 in the homework 5 folder, can you see it now?

*Why this follow-up was needed: the Homework 5 database wasn't on the machine yet, so the agents had no `desk`, `vendors` or `invoices` tables to work from.*

### Prompt 3
> okay nice, I moved it to the my-app folder, can you access it okay so that it is not in the homework 5 folder

*Why this follow-up was needed: `data 4/` wasn't part of the expected hw5 layout, so it was moved out of the Homework 5 folder.*

## Problem 2: Study the campus customs database

### Prompt 1
> Problem 2: Study the campus customs database
> Open the campus_customs.db and look through each table and its field. Copy the original file to campus_customs_new.db and use that new copy as the working copy for future problems.
>
> Study 3 open tickets so you see how they link to other tables (also show me this in the tables so that I can visualize it) Start the harness.md for each table list the fields and one short line on why that table matters for the agents.

## Problem 3: Build the MCP server

### Prompt 1
> Problem 3: Build the MCP server:
> write an mcp server in mcp_server/ using FastMCP. it will talk to the campus_customs_new.db
> Every agent in this homework uses the tools in this MCP server, I will be adding more tools to it later, for now, write three tools you know will need for the tickets in the database.
> Keep the names clear, never invent any data, only use information in the database.
>
> In harness.md list each of the three MCP tools for every tool include:
> which table it reads
> Which ticket it helps unlock, 101, 102, 103,
> One sentence on why that tool is right for that ticket
>
> Vague lines like "reads inventory" score low, tie the tool directly to the ticket.
>
> Also add a short mcp_server/README.md file that explains what the MCP server is for, which database file it uses, and the 3 tools it has.

## Problem 4: Add the MCP server to vibe coder and test each tool

### Prompt 1
> Problem 4: Add the MCP server to vibe coder and test each tool
>
> In the vibe coder, add the MCP server to the project so that vibe coder can call the tools. Save the connection JSON text in .mcp.json at the eproject root.

### Prompt 2
> Now that the vibe coder is connected, test each of the 3 MCP tools, save the evidence in mcp_smoke.json
>
> For every tool include:
> The prompt the vibe coder asked
> the tool name
> The tool output (must match values in campus_customs_new.db)

*Why this follow-up was needed: Prompt 1 only registered the server. The tools still had to be called and the evidence saved. Note: the campus-customs tools had not loaded into this vibe-coder session, so the evidence came from an MCP stdio client launched from `.mcp.json`.*

### Prompt 3
> You are the vibe coder, should have mentioned that earlier

*Why this follow-up was needed: it clarified that the vibe coder means Claude Code itself, so the smoke test has to come from Claude Code's own MCP tool calls. That needs the campus-customs server loaded into a fresh session.*

### Prompt 4
> What do you mean by the campus-customs tools aren't there?

*Why this follow-up was needed: it was a clarifying question about why the vibe coder couldn't call the MCP tools directly in the current session.*

### Prompt 5
> lets work in homework 5, and I want you to use the mcp server tools to call data from the campus_customs_new.db

*Why this follow-up was needed: in a new session the campus-customs server loaded, so Claude Code could call `check_stock`, `vendor_status`, and `lease_and_cash_status` itself. It re-ran all 7 smoke calls (4 ticket calls, 3 negative tests). The outputs were the same as before, and `mcp_smoke.json` now names Claude Code as the client.*

## Problem 5: Build the agent team and grow the MCP tools

### Prompt 1
> Problem 5: build the agent team and grow the MCP tools
>
> Now we will build the team for campus customs using PydanticAI:
> -Boss
> -inventory
> -accounting
> -facilities
> -customer service
>
> Include prompts, models, and agent loops so they can delegate work to each other with full connectivitiy.
>
> Put the agent prompts in backend/prompts/
> it should be one file per agent
> put data types in backend/models.py, and the agent files under backend/
> Have the agents pulled from my claude API.

### Prompt 2
> Okay our people will be based on transformers.
> So OBVIOUSLY the boss is optimus prime.
> I want it to talk like optimus prime, I would also love it if when it started, he would audibly say "autobots roll-out" because it is so iconic.
> I think optimus is a great leader, fair, and knows when he has to be kind, he also leads from the front, so he can get involved when required.
>
> I think that customer service should be Bumblebee, he feels like he would be great to talk to people. His thing is obviously that his speech is only able to be done using famous quotes because of his limits to the voice box, so any communications should reflect that, a series of famous quotes that sort of make sense in the context.
>
> Accounting/facilities/inventory, you can take your pick from the rest of the autobots. I would be happy to have accounting be megatron, because he will be the one sort of fighting optimus prime on the fact they are going to run out of money so in the context of the world, it makes the most sense.

*Why this follow-up was needed: Prompt 1 built a team that worked but had no personality. This prompt gave each agent a Transformers persona: Optimus Prime (boss, leads from the front, so he now has the specialists' request tools too), Megatron (accounting, argues with Prime about cash in a new `pushback` field), Ratchet (inventory), Ironhide (facilities), and Bumblebee (customer service, who talks only in quotes). It also adds a spoken "Autobots, roll out!" at the start of every run.*

### Prompt 3
> where will I find my API key for claude?

*Why this follow-up was needed: the agents need the user's own Anthropic API key in `.env` before they can run on Claude, and the user didn't know where to get one.*

### Prompt 4
> so is that key different from the claude code $20 daily limit I get from Yale?

*Why this follow-up was needed: the user wanted to know whether the API key for the agents is the same thing as their Yale-provided Claude Code allowance, or separate.*

### Prompt 5
> Okay, can you revert back to the portkey that we have used previously that has my open AI key in it?

*Why this follow-up was needed: an Anthropic API key would be billed separately from the Yale Claude Code allowance, so the user went back to the Portkey-served OpenAI model from HW4 (`gpt-5.6-luna`). The Portkey settings were copied from `Homework 4/.env` into `Homework 5/.env`.*

### Prompt 6
> okay so I want the AI agents to write to audit_trail.json as they run, for each agent loop step, include enough information to audit later

*Why this follow-up was needed: up to here the run's trace only lived in memory and was printed at the end. Nothing was saved, and a crash lost everything. Now every loop step (model request and response, tool call and result, delegation, report, start and end) is appended to `output/audit_trail.json` as it happens. Each event carries run and agent ids, the delegation chain, the step number, latency, tokens and full details.*

### Prompt 7
> in output harness.md  list each agent and the tools they have along with which table the tool uses, also add a guardrail that doesn't allow them to make up information or send any emails or make calls.
>
> Then update the README file so that it includes all the relevant tools list included

*Why this follow-up was needed: `harness.md` still described only the original 3 read-only tools, and the README was a placeholder. This prompt asked for the agent → tool → table map and for guardrails. The guardrails are enforced in code, not just written down: a grounding check on every report, a block on outbound-contact tools, and rejection of claims that something was "sent", "emailed" or "called". The README now lists every tool.*

## Problem 6: Plan the three tickets

### Prompt 1
> Before wiring the backend, we are going to build out the expectations on each active ticket. this will go into output/desk_tickets.html (I should be able to double click this and see tabs for each of the tickets, 101, 102, 103) also add empty cash and reflections tabs for later. for each tab fill an expected section, and leave room for an "actual" section, cash and reflections should just be blank.
>
> could you also provide me with a rundown of each ticket in the tab so I can see what each entails?

*Why this follow-up was needed: before the backend is wired up and the agents run for real, the user wanted a written baseline of what "correct" looks like for each ticket, so the actual run can be checked against it. `desk_tickets.html` is a self-contained page that opens with a double-click. It has a tab per ticket (rundown, expected steps, end state, pass/red-flag checks, and an empty Actual table), plus blank Cash and Reflections tabs.*

### Prompt 2
> okay for ticket 101, the boss is going to speak to the accountant, who will be in charge of paying the overdue balance. From there, we confirm it paid and then move on to restocking the t shirt in size small and logging it.
> Then we have to communicate to Tauhid that the shirt can be with him by a specific time, that time should be based on how long it would take from todays date to arrive, it should not be promised to be delivered today!
>
> For 102, the boss will read the email and can then go to the accountant who will be the one saying when it is due and to have it queued, it should NOT be paid yet, but the landlord should be notified that it WILL be paid on time. It should not say that it has already been paid.
>
> for 103 - the first point of call is to check the stock, from there, the stock checker will report the shortfall to optimus and megatron, they will then discuss how best to move forward, megatron has to push back against optimus due to the fact that they do not have the funds to execute the order. They should offer the remaining 8 at a discount of 10%, and should then say that the remaining 12 can be ordered on backorder and the 10% is a thank you for their patience in the matter. Then it should be shown as awaiting sign off from Megatron. Customer service should be the one who suggests the discount. Inventory should be pending the 8 to be sent while they wait on the response

### Prompt 3
> we should also not have to send every specialist on every ticket, some do not require that!
> Sorry, keep the existing roles
> Also add which MCP tools you expect the runs to use

*Why these follow-ups were needed: Prompt 1's expectations were my best guess at the flows. Here the user set the exact flow for each ticket:*
- *101: Megatron pays #501 first, payment is confirmed, then the tee is restocked and logged, and Tauhid gets a specific date (today + 5 lead days = 2026-09-05).*
- *102: Optimus hands it to Megatron, who confirms the due date and queues the rent without paying it, and the landlord is told it will be paid on time.*
- *103: stock is checked first, Megatron pushes back on funds, Bumblebee suggests 10% off the 8 on hand as a thank-you for patience, 12 go on backorder, the discount awaits Megatron's sign-off, and Ratchet holds the 8.*

*Prompt 3 added three things: only the specialists a ticket needs are used (Ironhide on none of the three, Ratchet not on 102); the five roles stay as they are; and each tab gets a table of the MCP tool calls the run should make.*

*Follow-up decisions (answered in a question prompt): Megatron's sign-off on a discount comes first, then the human approves ("Megatron, then human"); and the agent prompts and tool access should be updated now to follow these flows. Added the MCP tools `sign_off_discount` (Megatron only) and `hold_stock`. Bumblebee can now suggest discounts, and every prompt got a playbook for its part.*

## Problem 7: Backend Routes

### Prompt 1
> Problem 7: Backend Routes:
> we need to put together the backend before we make the frontend. should be in backend/main.py
> it should use FastAPI and routes to do the following:
> return the 3 tickets and establish if they are open or resolved
> take a ticket ID and run the agents on that ticket
> return each agent event - what they said and what they did
> approve a payment or purchase AFTER a human hits approve. agents only prepare the pay
> Return the current checking balance from cash_accounts
> reset the database to its original values when you run a fresh run.

### Prompt 2
> from the backend, start the server with:
> uvicorn main:app --reload --port 8000
> in the output/harness.md list each route in one line, what URL and what it does

*Why this follow-up was needed: Prompt 1 defined what the routes do. This one fixed how the server starts (from inside `backend/`, so `main.py` has to make the project imports work from there) and asked for a one-line-per-route list in `harness.md`.*

## Problem 8: Agent dashboard

### Prompt 1
> Problem 8:agent dashboard
>
> Now we will build the frontend dashboard in frontend/ with react + Vite + typescript
> the page should call the routes from problem 7. At minimum the baord should:
> list all 3 tickets
> let me pick one ticket and start the team of agents on it
> show all agents and what they are saying/doing during the runs
> mark the ticket as resolved when it is done - with a green check mark or something
> there should be a short summary of what each agent did on the ticket
> let a human approve or reject a payment or purchase when prompted
> show a live checking balance that updates with purchases and payments
>
> In terms of looks, should be obliviously transformers X Yale themed. However we do that is up to you, think back also to previous examples of nice layouts we have used and make it very visually appealing. The conversations between agents should be very visual, highlighting who is speaking to who at each time. Perhaps with their image/ID card being the thing that moves and shows them speak. I would also love for there to be an overall synergy/happiness level going on with the teammates. Should change live depending on the tasks. When megatron has to push back against optimus, it should be very dramatic and show a real stalemate between the two forces of nature.
>
> The frontend should also talk to the backend at the host 8000. allow the vite page origin so that it can call the routes.
> start the board with:
> npm run dev
>
> write the layout/design aspect in output/design.md  with the different design aspects we discuss.

### Prompt 2
> Everything from this:
> Before wiring the backend, we are going to build out the expectations on each active ticket. [...]
> until I mention problem 7 should be in "Problem 6: plan the three tickets"

*Why this follow-up was needed: the ticket-planning prompts had been logged under Problem 5. They belong to their own problem, so they were moved under a new "Problem 6: Plan the three tickets" heading and renumbered.*

### Prompt 3
> https://wallpapers.com/transformers
>
> Feel free to pull images and inspiration and such from here, but remove the backgrounds so it is just the characters themselves

*Why this follow-up was needed: the user wanted real character art on the cards. Nothing was downloaded, because downloading files needs the user's explicit OK and the wallpapers are copyrighted artwork. Instead, every card uses `frontend/public/agents/<role>.png` when that cut-out exists, and an original drawn SVG portrait otherwise.*

### Prompt 4
> what were the issues?

*Why this follow-up was needed: the user interrupted a long live test to ask what had gone wrong. The bugs found by testing against the live backend were: the synergy number hidden behind the needle; Megatron's card stuck on "In the room"; the balance stuck at $0.00 in a hidden tab; the page crashing on guardrail events, where a check name was treated as an agent; repeated requests for missing images; and slow Portkey model calls.*

### Prompt 5
> yes do it

*Why this follow-up was needed: the user approved finishing the live test of all three tickets on the board, including the Megatron vs. Optimus stalemate.*

### Prompt 6
> I started those

*Why this follow-up was needed: two runs (102 and 103) were in the run list that the vibe coder hadn't started. The user had started them from the board. Checking those runs confirmed 103 produced Megatron's real −$112 pushback, so the stalemate screen could be tested on a real run.*

### Prompt 7
> the images have not yet changed to reflect the new images you got from the wallpaper site

*Why this follow-up was needed: nothing had been downloaded yet, because downloads need explicit approval. The user chose to have the vibe coder find the images, and approved each file:*
- *Optimus head, Megatron head, Bumblebee close-up and full body, and a "medical bot" stand-in for Ratchet, all from wallpapers.com.*
- *Ironhide has no image on the site, so he keeps the drawn portrait.*
- *Four of the files already had transparent backgrounds. Bumblebee's close-up had its black background removed locally with an edge flood-fill, so the 170 MB rembg tool wasn't needed.*
- *Every image was cropped to a 512×512 head-and-shoulders square and saved to `frontend/public/agents/`.*
- *The source license requires attribution, so credits were added to the footer and to `public/agents/CREDITS.md`.*

## Problem 9: Resolve the tickets

### Prompt 1
> Problem 9: Resolve the tickets
> now that we have run each of them, I want you to record the results in output/desk_tickets.html
> On each tab, fill in the actual result, which is what happened and what was said to each other. Which tools they used. Which agents worked on the problem. Which ones were delegated.

### Prompt 2
> Then on the cash tab of the desk_tickets.html itemize the money
> Starting balance after the reset
> For each ticket, how cash changed when the ticket was resolved, and why the cash changed the way it did.
> Ending checking balance - which should match the cash_accounts in the database
>
> Wrong math loses points, so make sure everything is correct.
>
> Also for each ticket ID save into resolved tickets json, the ticket ID, the outcome, the final status, what each agent contributed, and any human approvals needed.
>
> resolved board html page should include a screenshot of each resolved ticket on the dashboard.
>
> Then append real runs to the audit trail json  and finish the harness.md so it covers the tables, tools, five agents, MCP, API routes, the dashboard, and the safety rules

*Why this follow-up was needed: Prompt 1 only covered the ticket tabs. This prompt added the rest of the Problem 9 deliverables:*
- *the Cash tab, with every figure computed from `payments` and checked against `cash_accounts` in code;*
- *`resolved_tickets.json`;*
- *`resolved_board.html`, with 8 dashboard screenshots embedded;*
- *the real runs appended to `audit_trail.json`;*
- *a finished `harness.md`.*

*The recorded runs came from the live session on a working copy, so that session's final DB state was copied into `data/campus_customs_new.db`, with a backup made first, so every file matches the database.*

### Prompt 3
> Could you actually change the visual, it is too blue, I think I would prefer it if it was maybe a little lighter with the overall theme, maybe a yale blue top that blends into white with a gradient instead! please do that and take new screenshots

*Why this follow-up was needed: the dark navy dashboard looked too blue. The board was rethemed:*
- *A Yale-blue band at the top fades into a white page, with white cards and a light command bridge.*
- *Agent colors were darkened slightly so text stays readable on white.*
- *The stalemate screen and roll-out splash stay dark, for drama.*

*While retaking the screenshots, a bug turned up: the comms log scrolled the whole page whenever a new line arrived. It was fixed so only the log box scrolls. `resolved_board.html` was rebuilt with the new screenshots and restyled to match, and `design.md` was updated.*

## Problem 10: Reflections

### Prompt 1
> so in the desk tickets html in the reflections tab I want you to put this into it:
> So I think they did a good job of performing their individual functions. I do think that we likely had some superfluous agents at times, but that is okay.
> So the expected result matches somewhat, obviously I could not have predicted the actual text that they would say to each other which exists in the actual. However, I was hoping maybe for the characters to represent themselves better. Be more like the characters, so I may go back and add that.
> I'm not sure if it would have been "simpler" to have one agent with tools, because things can run simultaneously, however, I do think that we had excess agents for sure. I had to change the set up at one point because how I described the task meant that one agent wouldn't be used at all!
> They could likely predict which stock to order more of and evaluate trends in purchases.
> They would be able to send the emails likely and handle simple customer service questions and answers.
> I think they would be able to automate a lot of payments too, but that runs the risk of accidentally buying all of the potatoes in the market (see Ray Dahlio's experience with automated trading to get the reference)
>
> I think they wouldn't be able to handle the human side of things, like being personable, or lateral thinking to solve a problem.
> I also think they would struggle in the event that they had to do market research on competitors. They would need the ability to parse the internet and other APIs to do that.
> They would also be unable to transfer funds currently. If we had a tool that would allow them to move funds around from other accounts or pay for things on credit to ensure that we get all of our sweaters in time when a big order comes in, that would be great!

### Prompt 2
> So like I mentioned in my notes, I want you to make sure the characters themselves really come across in their interactions, I want optimus to feel like he really embodies the character, the same with megatron! For example, megatron would HATE having to wait for human approval, that should be reflected in the voice of his character in the interactions!
>
> Also fix the Dalio spelling thank you!

*Why this follow-up was needed: the reflection said the characters didn't come through strongly enough. In the recorded runs, reports were mostly plain fields and Optimus's hand-offs read like dry instructions. The changes:*
- *Every specialist report now has an `in_character` line spoken in the character's voice, and that's what the board shows as speech. `summary` and `facts` stay plain.*
- *Every `delegate` task now opens with one line in the speaker's own voice.*
- *Optimus and Megatron's persona sections were rewritten, and Ratchet and Ironhide got stronger voices too. Megatron now openly despises waiting for human approval, but always waits.*

*A live test on a scratch DB (tickets 102 and 103) showed it working. Megatron: "Nothing has been paid; now I must wait, like a drone, for a human to scrawl their name. Unbearable." Optimus: "Ratchet, old friend." / "Hold the line. Till all are one." Because Megatron reused the example line word for word, the prompts now tell the agents to invent fresh lines.*

*"Dahlio" was corrected to "Dalio" in the Reflections tab. (The user's prompt above is quoted as written.)*

## Problem 11: Submit to GitHub

### Prompt 1
> Problem 11: Submit to Github
> push the code to a public github repository so that it can be graded and evaluated. do not push the real .env but DO include both database files under data/
> and again, we should be following this layout!
>
> Also, before we submit, make sure you go through the feedback from hw1 and hw2 so that we know we have covered all the bases!
>
> *[Attached: the expected hw5/ file layout, and the README requirements: copy the original DB to the working copy for a clean run, start the MCP server, start the FastAPI backend, start the React board, reset the DB before a full three-ticket run]*

### Prompt 2
> I also got 100% on hw 3  which used this layout, maybe go back and just think about how you ensured that you hit all the points for that in the other homework, naturally they are totally different projects and you should be using the earlier layout and such, but yeah, make sure it is good!
>
> *[Attached: the hw3/ expected layout, for reference]*

*Why this follow-up was needed: it pointed back to what earned full marks on HW3, which was matching the given layout exactly, so the submission was checked the same way. The HW1/HW2 feedback checklist (recovered from the HW4 submission session) was checked item by item:*
1. *`AI_prompts.md` is spelled exactly.*
2. *Every problem has a `## Problem N` heading.*
3. *`.env.example` holds variable names only.*
4. *The layout matches the spec exactly.*
5. *Every doc path exists.*
6. *The prompt files load and real model calls happen.*
7. *The HTML outputs open with a double-click.*
8. *The documented run commands were actually run.*
9. *There are no notes to the AI grader.*
10. *Every import is in `requirements.txt` (checked with a fresh venv), the frontend builds with 0 errors, and the docs use American spelling.*

*`data/campus_customs_new.db` was removed from `.gitignore` so both databases are pushed. The README was restructured around the five required steps.*

### Prompt 3
> okay launch it so I can do the approvals and such, and also fix the typos

*Why this follow-up was needed: the recorded runs came from before the character-voice upgrade, and their approvals were clicked by the vibe coder in testing ("Scott (test)"). So the user chose to re-run all three tickets with the new voices and approve as themselves. The previous recorded state was backed up, the DB was reset to the original, and the dashboard was launched. The typos flagged in this problem's prompts ("ush" → "push", "chracter" → "character", "al" → "all") were corrected in this log.*

### Prompt 4
> okay done!

*Why this follow-up was needed: the user finished the new desk run on the dashboard (7 runs, 23:48–23:57 UTC, every approval by Scott). Everything was then re-recorded from that session:*
- *the Actual sections of `desk_tickets.html`, now with each agent's in-character lines next to the plain record;*
- *the Cash tab: $3,400.00 → $152.00, checked against `cash_accounts`;*
- *`resolved_tickets.json`;*
- *`resolved_board.html`, with 9 new screenshots, including the stalemate and Prime's ruling;*
- *the results section of `harness.md`.*

*Deviations from the plan were recorded honestly:*
- *Megatron set a $54.00 discount for 20 units himself, instead of Bumblebee's 10% on 8.*
- *Optimus held the hoodies himself.*
- *Bumblebee's landlord note said "The check is in the mail".*
- *Bumblebee used a song lyric in a report.*

*While capturing the stalemate, a bug turned up: in the light theme its text had become dark on dark. It was fixed by giving the full-screen moments their own white text.*
