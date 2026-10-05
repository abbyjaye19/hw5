# AI Prompts Log — HW 5: Campus Customs Multi-Agent Operations

A log of the prompts I typed into my vibe coder (Claude Code) for each problem, written in my own words (lightly edited for spelling and grammar).

---

## Project Setup (before Problem 1)

**Prompt 1:**

> I'm going to work on HW 5 for AI now. Please do everything in that folder from here on.

**Prompt 2:**

> Setup: Campus Customs Multi-Agent Operations is the agentic team that runs the shop. Open tickets land on a board: customer orders, rent, unpaid bills, discount requests, whatever the shop has to handle. I'm going to build three pieces that talk to each other: an MCP server, a FastAPI backend with a multi-agent team, and a React dashboard so a human can watch the agents work and approve requests.
>
> The agent team has full connectivity: any agent may delegate tasks to any other agent for help. Please build these agents:
>
> - **Boss:** reads each ticket, decides who should work on it, and makes the final calls
> - **Inventory:** checks stock by SKU and size, spots shortfalls, and figures out which vendor can restock
> - **Accounting:** watches cash and invoices, checks margins, and prepares payments or purchase orders for human approval
> - **Facilities:** handles the shop-space side (leases, rent, etc.)
> - **Customer Service:** drafts messages for customers
>
> Please unzip the data pack I put in the HW 5 folder so I have `data/campus_customs.db`. This is the original shop database. Its tables include desk, tickets, inventory, pricing, vendors, leases, cash_accounts, payments, and invoices.
>
> The tools will update the database as tickets get resolved. Make a copy of the database called `data/campus_customs_new.db` and point the MCP server and backend at that working copy. Keep `campus_customs.db` untouched so I can reset before we start resolving tickets.
>
> Rules:
>
> - The field `desk.date_today` is "today" for the shop. Use this date to decide what is overdue.
> - Vendor lead times come from the vendors table.
> - A vendor will not ship new product while it still has an open, unpaid invoice.
> - Human approval is required for every payment (points are deducted otherwise). When a payment is made, update the relevant tables.
> - If there isn't enough cash, the pay tool must refuse. No negative balances.
> - Cash only goes out in this HW. Revenue isn't modeled, so no money comes in.
> - Before a full run to resolve the tickets, reset the database to its original values.
> - Don't email customers or call real vendors. Drafts stay on the board.
>
> Use my PORTKEY_API_KEY for AI calls. For this assignment, every agent must use only gpt-6-luna through Portkey. Multi-agent chats burn tokens fast, and points are deducted if any other model shows up in the code or the runs.
>
> I'll work one problem at a time with you and type each problem in my own words (no pasting the page URL or screenshotting the problems). The final submission is a public GitHub repo; the last problem shows the file tree.

**Follow-up prompt:**

> Use my PORTKEY_API_KEY for AI calls. This assignment requires ONLY gpt-6-luna through Portkey for every agent. If that wasn't how it was set up, fix it and update everything.

*What was lacking after the first prompt:* the agents had been set up for a different model than the one the assignment requires, so the model, guardrail, requirements and docs all had to be switched to gpt-6-luna.

---

## Problem 1: AI Prompts Log

**Prompt 1:**

> I'm now on Problem 1. Create `AI_prompts.md` at the start of the assignment and keep it updated as we work. It's the log of what I type to my vibe coder, with one section per problem. Each section must include:
>
> - The problem number and title
> - At least one prompt I typed, in my own words as much as possible
> - One follow-up prompt if I needed it (plus one sentence on what was lacking after the first)

**Follow-up prompt:** None needed.

---

## Problem 2: Understand the Database / Start the Harness

**Prompt 1:**

> I'm now on Problem 2. Please open `data/campus_customs.db` and look through every table and its fields. Copy the original file to `data/campus_customs_new.db`; later problems will update that working copy.
>
> Please study the three open tickets so I can see how they link to the other tables.
>
> Start `output/harness.md`. For each table, list its fields and add one short line on why that table matters to the agents. I'll keep growing this harness file in later problems.

**Follow-up prompt:** None needed.

---

## Problem 3: MCP Server with Three Tools

**Prompt 1:**

