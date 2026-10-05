# Campus Customs Multi-Agent Harness

Working notes for the agent team: Boss, Inventory, Accounting, Facilities and Customer Service. This file grows with each problem.

- **Original DB (never modified):** `data/campus_customs.db`
- **Working copy (tools read and write this):** `data/campus_customs_new.db`
- **Shop "today":** `desk.date_today` = **2026-08-31**


**Contents:** [1. Database tables](#1-database-tables) · [2. How the tickets link](#2-how-the-three-open-tickets-link-to-other-tables) · [3. First three MCP tools](#3-mcp-tools-the-first-three-problem-3) · [4. The five agents](#4-the-agent-team-backend) · [5. All MCP tools](#5-mcp-tools-current-mcp_serverserverpy) · [6. Safety](#6-safety) · [7. API routes](#7-backend-api-backendmainpy) · [8. Dashboard](#8-dashboard-frontend) · [9. Full run results](#9-full-run-results-problem-9) · [10. Output files](#10-output-files)

- **Model:** every agent uses only `gpt-6-luna` through Portkey (`backend/config.py`).

---

## 1. Database tables

### `desk` (1 row)
| Field | Type | Notes |
|---|---|---|
| `date_today` | TEXT | The shop's "today" (`2026-08-31`) |
| `notes` | TEXT | Free-form desk notes (empty) |

**Why it matters:** every agent measures overdue and due-soon against this date, not the real calendar.

### `tickets` (3 rows, all `open`)
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Ticket number (101–103) |
| `type` | TEXT | `customer_order`, `rent_notice`, `price_override` |
| `requester` | TEXT | Who asked (customer, landlord, student org) |
| `subject` | TEXT | Short title |
| `sku` | TEXT | → `inventory.sku` / `pricing.sku` (product tickets) |
| `size` | TEXT | → `inventory.size` |
| `qty` | INTEGER | Units requested |
| `lease_id` | INTEGER FK | → `leases.id` (rent tickets) |
| `invoice_id` | INTEGER FK | → `invoices.id` (related vendor bill) |
| `status` | TEXT | `open` → updated as tickets get resolved |
| `notes` | TEXT | Request details |
| `created_at` | TEXT | ISO timestamp |

**Why it matters:** the work queue. The Boss reads each ticket and routes it by `type` and by which foreign keys are filled in.

### `inventory` (10 rows, PK = `sku` + `size`)
| Field | Type | Notes |
|---|---|---|
| `sku` | TEXT | Product code |
| `name` | TEXT | Product name |
| `size` | TEXT | S / M / L / XL, or OS (one size) |
| `qty` | INTEGER | Units on hand |
| `location` | TEXT | Aisle |

**Why it matters:** Inventory checks stock by SKU and size here and spots shortfalls (white tee S = 0, crest mug = 0).

### `pricing` (4 rows)
| Field | Type | Notes |
|---|---|---|
| `sku` | TEXT PK | → `inventory.sku` |
| `unit_cost` | REAL | What the shop pays per unit |
| `list_price` | REAL | Normal selling price |

**Why it matters:** Accounting uses cost and list price to check margins on discount requests and to cost out restock purchase orders.

### `vendors` (3 rows)
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Vendor id |
| `name` | TEXT | Bulldog Print Co / Elm City Gifts / QuickShip CT |
| `specialty` | TEXT | Apparel reprint / mugs and small goods / local courier |
| `lead_days` | INTEGER | Days to deliver (5 / 3 / 1) |

**Why it matters:** Inventory picks a vendor that can restock by matching `specialty`; `lead_days` gives the earliest restock date. A vendor with an open, unpaid invoice will not ship.

### `invoices` (1 row)
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Invoice number |
| `vendor_id` | INTEGER FK | → `vendors.id` |
| `amount` | REAL | Amount owed |
| `due_date` | TEXT | Overdue if before `desk.date_today` and still open |
| `status` | TEXT | `open` → `paid` |
| `description` | TEXT | What it was for |

**Why it matters:** Accounting tracks what the shop owes here. An open invoice blocks that vendor from shipping, so it gates Inventory's restock plans.

### `leases` (1 row)
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Lease id |
| `space_name` | TEXT | Chapel Street shop |
| `landlord` | TEXT | Elm City Properties |
| `monthly_rent` | REAL | $2,400 |
| `next_due` | TEXT | Next rent date → moves forward one month when paid |
| `notes` | TEXT | Free-form |

**Why it matters:** Facilities owns the shop space. It checks when rent is due and prepares the rent payment for approval.

### `cash_accounts` (1 row)
| Field | Type | Notes |
|---|---|---|
| `name` | TEXT PK | `checking` |
| `balance` | REAL | $3,400.00 |
| `date` | TEXT | Balance as-of date |

**Why it matters:** the only money the shop has (cash only goes out; there is no revenue). The pay tool must refuse any payment that would make the balance negative.

### `payments` (0 rows)
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Payment id |
| `kind` | TEXT | e.g. `invoice`, `rent`, `purchase_order` |
| `ref_id` | INTEGER | id of the invoice or lease being paid |
| `amount` | REAL | Amount paid |
| `account` | TEXT | → `cash_accounts.name` |
| `paid_at` | TEXT | Date paid |
| `approved_by` | TEXT | The human approver (required; agents cannot pay on their own) |

**Why it matters:** the audit trail. Every approved payment writes a row here, and `approved_by` is the record that a human signed off.


### Board tables (added to the working copy by the MCP server)
| Table | Fields | Why it matters |
|---|---|---|
| `payment_requests` | id, kind (`invoice` / `rent` / `purchase_order`), ref_id, vendor_id, sku, size, qty, payee, amount, ticket_id, reason, requested_by, status (`pending` / `paid` / `rejected`), created_on, decided_by, decided_on, decision_note, payment_id, expected_arrival | The approval queue. Agents can only add `pending` rows; a human turns them into `paid` or `rejected` |
| `drafts` | id, ticket_id, recipient, subject, body, author, status (`draft`), created_on | Customer messages stay on the board, never sent |

These two tables exist only in `campus_customs_new.db`. The original database never gets them.

---

## 2. How the three open tickets link to other tables

```
tickets ─┬─ sku, size ──► inventory (qty) ──► pricing (cost / list)
         ├─ invoice_id ─► invoices ─ vendor_id ─► vendors (lead_days)
         └─ lease_id ───► leases (rent, next_due)
                 all payments ──► cash_accounts (balance) + payments (audit row)
```

### Ticket 101: `customer_order` · Tauhid Zaman · 1 × CC-TEE-WHITE size S
- **inventory:** Classic Bulldog Tee S has **qty 0**, so the shop is short 1 unit.
- **invoice_id 501 → invoices:** $840.00 to vendor 1, "Rush reprint CC-TEE-WHITE S", due 2026-08-28, status `open`, so it is **3 days overdue**.
- **vendors:** vendor 1 is Bulldog Print Co (apparel reprint, 5-day lead time). It **will not ship** while invoice 501 is unpaid.
- **pricing:** cost $8, list $28.
- **Path:** human-approved payment of invoice 501 → Bulldog can ship → earliest restock about 2026-09-05 → Customer Service drafts an honest ETA for Tauhid.

### Ticket 102: `rent_notice` · Elm City Properties · rent due
- **lease_id 1 → leases:** Chapel Street shop, $2,400/month, `next_due` **2026-09-02**, which is in 2 days (due soon, not overdue).
- **Path:** Facilities confirms the amount and date → Accounting checks cash → human approves → pay → `leases.next_due` moves to 2026-10-02.

### Ticket 103: `price_override` · Yale AI Club · 20 × CC-HOOD-NAVY size M, bulk discount
- **inventory:** Basic Hoodie M has **qty 8**, so the shop is short **12 units**.
- **pricing:** cost $22, list $58. At list price, 20 units = $1,160 revenue vs $440 cost (62% margin). Any discount should keep a healthy margin.
- **vendors:** hoodies are apparel, so the restock comes from Bulldog Print Co, which is the same vendor **blocked by invoice 501**.
- **Path:** Inventory reports the shortfall → Accounting proposes a discount that protects the margin → restock PO goes to Bulldog only after 501 is paid → Customer Service drafts the reply to the club.

### Cash picture (what the Boss has to balance)
| Item | Amount | Running balance |
|---|---|---|
| Starting checking | | $3,400.00 |
| Invoice 501 (overdue) | −$840.00 | $2,560.00 |
| Rent, lease 1 (due 09-02) | −$2,400.00 | $160.00 |
| Restock 12 hoodies @ $22 | −$264.00 | **−$104.00 ✗** |

Paying the overdue invoice and the rent fits ($160 left over), but the hoodie restock PO would then make the balance negative, so the pay tool must refuse it. Since no revenue comes in, the Boss has to prioritise. The likely call is to pay the overdue invoice and the rent, then offer the club the 8 hoodies on hand or a later date for the rest.

---

## 3. MCP tools: the first three (Problem 3)

The server reads `data/campus_customs_new.db` only. All three tools are read-only and return an error instead of a guess when a row is missing.

| Tool | Reads | Unlocks ticket | Why it's the right tool for that ticket |
|---|---|---|---|
| `check_stock(sku, size, qty_needed)` | `inventory` | **103**, Yale AI Club, 20 × CC-HOOD-NAVY M | The club wants 20 size-M hoodies, and this returns the 8 on hand with a shortfall of 12. That tells the Boss whether to quote all 20 now or only 8, and how many units a restock would need before Accounting prices the discount. *(It also confirms ticket 101's tee S is at 0.)* |
| `get_invoice_status(invoice_id)` | `invoices`, `vendors`, `desk` | **101**, Tauhid's tee S (`invoice_id` 501) | The tee is out of stock and only Bulldog Print Co can reprint it. This tool shows invoice 501 ($840) is open and 3 days past `desk.date_today`, and returns `vendor_blocked_from_shipping = true` with Bulldog's 5-day lead time. That is exactly why the order is stuck, and it says what must be paid (with human approval) before Customer Service can give Tauhid a real ETA. |
| `get_lease_rent_due(lease_id)` | `leases`, `desk` | **102**, Elm City Properties rent notice (`lease_id` 1) | The landlord's email says rent is "due in 2 days". This tool checks that claim against the lease itself ($2,400, `next_due` 2026-09-02, `days_until_due = 2`, `upcoming`), so Facilities works from the database rather than the email, and Accounting knows the exact amount and deadline to queue for approval. |

---

## 4. The agent team (`backend/`)

Built with PydanticAI. Every agent uses **only `gpt-6-luna`** through Portkey (OpenAI Responses API, in `backend/config.py`). A model guard stops the run if any response comes back from a different model.

| Agent | File / prompt | Role | Output |
|---|---|---|---|
| **Boss** | `agents/boss.py` · `prompts/boss.md` | Reads each ticket, routes it to the fewest specialists, weighs cash and margin trade-offs, sets ticket status, makes the final call | `TicketOutcome` |
| **Inventory** | `agents/inventory.py` · `prompts/inventory.md` | Stock by SKU and size, shortfalls, which vendor can restock, lead time, whether the vendor is blocked. Never makes up numbers | `AgentReport` |
| **Accounting** | `agents/accounting.py` · `prompts/accounting.md` | Cash, invoices, margins and discount math. Prepares invoice, rent and PO payment requests for human approval only | `AgentReport` |
| **Facilities** | `agents/facilities.py` · `prompts/facilities.md` | The shop's real-estate person: lease, rent schedule, landlord. Checks rent notices against the lease | `AgentReport` |
| **Customer Service** | `agents/customer_service.py` · `prompts/customer_service.md` | Answers questions (with an FAQ) and saves honest customer drafts on the board. Never sends anything | `AgentReport` |

- **Shared rules** for all five agents are in `prompts/team_charter.md`: facts only from MCP, desk date, vendor lead times, blocked vendors, human-approved money, no negative cash, no outside contact, token budget.
- **Full connectivity:** every agent has a `delegate(to_agent, task)` tool that can reach any other agent. A specialist can ask another specialist, for example Inventory → Accounting for a PO. Delegation runs that agent's own loop and returns its structured report.
- **Agent loop:** `CampusTeam.run_agent` (`agents/team.py`) steps through each PydanticAI run node by node: model request → model response (tool calls) → tool results → … → final output.
- **Audit trail:** every step is appended to `output/audit_trail.json`, which is never wiped. Each entry records timestamp, run_id, ticket_id, agent, delegation depth and chain, and the event (`run_start`, `model_request`, `model_response` with model name and token usage, `tool_call` with args, `tool_result` with output and latency, `delegation`, `guard_block`, `error`, `run_end` with output and cumulative ticket usage).
- **How to run:** `python -m backend.run_ticket --all --reset` resets the working DB, then works every open ticket. Offline wiring test with no LLM: `python -m tests.test_team_wiring`.

## 5. MCP tools (current, `mcp_server/server.py`)

All shop facts reach the agents through this server over `data/campus_customs_new.db`. There is no other data layer. "Who can use it" is enforced by per-agent allowlists in `backend/agents/*.py`.

| Tool | Tables | Kind | Who can use it |
|---|---|---|---|
| `get_shop_today` | desk | read | all |
| `list_open_tickets` | tickets | read | Boss |
| `list_tickets` | tickets | read | backend API only (dashboard ticket list) |
| `get_ticket` | tickets | read | all |
| `check_stock` | inventory | read | Inventory, Customer Service |
| `get_product_pricing` | pricing, inventory | read | Inventory, Accounting, Customer Service |
| `check_margin` | pricing | read | Accounting |
| `list_vendors` | vendors, invoices, desk | read | Inventory, Accounting, Customer Service |
| `get_invoice_status` | invoices, vendors, desk | read | Inventory, Accounting |
| `list_open_invoices` | invoices, vendors, desk | read | Accounting |
| `get_lease_rent_due` | leases, desk | read | Facilities, Accounting |
| `get_cash_position` | cash_accounts, payment_requests | read | Boss, Accounting, Facilities |
| `list_payment_requests` | payment_requests | read | Boss, Accounting, Facilities |
| `list_drafts` | drafts | read | Boss, Customer Service |
| `request_payment_approval` | invoices / leases → payment_requests | write (request only) | Accounting |
| `create_purchase_order_request` | vendors, inventory, pricing, invoices → payment_requests | write (request only) | Accounting |
| `save_customer_draft` | tickets → drafts | write (draft only) | Customer Service |
| `update_ticket_status` | tickets | write | Boss |
| `approve_payment` | payment_requests, cash_accounts, payments, invoices / leases | **money, HUMAN ONLY** | no agent (dashboard only) |
| `reject_payment` | payment_requests | **HUMAN ONLY** | no agent (dashboard only) |

`payment_requests` and `drafts` are board tables the server creates in the working copy. The original DB is never touched.

## 6. Safety

**Guardrails for real customers and real money**
- **Human in the loop for every dollar:** agents can only create *pending* requests. `approve_payment` and `reject_payment` are never given to an agent, the backend blocks them a second time if one tries, and the server rejects a blank or agent-named approver. Every payment records `approved_by`.
- **No negative balances:** `approve_payment` refuses if cash < amount, checked inside a single database transaction. Accounting must also check cash *plus pending requests* before asking.
- **Amounts come from the database, not the model:** invoice and rent amounts are read from their rows, and PO amounts are qty × `unit_cost`. An agent can't type in a bigger number.
- **Vendor rule enforced in code:** a PO for a vendor with an open invoice is refused at payment time.
- **Duplicate protection:** a second pending request for the same invoice or lease is rejected.
- **Least privilege:** each agent sees only the tools its job needs (for example, only Accounting can request payments and only Customer Service can draft messages).
- **No impersonation:** `requested_by`, `author` and `updated_by` are stamped by the backend with the real agent's name.
- **No outside contact:** no email or vendor-call tools exist. Customer text is a draft on the board.
- **No invented facts:** missing rows return errors, and prompts require each fact to cite its tool.
- **Full audit:** the append-only `audit_trail.json` records every step, so any decision can be traced to the tool output behind it.
- **Reset path:** the original DB stays untouched, and `python -m backend.reset_db` restores the working copy.

**Limits that keep token use in check**
- **One model** (`gpt-6-luna`) for every agent. The model guard refuses any response from another model.
- **Per-ticket caps** shared across all delegated runs: 30 model requests and 150k total tokens (`UsageLimits`). `max_tokens` = 1,200 per response.
- **Delegation caps:** at most 6 delegations per ticket, depth ≤ 2, no self-delegation, no delegating back up the chain (prevents ping-pong loops).
- **Prompts tell agents to be brief:** fewest tool calls, one pass of delegation (the Boss aims for ≤ 4), no repeated calls, short structured reports.
- **Small, precomputed tool results:** for example `check_margin` and `get_cash_position` do the math server-side, so agents don't need extra reasoning turns. Long text in the audit trail is clipped.

---

## 7. Backend API (`backend/main.py`)

Start from `backend/` with `uvicorn main:app --reload --port 8000`, which serves http://localhost:8000. Interactive docs are at `/docs`. Every route reaches the database through the MCP server, never SQLite directly.

- `GET  /api/tickets` lists every ticket with its status and whether it is `open` or `resolved`.
- `POST /api/tickets/{ticket_id}/run` starts the agent team (Boss plus delegations) on one ticket and returns a `run_id` right away (202).
- `GET  /api/runs/{run_id}` shows a run's status (`queued`, `running`, `done` with the Boss's `TicketOutcome`, or `error`).
- `GET  /api/events?since=&ticket_id=&run_id=` returns recent agent events from `audit_trail.json`: what each agent said, which tools it called with what args and results, delegations, and guard blocks. Poll with `since=last_id`.
- `GET  /api/payments?status=` is the approval queue: payment and purchase-order requests the agents prepared.
- `POST /api/payments/{request_id}/approve` `{approved_by}` is the human Approve click. It is the **only** route that changes cash: it pays via MCP `approve_payment` and updates cash_accounts, payments and the invoice or lease. It refuses on insufficient cash or a blocked vendor (409).
- `POST /api/payments/{request_id}/reject` `{decided_by, reason}` is the human Reject click. No money moves.
- `GET  /api/cash` returns the current checking balance from cash_accounts, plus pending requests and the balance if they were all paid.
- `GET  /api/drafts?ticket_id=` returns customer drafts the agents left on the board (never sent).
- `POST /api/reset` restores `campus_customs_new.db` from the original `campus_customs.db` for a fresh run. The audit trail is kept and gets a `db_reset` event.
- `GET  /api/health` reports server, model and team readiness.

---

## 8. Dashboard (`frontend/`)

React + Vite + TypeScript. Start it with `npm run dev`, which serves http://localhost:5173 and calls the backend at http://localhost:8000. CORS in `backend/main.py` allows `http://localhost:5173` and `http://127.0.0.1:5173`.

- **Docket:** lists all three tickets; seals show open, in session or resolved.
- **Convene the team:** `POST /api/tickets/{id}/run`, then polls `/api/runs/{run_id}` and `/api/events`.
- **Boardroom:** each agent's nameplate lights up while it works, with its latest words; gold lines show delegations.
- **Minutes:** what each agent said and every MCP tool it used, with arguments and results.
- **Resolution:** a ticket is marked **resolved** when the run finishes. The Boss sets it, and the backend makes sure of it. The panel shows the Boss's decision, the human's next steps, a short brief per agent, and any customer draft.
- **Treasury:** checking balance (`/api/cash`); pending payments and POs appear as cheques the human signs (`POST /api/payments/{id}/approve`). The balance drops after an approved payment, and refusals (insufficient cash, blocked vendor) show on the cheque.
- **Reset the books:** `POST /api/reset`.
- **UI testing without an LLM:** `python tests/run_demo_backend.py` runs a scripted stand-in on scratch copies. The header shows "scripted-demo (no LLM)". It's never used for real runs.

Design rationale: `output/design.md`.

---

## 9. Full run results (Problem 9)

The working DB was reset first (starting checking **$3,400.00**), then tickets 101 → 102 → 103 were run on the board one at a time, and a human (Abby Jaye) signed the cheques on the dashboard. Every model response was `gpt-6-luna-global`.

| Ticket | Delegations | Outcome | Cash |
|---|---|---|---|
| 101 · Tee | Boss → Inventory, Boss → Accounting, Boss → Customer Service | Size S out of stock and the vendor blocked by invoice 501. Queued #1 invoice 501 ($840) and #3 a 1-tee PO ($8); Accounting also queued #2 rent early. Draft #1 to Tauhid | −$848.00 |
| 102 · Rent | Boss → Facilities, Boss → Accounting | Lease confirms $2,400 due 09-02. Rent was already queued as #2, so no duplicate | −$2,400.00 |
| 103 · Hoodies | Boss → Inventory, Boss → Accounting, Boss → Customer Service | Offer $48 each (54.2% margin), 8 now; the 12-unit restock ($264) isn't affordable, so no PO. Draft #2 to the Yale AI Club | $0.00 |

**Cash:** $3,400.00 − $840.00 (#1) − $2,400.00 (#2) − $8.00 (#3) = **$152.00**, which matches `cash_accounts.checking.balance` in the working DB. Three `payments` rows, all `approved_by = Abby Jaye`. Invoice 501 → `paid`, lease 1 `next_due` → 2026-10-02, PO expected arrival 2026-09-05.

**Expected vs actual:**
- First call and the specialists involved matched the plan on all three tickets. Facilities was correctly skipped on 101 and 103.
- Differences: Accounting queued the rent during 101 instead of 102, and created an $8 PO the plan didn't expect. On 102 the Boss routed Accounting itself instead of Facilities handing off.
- Token use: 16 / 11 / 14 model calls (about 50k, 27k and 44k input tokens), well inside the per-ticket caps. Accounting tends to fetch more tools than it needs.

Full detail: `output/desk_tickets.html` (Actual + Cash tabs) and `output/resolved_tickets.json`.

## 10. Output files

| File | What it holds |
|---|---|
| `output/harness.md` | This file: tables, tools, agents, routes, dashboard, safety, run results |
| `output/mcp_smoke.json` | Problem 4: vibe-coder calls to the three MCP tools, with outputs matched to the DB |
| `output/audit_trail.json` | Append-only log of every agent-loop step, human approval and DB reset |
| `output/desk_tickets.html` | Expected plan vs actual run per ticket, plus the Cash reconciliation |
| `output/design.md` | Dashboard design choices and rationale |
| `output/resolved_tickets.json` | Per-ticket final status, outcome, agent contributions and human approvals |
| `output/resolved_board.html` + `output/screenshots/` | Screenshots of the React board for each resolved ticket |
