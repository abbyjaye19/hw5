# Campus Customs MCP Server

A [FastMCP](https://gofastmcp.com) server that is the shared tool belt for every agent on the Campus Customs operations team (Boss, Inventory, Accounting, Facilities, Customer Service). Agents never query SQLite directly. All shop facts come through these tools, which return only what is in the database and never invent stock, prices, dates or amounts.

## Database

- **Uses:** `data/campus_customs_new.db`, the working copy that tools read and update as tickets are resolved.
- **Never touches:** `data/campus_customs.db`, the original. The server refuses to start if pointed at it, and `python -m backend.reset_db` copies it over the working copy for a clean run.
- **Board tables:** on first connect the server adds `payment_requests` and `drafts` to the working copy.
- **Override (optional):** set `CAMPUS_CUSTOMS_DB` to another path.
- **"Today"** for every date calculation is `desk.date_today` (2026-08-31), not the real calendar.

## Tools

### Read
| Tool | Reads | Returns |
|---|---|---|
| `get_shop_today()` | desk | The shop's "today" and desk notes |
| `list_open_tickets()` | tickets | Every unresolved ticket |
| `list_tickets()` | tickets | Every ticket (open and resolved) with `is_resolved`, used by the dashboard API |
| `get_ticket(ticket_id)` | tickets | One ticket with all fields |
| `check_stock(sku, size, qty_needed?)` | inventory | On hand, `can_fill_now`, `shortfall` |
| `get_product_pricing(sku)` | pricing, inventory | Unit cost, list price, margin at list |
| `check_margin(sku, qty, unit_price)` | pricing | Revenue, cost, profit, margin %, discount % vs list |
| `list_vendors()` | vendors, invoices, desk | Specialty, lead days, earliest arrival, blocked-by-open-invoice |
| `get_invoice_status(invoice_id)` | invoices, vendors, desk | Amount, due date, days overdue, vendor lead time, vendor blocked |
| `list_open_invoices()` | invoices, vendors, desk | All unpaid invoices with days overdue |
| `get_lease_rent_due(lease_id)` | leases, desk | Rent, next due date, days until due, status |
| `get_cash_position(account?)` | cash_accounts, payment_requests | Balance, pending requests, balance if all paid |
| `list_payment_requests(status?)` | payment_requests | The approval board |
| `list_drafts(ticket_id?)` | drafts | Customer drafts on the board |

### Write (agents: requests and drafts only, no money moves)
| Tool | Writes | Notes |
|---|---|---|
| `request_payment_approval(kind, ref_id, requested_by, reason, ticket_id?)` | payment_requests | Invoice or rent. The amount is read from the DB. Duplicate pending requests are refused |
| `create_purchase_order_request(vendor_id, sku, size, qty, requested_by, reason, ticket_id?)` | payment_requests | Amount = qty × unit_cost. Reports whether the vendor is blocked and its expected arrival |
| `save_customer_draft(ticket_id, recipient, subject, body, author)` | drafts | Saved on the board, never sent |
| `update_ticket_status(ticket_id, status, note, updated_by)` | tickets | Appends a dated note and keeps the original request text |

### Human only (never given to agents)
| Tool | Writes | Notes |
|---|---|---|
| `approve_payment(request_id, approved_by)` | payments, cash_accounts, invoices / leases, payment_requests | Refuses a blank or agent approver, insufficient cash (no negative balance), or a PO to a vendor with an open invoice. Marks the invoice paid, moves the lease `next_due` forward a month, or records the PO's expected arrival |
| `reject_payment(request_id, decided_by, reason)` | payment_requests | No money moves |

## Run

```bash
pip install -r requirements.txt
python mcp_server/server.py   # stdio transport
```

Claude Code connects through the project's `.mcp.json`. The agent backend starts the same server over stdio.