> I'm now on Problem 3. Please write an MCP server in `mcp_server/` using FastMCP. It will talk to `data/campus_customs_new.db`. Don't connect it or run it in this problem.
>
> Every agent in this HW uses the tools in this MCP server. I'll add more tools later, but for now write the three tools you know we'll need for the tickets in the database. Keep the names clear. Never invent data; only use what's in the database.
>
> In `output/harness.md`, list the three MCP tools. For each one, include which table it reads, which ticket it helps unlock (101, 102, or 103), and one sentence on why it's the right tool for that ticket. Vague lines like "reads inventory" score low, so tie each tool to its ticket.
>
> Also add a short `mcp_server/README.md` that explains what the MCP server is for, which database file it uses, and its three tools.

**Follow-up prompt:** None needed.

---

## Problem 4: Connect the MCP Server to the Vibe Coder / Smoke Test

**Prompt 1:**

> I'm now on Problem 4. Add the MCP server to this project in my vibe coder so it can call the tools. Save the connection JSON in `.mcp.json` at the project root (or wherever the vibe coder keeps its local MCP server list). With the vibe coder connected, test each of the three MCP tools and save the evidence in `output/mcp_smoke.json`. For each tool, include:
>
> - The prompt I asked the vibe coder
> - The tool name
> - The tool output (it must match the values in `data/campus_customs_new.db`)

**Prompt 2:**

> Finish Problem 4. Using the campus-customs MCP server (not Python), call these three tools one at a time: `check_stock` for CC-HOOD-NAVY size M with qty_needed 20; `get_invoice_status` for invoice 501; and `get_lease_rent_due` for lease 1. Save `output/mcp_smoke.json` with one entry per tool containing the prompt I asked, the tool name, and the exact tool output. Then confirm each output matches `data/campus_customs_new.db`, and update `AI_prompts.md` under Problem 4.

**Follow-up prompt:**

> I'm in HW5. Please just do it.

*What was lacking:* The session had started outside the HW5 folder, so the campus-customs MCP server from `.mcp.json` wasn't loaded. That attempt reached the server through a hand-written script over its stdio transport rather than through Claude Code's MCP connection.

**Follow-up prompt 2:**

> Redo the Problem 4 smoke test using the campus-customs MCP tools connected to this session. Don't use Python, Bash or scripts to talk to the server; if those tools aren't available, stop and tell me. Call `check_stock` for CC-HOOD-NAVY size M with qty_needed 20, `get_invoice_status` for invoice 501, and `get_lease_rent_due` for lease 1. Overwrite `output/mcp_smoke.json` with one entry per tool containing the prompt I asked, the tool name, and the exact tool output, and note that the calls went through the `.mcp.json` connection. Confirm each output matches `data/campus_customs_new.db`. Don't reset the database and don't push anything.

*What was lacking:* The earlier evidence didn't clearly show that the session's connected MCP tools had been called, and it no longer matched the working database (invoice 501 and lease 1 rent were paid on 2026-08-31 after it was saved). The redo used the `mcp__campus-customs__*` tools directly.

---

## Problem 5: Build the Multi-Agent Team (PydanticAI)

**Prompt 1:**

> I'm now on Problem 5. Please build the Campus Customs agent team in PydanticAI: Boss, Inventory, Accounting, Facilities, and Customer Service. Include prompts, models, and agent loops so they can delegate work to each other with full connectivity.
>
> Put the agent prompts in `backend/prompts/`, one file per agent. Put the data types in `backend/models.py` and the agent files under `backend/` (the layout can vary as long as the five roles are clear). Use my PORTKEY_API_KEY and only gpt-6-luna for every agent.
>
> I'm describing each agent's shop role in my own words. Detailed prompts that cover every part of an agent's work and scope score higher than short, generic ones. Here's what I'm thinking, but tell me your thoughts too:
>
> - **Boss:** the person in charge, who makes the decisions and the final output. It shouldn't overthink things or waste tokens.
> - **Inventory:** never makes up numbers.
> - **Accounting:** keeps control of all the finances and doesn't make mistakes. The finances matter.
> - **Facilities:** the company's real-estate person.
> - **Customer Service:** answers questions and has an FAQ section.
>
> Add whatever tools the agents need to the MCP server so they can work the open tickets. Shop facts must come from the MCP server over `data/campus_customs_new.db`. Don't build a second shop-tools layer that bypasses MCP.
>
> Wire the agents so they append to `output/audit_trail.json` as they run, recording enough about each agent-loop step to audit later. Append to the file; don't wipe it each run.
>
> In `output/harness.md`, list each agent and each MCP tool (including any added in this problem) with the table each tool uses. Also add a short safety section: the guardrails a real business would want when agents touch real customers and real money, plus the limits that keep token use in check.
>
> Update `mcp_server/README.md` so its tool list matches what we have now.

