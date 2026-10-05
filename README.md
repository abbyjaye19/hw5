# Campus Customs: Multi-Agent Operations (HW 5)

An agent team that works the Campus Customs shop's ticket board: customer orders, rent, unpaid bills and discount requests. A human watches the agents on a dashboard and signs every payment.

- **MCP server** (`mcp_server/`, FastMCP): the only way agents touch the shop database
- **FastAPI backend** (`backend/`): a PydanticAI team of five agents (Boss, Inventory, Accounting, Facilities, Customer Service) with full delegation, plus the API the board calls
- **React dashboard** (`frontend/`, Vite + TypeScript): pick a ticket, watch the agents work, approve payments, see cash change
- **Model:** every agent uses **gpt-6-luna** through Portkey

## Requirements

- Python 3.12+ and Node.js 20+
- A Portkey API key

## 1. Setup

```bash
git clone https://github.com/abbyjaye19/hw5.git
cd hw5

python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

copy .env.example .env          # macOS/Linux: cp .env.example .env
#   then put your PORTKEY_API_KEY in .env

cd frontend
npm install
cd ..
```

## 2. The databases (`data/`)

| File | Role |
|---|---|
| `data/campus_customs.db` | **Original** shop database. Never modified; it's the reset point |
| `data/campus_customs_new.db` | **Working copy.** The MCP server and backend read and write only this file |

The working copy is committed in its **post-run state** (after the Problem 9 full run: checking $152.00, all three tickets resolved). **For a clean run, copy the original over the working copy first**, using any one of these:

```bash
python -m backend.reset_db                      # from hw5/
```

```bash
copy data\campus_customs.db data\campus_customs_new.db
```

…or click **Reset the books** on the dashboard (which calls `POST /api/reset`). All three restore checking to $3,400.00 and reopen tickets 101–103. The audit trail is never wiped.

## 3. Start the MCP server

The backend starts the MCP server itself over stdio, so you don't need to run it separately for the app. To run it on its own (or to let a vibe coder call the tools through `.mcp.json`):

```bash
python mcp_server/server.py
```

`.mcp.json` registers it as `campus-customs` for Claude Code when a session is opened in this folder.

## 4. Start the FastAPI backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

This serves http://localhost:8000 (interactive docs at `/docs`). It allows the Vite origin `http://localhost:5173`.

## 5. Start the React board

In a second terminal:

```bash
cd frontend
npm run dev
```

This opens http://localhost:5173: the docket of tickets, the boardroom of agents, live minutes, and the Treasury with cheques to sign.

## 6. A full three-ticket run

1. **Reset the DB** (section 2). Starting checking should be **$3,400.00**.
2. On the board, select ticket **101** and click **Convene the team**. Wait until its seal shows resolved, then do the same for **102** and **103**, one at a time (they share one cash account).
3. In the Treasury, type your name as the authorised signatory and **Sign & approve** the cheques the agents prepared. Approve vendor invoices before purchase orders to the same vendor; a PO to a vendor with an open invoice is refused.
4. Every agent-loop step is appended to `output/audit_trail.json`.

CLI alternative: `python -m backend.run_ticket --all --reset`.

## Project layout

```
hw5/
├── AI_prompts.md            prompts I typed, per problem
├── requirements.txt
├── .env.example             copy to .env (the real .env is git-ignored)
├── .gitignore
├── .mcp.json                registers the MCP server for the vibe coder
├── data/                    campus_customs.db (original) + campus_customs_new.db (working copy)
├── mcp_server/              server.py (FastMCP tools) + README.md
├── backend/
│   ├── main.py              FastAPI routes
│   ├── models.py            data types
│   ├── config.py            gpt-6-luna via Portkey, token limits, model guard
│   ├── agents/              boss / inventory / accounting / facilities / customer_service + team.py (loops, delegation)
│   ├── prompts/             one prompt per agent + team_charter.md
│   ├── audit.py             append-only audit trail
│   └── reset_db.py          copy the original DB over the working copy
├── frontend/                React + Vite + TypeScript dashboard
├── tests/                   offline wiring test + scripted UI demo (no LLM)
└── output/
    ├── harness.md           tables, MCP tools, agents, routes, dashboard, safety, run results
    ├── mcp_smoke.json       vibe-coder MCP tool test
    ├── desk_tickets.html    Expected vs Actual per ticket, Cash, Reflection
    ├── design.md            dashboard design
    ├── resolved_tickets.json
    ├── resolved_board.html  (+ screenshots/)
    ├── audit_trail.json
    └── github_url.txt
```

## Safety, in brief

Agents can only *request* payments. Only a human approving on the dashboard moves money, and the pay tool refuses negative balances and shipments from vendors with open invoices. Customer messages are drafts only. Every agent sees only the MCP tools its role needs. Details: `output/harness.md`, section 6.