**Follow-up prompt:** None needed.

---

## Problem 6: Expected Plan Before Wiring (desk_tickets.html)

**Prompt 1:**

> I'm now on Problem 6. Before we wire up the backend, write down what I expect the team to do on each open ticket. Build `output/desk_tickets.html`, a page I can double-click to open, with one tab per ticket (101, 102, 103). Also add empty Cash and Reflection tabs for later problems (blank, or a short "coming later" note for now).
>
> On each ticket tab, fill in only the Expected section, and leave room for an Actual section to fill in after the agents run.
>
> For each ticket's Expected section, cover:
>
> - Who the Boss should call first, and why
> - Every agent delegation I expect (not just "the Boss calls everyone")
> - Which MCP tools I expect the run to use
>
> Plans that send every specialist on every ticket score low. I'll compare this plan with what actually happens when the agents resolve the three tickets.

**Follow-up prompt:**

> Here's the part that should be in my own words: have Inventory go first, then Facilities. That way we know whether the order can be filled today, and how many units we have before offering any discount, before we look at the facilities side. Don't call every agent at once. Use whichever MCP tools make the most sense. I trust you on this.

*What was lacking after the first prompt:* the vibe coder drafted the Expected plan, so it didn't yet include my own reasoning about the order the agents should be called in (Inventory first, then Facilities, one at a time).

---

## Problem 7: FastAPI Backend Routes

**Prompt 1:**

> I'm now on Problem 7. The React dashboard (Problem 8) needs a backend to call. In `backend/main.py`, use FastAPI to add routes that:
>
> - Return the three tickets and whether each is open or resolved
> - Take a ticket id and run the agent team on that ticket
> - Return recent agent events (what each agent said and which tools it used) so the board can refresh
> - Approve a payment or purchase after a human clicks Approve (agents only prepare payments; this route is what actually changes cash)
> - Return the current checking balance from cash_accounts
> - Reset the database to its original values when I want a fresh run
>
> From the `backend/` folder, I start the server with `uvicorn main:app --reload --port 8000`, which runs the backend at http://localhost:8000 so the dashboard can call those routes.
>
> In `output/harness.md`, list each route on one line (its URL and what it does).

**Follow-up prompt:** None needed.

---

## Problem 8: React Dashboard

**Prompt 1:**

> I'm now on Problem 8. Please build the dashboard in `frontend/` with React, Vite, and TypeScript. It should call the routes from Problem 7. At a minimum (going a little further is welcome), the board should:
>
> - List all three tickets
> - Let me pick a ticket and start the agent team on it
> - Show each agent and what it's saying or doing while the ticket runs
> - Mark a ticket resolved when the run finishes
> - Show a short summary of what each agent did on that ticket
> - Let a human approve a payment or purchase when asked
> - Show the checking balance (it should drop after an approved payment)
>
> Make the dashboard look good. Be creative with the layout and feel; this is a real desk people should want to sit at. I want it navy, white, gold, and silver (not the black-and-pink style), and formal and professional.
>
> The frontend should talk to the backend at http://localhost:8000. On the backend, allow the Vite page's origin (usually http://localhost:5173) so the browser can call those routes. I start the board with `npm run dev`, which opens it in the browser so I can pick tickets and watch the agents.
>
> Write `output/design.md` explaining the look I chose (the layout, how the agents read differently, and how resolved tickets and cash flow show up) and why, including the creative choices that make it feel special.

**Follow-up prompt:**

> Why does the site show a different model than the one I want? Also, I tried running the first ticket and got an error. Please fix it, and tell me where to find the Expected vs. Actual page.

*What was lacking after the first prompt:* the board worked, but running ticket 101 failed because the agents were set to the wrong model for my Portkey key, and I needed to know where the Expected vs. Actual plan lives.

**Follow-up prompt 2:**

> Please restyle the Expected vs. Actual page in the same navy, white, gold, and silver format as the dashboard. Also, for anything written in my own words, make sure the spelling and grammar are good. Feel free to rewrite it so it reads clearly.

*What was lacking after the previous prompt:* the Expected vs. Actual page still used the old black-and-pink style, and my own-words text needed cleaning up.

---

## Problem 9: Full Run of All Three Tickets

**Prompt 1:**

> I'm now on Problem 9. Before testing the agents on a full run of the three tickets, reset the working database `data/campus_customs_new.db` again so we start clean, and note the starting checking balance. Then run all three tickets on the board (101, 102, and 103) until each one is resolved.
>
> Open `output/desk_tickets.html` from Problem 6. On each ticket tab, fill in the Actual section from this run: which agents worked, what they delegated, and which tools they used. Keep the Expected section so I can compare the two.
>
> On the Cash tab of the same page, itemize the money:
>
> - The starting checking balance (after the reset)
> - For each ticket, how cash changed when that ticket was resolved, and why (which payment or purchase, and the dollar amount)
> - The ending checking balance, which must match cash_accounts in the working database
>
> Wrong cash math loses points even if the board shows every ticket resolved. Also save:
>
> - `output/resolved_tickets.json`: for each ticket, its ID, final status, a short outcome, what each agent contributed, and any human approvals
> - `output/resolved_board.html`: a page I can double-click, with a screenshot of the React board for each resolved ticket (101, 102, and 103)
>
> Append the real runs to `output/audit_trail.json`. Finish `output/harness.md` so it covers the tables, MCP tools, the five agents, the API routes, the dashboard, and the safety rules.

**Follow-up prompt:** None needed yet.

---

## Problem 10: Reflection

**Prompt 1:**

> I'm now on Problem 10. Please open `output/desk_tickets.html` and fill in the Reflection tab. I'll answer in my own words; feel free to make my answers more detailed, add anything I've missed, and fill in anything I've left blank.
>
> - **How would you evaluate the agents' performance on each ticket, and why?** Timing was quick on each one, with no hold-ups. The order of operations made sense, and the agents didn't take unnecessary actions. The draft emails were great too.
> - **For each ticket, how did the Actual compare to the Expected plan written earlier?**
>   - Ticket 101: Expected and Actual lined up, except the rent was queued here instead of on ticket 102, and an unnecessary $8 purchase order was created.
>   - Ticket 102: I expected the route to be Facilities → Accounting, but the Boss routed Accounting itself because Facilities had already reported the rent was queued.
>   - Ticket 103: Everything went as planned. The only minor difference is that the offer quotes the total for all 20 rather than just the 8 available.
> - **What would have been simpler as one agent with tools, and why?** Facilities wasn't necessary in this case, though it might be for other work.
> - **Describe three new problems Campus Customs might face that this agent team could solve with the tools I built.** I need suggestions here, and I'll approve them.
> - **Describe three new problems the team could not solve with the tools I built, and explain the tools and agents needed to solve them.** I need suggestions here, and I'll approve them.
>
> Tie every answer to this app and the three tickets I ran, using the ticket tabs and the Cash tab on the same page as evidence. Generic AI essays without Campus Customs details score low.

**Follow-up prompt:**

> All six suggestions are good.

*What was lacking after the first prompt:* I'd left the "could solve" and "could not solve" questions for the vibe coder to suggest, so I needed to review and approve the six Campus Customs-specific ideas before they counted as my answers.

---

## Problem 11: Push to a Public GitHub Repo

**Prompt 1:**

> Please check that everything is ready to submit. Then, for Problem 11, push the code to a public GitHub repository so graders can clone it. Give me the repo URL so I can submit it, and also put it in `output/github_url.txt`. Don't push the real `.env`, but do include both database files under `data/` (the original and my working copy) so graders can run the app easily. The README should explain how to copy the original database over the working copy for a clean run, start the MCP server, start the FastAPI backend, start the React board, and reset the database before a full three-ticket run.

**Follow-up prompt:** None needed yet.

---
