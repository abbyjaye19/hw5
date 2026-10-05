"""Campus Customs MCP server (FastMCP).

Shared tool belt for every agent on the Campus Customs operations team.
Reads and writes the WORKING copy of the shop database:

    data/campus_customs_new.db

The original data/campus_customs.db is never opened, so it can be used to reset.
Tools only report what is in the database; missing rows come back as errors
rather than guesses. Money amounts are always computed here from the database,
never taken from an agent.

Payment flow (human approval required):
  agents  -> request_payment_approval / create_purchase_order_request  (status 'pending')
  human   -> approve_payment (pays, updates tables) or reject_payment
Agents are never given approve_payment / reject_payment (see backend allowlists).

Run:  python mcp_server/server.py
"""

from __future__ import annotations

import calendar
import os
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Literal

from fastmcp import FastMCP

HW_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("CAMPUS_CUSTOMS_DB", HW_ROOT / "data" / "campus_customs_new.db")).resolve()
ORIGINAL_DB = (HW_ROOT / "data" / "campus_customs.db").resolve()

if DB_PATH == ORIGINAL_DB:
    raise RuntimeError("Refusing to use the original campus_customs.db; point at campus_customs_new.db.")

AGENT_NAMES = {"boss", "inventory", "accounting", "facilities", "customer_service"}
TICKET_STATUSES = ("open", "in_progress", "waiting_approval", "blocked", "resolved")

READ_ONLY = {"readOnlyHint": True, "openWorldHint": False}
WRITES = {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False}
MONEY = {"readOnlyHint": False, "destructiveHint": True, "openWorldHint": False}

mcp = FastMCP(
    name="campus-customs",
    instructions=(
        "Tools for the Campus Customs shop database (working copy). "
        "Use these to look up facts; never invent stock, prices, dates or amounts. "
        "The shop's 'today' is desk.date_today, not the real calendar. "
        "Payments are only ever requested by agents; a human approves them."
    ),
)

# Board tables the team adds to the working copy (the original DB is never touched).
BOARD_SCHEMA = """
CREATE TABLE IF NOT EXISTS payment_requests (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,              -- invoice | rent | purchase_order
    ref_id INTEGER,                  -- invoices.id or leases.id (NULL for purchase orders)
    vendor_id INTEGER,
    sku TEXT, size TEXT, qty INTEGER,
    payee TEXT NOT NULL,
    amount REAL NOT NULL,
    ticket_id INTEGER,
    reason TEXT,
    requested_by TEXT NOT NULL,
    status TEXT NOT NULL,            -- pending | paid | rejected
    created_on TEXT NOT NULL,
    decided_by TEXT, decided_on TEXT, decision_note TEXT,
    payment_id INTEGER,
    expected_arrival TEXT
);
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER,
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    author TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',   -- drafts are never sent
    created_on TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Working database not found: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(BOARD_SCHEMA)
    return conn


def _today(conn: sqlite3.Connection) -> date:
    """The shop's 'today' from desk.date_today."""
    row = conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
    if not row:
        raise ValueError("desk.date_today is missing from the database")
    return date.fromisoformat(row["date_today"])


def _add_month(d: date) -> date:
    y, m = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return d.replace(year=y, month=m, day=min(d.day, calendar.monthrange(y, m)[1]))


def _vendor_open_invoices(conn: sqlite3.Connection, vendor_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT id, amount, due_date FROM invoices WHERE vendor_id = ? AND status = 'open' ORDER BY due_date",
        (vendor_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _cash(conn: sqlite3.Connection, account: str = "checking") -> sqlite3.Row | None:
    return conn.execute("SELECT name, balance, date FROM cash_accounts WHERE name = ?", (account,)).fetchone()


# ---------------------------------------------------------------- read tools


@mcp.tool(annotations=READ_ONLY)
def get_shop_today() -> dict[str, Any]:
    """The shop's official 'today' (desk.date_today) plus desk notes. Use this date for every overdue / due-soon check."""
    with _connect() as conn:
        row = conn.execute("SELECT date_today, notes FROM desk LIMIT 1").fetchone()
    return {"date_today": row["date_today"], "notes": row["notes"]}


@mcp.tool(annotations=READ_ONLY)
def list_open_tickets() -> list[dict[str, Any]]:
    """All tickets on the board that are not resolved yet, oldest first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM tickets WHERE status != 'resolved' ORDER BY created_at"
        ).fetchall()
    return [dict(r) for r in rows]


@mcp.tool(annotations=READ_ONLY)
def list_tickets() -> list[dict[str, Any]]:
    """Every ticket on the board (open and resolved) with its current status, by id."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, type, requester, subject, sku, size, qty, lease_id, invoice_id, status, notes, created_at "
            "FROM tickets ORDER BY id"
        ).fetchall()
    return [{**dict(r), "is_resolved": r["status"] == "resolved"} for r in rows]


@mcp.tool(annotations=READ_ONLY)
def get_ticket(ticket_id: int) -> dict[str, Any]:
    """One ticket with every field (type, requester, sku/size/qty, lease_id, invoice_id, status, notes)."""
    with _connect() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if not row:
        return {"found": False, "error": f"No ticket with id {ticket_id}"}
    return {"found": True, **dict(row)}


@mcp.tool(annotations=READ_ONLY)
def check_stock(sku: str, size: str, qty_needed: int | None = None) -> dict[str, Any]:
    """Check units on hand for one product SKU in one size, and the shortfall against a requested quantity.

    Args:
        sku: Product code, e.g. "CC-HOOD-NAVY".
        size: Size code exactly as stored, e.g. "S", "M", "L", "XL" or "OS" (one size).
        qty_needed: Units the ticket asks for. If given, the result includes how many are missing.
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ?",
            (sku.strip(), size.strip()),
        ).fetchone()
        if not row:
            sizes = [r["size"] for r in conn.execute("SELECT size FROM inventory WHERE sku = ?", (sku.strip(),))]
            if sizes:
                return {"found": False, "error": f"{sku} has no size {size!r}; sizes on file: {sizes}"}
            return {"found": False, "error": f"No inventory rows for SKU {sku!r}"}

    result: dict[str, Any] = {"found": True, **dict(row), "qty_on_hand": row["qty"]}
    del result["qty"]
    if qty_needed is not None:
        shortfall = max(qty_needed - row["qty"], 0)
        result.update(
            qty_needed=qty_needed,
            can_fill_now=min(qty_needed, row["qty"]),
            shortfall=shortfall,
            fully_in_stock=shortfall == 0,
        )
    return result


@mcp.tool(annotations=READ_ONLY)
def get_product_pricing(sku: str) -> dict[str, Any]:
    """Unit cost, list price and per-unit margin for one SKU (pricing table), with the product name."""
    with _connect() as conn:
        row = conn.execute(
            """SELECT p.sku, p.unit_cost, p.list_price,
                      (SELECT name FROM inventory i WHERE i.sku = p.sku LIMIT 1) AS name
               FROM pricing p WHERE p.sku = ?""",
            (sku.strip(),),
        ).fetchone()
    if not row:
        return {"found": False, "error": f"No pricing for SKU {sku!r}"}
    unit_profit = row["list_price"] - row["unit_cost"]
    return {
        "found": True,
        **dict(row),
        "unit_profit_at_list": round(unit_profit, 2),
        "margin_pct_at_list": round(100 * unit_profit / row["list_price"], 1),
    }


@mcp.tool(annotations=READ_ONLY)
def check_margin(sku: str, qty: int, unit_price: float) -> dict[str, Any]:
    """Margin check for selling `qty` units of a SKU at a proposed `unit_price` (e.g. a bulk discount).

    Returns revenue, cost, profit, margin % and the discount % versus list price, all from the pricing table.
    """
    if qty <= 0 or unit_price <= 0:
        return {"ok": False, "error": "qty and unit_price must be positive"}
    with _connect() as conn:
        row = conn.execute("SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku.strip(),)).fetchone()
    if not row:
        return {"ok": False, "error": f"No pricing for SKU {sku!r}"}
    revenue = unit_price * qty
    cost = row["unit_cost"] * qty
    return {
        "ok": True,
        "sku": sku,
        "qty": qty,
        "unit_price": unit_price,
        "unit_cost": row["unit_cost"],
        "list_price": row["list_price"],
        "discount_pct_vs_list": round(100 * (1 - unit_price / row["list_price"]), 1),
        "revenue": round(revenue, 2),
        "cost": round(cost, 2),
        "profit": round(revenue - cost, 2),
        "margin_pct": round(100 * (revenue - cost) / revenue, 1),
        "sells_below_cost": unit_price < row["unit_cost"],
    }


@mcp.tool(annotations=READ_ONLY)
def list_vendors() -> list[dict[str, Any]]:
    """Every vendor with specialty, lead time, earliest arrival if ordered today, and whether an open
    unpaid invoice blocks them from shipping new product."""
    with _connect() as conn:
        today = _today(conn)
        vendors = conn.execute("SELECT id, name, specialty, lead_days FROM vendors ORDER BY id").fetchall()
        out = []
        for v in vendors:
            open_inv = _vendor_open_invoices(conn, v["id"])
            out.append(
                {
                    **dict(v),
                    "earliest_arrival_if_ordered_today": (today + timedelta(days=v["lead_days"])).isoformat(),
                    "open_invoices": open_inv,
                    "blocked_from_shipping": bool(open_inv),
                }
            )
    return out


@mcp.tool(annotations=READ_ONLY)
def get_invoice_status(invoice_id: int) -> dict[str, Any]:
    """Look up a vendor invoice: amount, due date, open/paid status, days overdue (vs desk.date_today),
    and the vendor's lead time. A vendor will not ship new product while it has an open unpaid invoice.

    Args:
        invoice_id: The invoice id, e.g. from tickets.invoice_id.
    """
    with _connect() as conn:
        today = _today(conn)
        inv = conn.execute(
            """SELECT i.id, i.vendor_id, i.amount, i.due_date, i.status, i.description,
                      v.name AS vendor_name, v.specialty AS vendor_specialty, v.lead_days AS vendor_lead_days
               FROM invoices i JOIN vendors v ON v.id = i.vendor_id
               WHERE i.id = ?""",
            (invoice_id,),
        ).fetchone()
        if not inv:
            return {"found": False, "error": f"No invoice with id {invoice_id}"}
        open_for_vendor = _vendor_open_invoices(conn, inv["vendor_id"])

    is_open = inv["status"] == "open"
    days_past_due = (today - date.fromisoformat(inv["due_date"])).days
    return {
        "found": True,
        **dict(inv),
        "today": today.isoformat(),
        "is_open": is_open,
        "is_overdue": is_open and days_past_due > 0,
        "days_overdue": max(days_past_due, 0) if is_open else 0,
        "vendor_open_invoices": open_for_vendor,
        "vendor_blocked_from_shipping": bool(open_for_vendor),
    }


@mcp.tool(annotations=READ_ONLY)
def list_open_invoices() -> list[dict[str, Any]]:
    """All unpaid vendor invoices with vendor name and days overdue versus desk.date_today."""
    with _connect() as conn:
        today = _today(conn)
        rows = conn.execute(
            """SELECT i.id, i.vendor_id, v.name AS vendor_name, i.amount, i.due_date, i.status, i.description
               FROM invoices i JOIN vendors v ON v.id = i.vendor_id
               WHERE i.status = 'open' ORDER BY i.due_date"""
        ).fetchall()
    out = []
    for r in rows:
        late = (today - date.fromisoformat(r["due_date"])).days
        out.append({**dict(r), "is_overdue": late > 0, "days_overdue": max(late, 0)})
    return out


@mcp.tool(annotations=READ_ONLY)
def get_lease_rent_due(lease_id: int) -> dict[str, Any]:
    """Look up a shop lease: landlord, monthly rent, next rent due date and how many days until
    (or past) that date, measured from desk.date_today.

    Args:
        lease_id: The lease id, e.g. from tickets.lease_id.
    """
    with _connect() as conn:
        today = _today(conn)
        lease = conn.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases WHERE id = ?",
            (lease_id,),
        ).fetchone()
        if not lease:
            return {"found": False, "error": f"No lease with id {lease_id}"}

    days_until_due = (date.fromisoformat(lease["next_due"]) - today).days
    status = "overdue" if days_until_due < 0 else "due_today" if days_until_due == 0 else "upcoming"
    return {
        "found": True,
        **dict(lease),
        "today": today.isoformat(),
        "days_until_due": days_until_due,
        "rent_status": status,
    }


@mcp.tool(annotations=READ_ONLY)
def get_cash_position(account: str = "checking") -> dict[str, Any]:
    """Cash balance for an account plus the total of payment requests still waiting for human approval,
    and what the balance would be if all of them were approved. Cash only goes out in this shop."""
    with _connect() as conn:
        cash = _cash(conn, account)
        if not cash:
            return {"found": False, "error": f"No cash account {account!r}"}
        pending = conn.execute(
            "SELECT id, kind, payee, amount, ticket_id FROM payment_requests WHERE status = 'pending' ORDER BY id"
        ).fetchall()
    pending_total = round(sum(p["amount"] for p in pending), 2)
    return {
        "found": True,
        "account": cash["name"],
        "balance": cash["balance"],
        "as_of": cash["date"],
        "pending_requests": [dict(p) for p in pending],
        "pending_total": pending_total,
        "balance_if_all_pending_paid": round(cash["balance"] - pending_total, 2),
    }


@mcp.tool(annotations=READ_ONLY)
def list_payment_requests(status: Literal["pending", "paid", "rejected"] | None = None) -> list[dict[str, Any]]:
    """Payment requests on the approval board (optionally filtered by status)."""
    with _connect() as conn:
        if status:
            rows = conn.execute("SELECT * FROM payment_requests WHERE status = ? ORDER BY id", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM payment_requests ORDER BY id").fetchall()
    return [dict(r) for r in rows]


@mcp.tool(annotations=READ_ONLY)
def list_drafts(ticket_id: int | None = None) -> list[dict[str, Any]]:
    """Customer message drafts saved on the board (never sent), optionally for one ticket."""
    with _connect() as conn:
        if ticket_id is None:
            rows = conn.execute("SELECT * FROM drafts ORDER BY id").fetchall()
        else:
            rows = conn.execute("SELECT * FROM drafts WHERE ticket_id = ? ORDER BY id", (ticket_id,)).fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------- agent write tools


@mcp.tool(annotations=WRITES)
def request_payment_approval(
    kind: Literal["invoice", "rent"],
    ref_id: int,
    requested_by: str,
    reason: str,
    ticket_id: int | None = None,
) -> dict[str, Any]:
    """Queue a vendor-invoice or rent payment for HUMAN approval. Does NOT move any money.

    The amount is read from the database (invoice amount or lease monthly rent), never supplied by the caller.

    Args:
        kind: "invoice" (ref_id = invoices.id) or "rent" (ref_id = leases.id).
        ref_id: The invoice or lease id.
        requested_by: Agent asking for the payment.
        reason: One or two sentences the human approver will read.
        ticket_id: Ticket this payment unblocks, if any.
    """
    with _connect() as conn:
        today = _today(conn)
        if kind == "invoice":
            row = conn.execute(
                "SELECT i.amount, i.status, v.name, i.vendor_id FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
                (ref_id,),
            ).fetchone()
            if not row:
                return {"ok": False, "error": f"No invoice with id {ref_id}"}
            if row["status"] != "open":
                return {"ok": False, "error": f"Invoice {ref_id} is already {row['status']}"}
            amount, payee, vendor_id = row["amount"], row["name"], row["vendor_id"]
        else:
            row = conn.execute("SELECT monthly_rent, landlord, next_due FROM leases WHERE id = ?", (ref_id,)).fetchone()
            if not row:
                return {"ok": False, "error": f"No lease with id {ref_id}"}
            amount, payee, vendor_id = row["monthly_rent"], row["landlord"], None

        dup = conn.execute(
            "SELECT id FROM payment_requests WHERE kind = ? AND ref_id = ? AND status = 'pending'", (kind, ref_id)
        ).fetchone()
        if dup:
            return {"ok": False, "error": f"Request #{dup['id']} for this {kind} is already pending approval"}

        cur = conn.execute(
            """INSERT INTO payment_requests (kind, ref_id, vendor_id, payee, amount, ticket_id, reason,
                                              requested_by, status, created_on)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
            (kind, ref_id, vendor_id, payee, amount, ticket_id, reason, requested_by, today.isoformat()),
        )
        cash = _cash(conn)
    return {
        "ok": True,
        "request_id": cur.lastrowid,
        "status": "pending",
        "kind": kind,
        "payee": payee,
        "amount": amount,
        "cash_balance_now": cash["balance"] if cash else None,
        "note": "Waiting for human approval. No money has moved.",
    }


@mcp.tool(annotations=WRITES)
def create_purchase_order_request(
    vendor_id: int,
    sku: str,
    size: str,
    qty: int,
    requested_by: str,
    reason: str,
    ticket_id: int | None = None,
) -> dict[str, Any]:
    """Draft a restock purchase order and queue its payment for HUMAN approval. Does NOT move money.

    Amount = qty x pricing.unit_cost. Reports whether the vendor is currently blocked by an open
    invoice (it will not ship until that is paid) and the expected arrival using vendors.lead_days.
    """
    if qty <= 0:
        return {"ok": False, "error": "qty must be positive"}
    with _connect() as conn:
        today = _today(conn)
        vendor = conn.execute("SELECT id, name, lead_days FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        if not vendor:
            return {"ok": False, "error": f"No vendor with id {vendor_id}"}
        if not conn.execute("SELECT 1 FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone():
            return {"ok": False, "error": f"No inventory row for {sku} size {size}"}
        price = conn.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if not price:
            return {"ok": False, "error": f"No pricing for SKU {sku}"}
        amount = round(price["unit_cost"] * qty, 2)
        blockers = _vendor_open_invoices(conn, vendor_id)
        cur = conn.execute(
            """INSERT INTO payment_requests (kind, vendor_id, sku, size, qty, payee, amount, ticket_id, reason,
                                              requested_by, status, created_on)
               VALUES ('purchase_order', ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
            (vendor_id, sku, size, qty, vendor["name"], amount, ticket_id, reason, requested_by, today.isoformat()),
        )
        cash = _cash(conn)
    return {
        "ok": True,
        "request_id": cur.lastrowid,
        "status": "pending",
        "vendor": vendor["name"],
        "sku": sku,
        "size": size,
        "qty": qty,
        "unit_cost": price["unit_cost"],
        "amount": amount,
        "vendor_blocked_by_open_invoices": blockers,
        "lead_days": vendor["lead_days"],
        "expected_arrival_if_approved_today": (today + timedelta(days=vendor["lead_days"])).isoformat(),
        "cash_balance_now": cash["balance"] if cash else None,
        "note": "Waiting for human approval. The vendor will not ship while any open invoice remains unpaid.",
    }


@mcp.tool(annotations=WRITES)
def save_customer_draft(ticket_id: int, recipient: str, subject: str, body: str, author: str) -> dict[str, Any]:
    """Save a customer-facing message as a DRAFT on the board. Nothing is emailed or sent."""
    with _connect() as conn:
        today = _today(conn)
        if not conn.execute("SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)).fetchone():
            return {"ok": False, "error": f"No ticket with id {ticket_id}"}
        cur = conn.execute(
            "INSERT INTO drafts (ticket_id, recipient, subject, body, author, status, created_on) VALUES (?, ?, ?, ?, ?, 'draft', ?)",
            (ticket_id, recipient, subject, body, author, today.isoformat()),
        )
    return {"ok": True, "draft_id": cur.lastrowid, "status": "draft", "note": "Saved on the board; not sent."}


@mcp.tool(annotations=WRITES)
def update_ticket_status(
    ticket_id: int,
    status: Literal["open", "in_progress", "waiting_approval", "blocked", "resolved"],
    note: str,
    updated_by: str,
) -> dict[str, Any]:
    """Set a ticket's status and append a dated note (the original request text is kept)."""
    with _connect() as conn:
        today = _today(conn)
        row = conn.execute("SELECT status, notes FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if not row:
            return {"ok": False, "error": f"No ticket with id {ticket_id}"}
        notes = (row["notes"] or "") + f"\n[{today.isoformat()} {updated_by}] {status}: {note}"
        conn.execute("UPDATE tickets SET status = ?, notes = ? WHERE id = ?", (status, notes.strip(), ticket_id))
    return {"ok": True, "ticket_id": ticket_id, "old_status": row["status"], "new_status": status}


# ------------------------------------------------- human-only money tools
# The backend never gives these two tools to an agent; only the human approval
# endpoint (dashboard) calls them.


@mcp.tool(annotations=MONEY)
def approve_payment(request_id: int, approved_by: str) -> dict[str, Any]:
    """HUMAN ONLY. Approve a pending payment request and pay it from checking.

    Refuses if: the request is not pending, the approver is blank or an agent, the vendor of a
    purchase order still has an open invoice, or cash would go negative. On success writes a
    payments row, lowers cash_accounts.balance, and marks the invoice paid / moves the lease's
    next_due forward one month / records the PO's expected arrival.
    """
    approver = (approved_by or "").strip()
    if not approver or approver.lower() in AGENT_NAMES:
        return {"ok": False, "error": "A named human approver is required; agents cannot approve payments."}

    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        today = _today(conn)
        req = conn.execute("SELECT * FROM payment_requests WHERE id = ?", (request_id,)).fetchone()
        if not req:
            return {"ok": False, "error": f"No payment request {request_id}"}
        if req["status"] != "pending":
            return {"ok": False, "error": f"Request {request_id} is already {req['status']}"}

        cash = _cash(conn)
        if cash is None or cash["balance"] < req["amount"]:
            have = cash["balance"] if cash else 0
            return {
                "ok": False,
                "refused": True,
                "error": f"Insufficient cash: balance ${have:,.2f} < ${req['amount']:,.2f}. No negative balances.",
            }

        expected_arrival = None
        if req["kind"] == "invoice":
            inv = conn.execute("SELECT status FROM invoices WHERE id = ?", (req["ref_id"],)).fetchone()
            if not inv or inv["status"] != "open":
                return {"ok": False, "error": f"Invoice {req['ref_id']} is not open"}
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (req["ref_id"],))
        elif req["kind"] == "rent":
            lease = conn.execute("SELECT next_due FROM leases WHERE id = ?", (req["ref_id"],)).fetchone()
            if not lease:
                return {"ok": False, "error": f"Lease {req['ref_id']} not found"}
            new_due = _add_month(date.fromisoformat(lease["next_due"])).isoformat()
            conn.execute("UPDATE leases SET next_due = ? WHERE id = ?", (new_due, req["ref_id"]))
        elif req["kind"] == "purchase_order":
            blockers = _vendor_open_invoices(conn, req["vendor_id"])
            if blockers:
                return {
                    "ok": False,
                    "refused": True,
                    "error": f"Vendor still has open invoice(s) {[b['id'] for b in blockers]}; it will not ship. Pay those first.",
                }
            lead = conn.execute("SELECT lead_days FROM vendors WHERE id = ?", (req["vendor_id"],)).fetchone()
            expected_arrival = (today + timedelta(days=lead["lead_days"])).isoformat()

        new_balance = round(cash["balance"] - req["amount"], 2)
        conn.execute(
            "UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?", (new_balance, today.isoformat(), cash["name"])
        )
        pay = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
            (req["kind"], req["ref_id"] if req["kind"] != "purchase_order" else req["id"], req["amount"], cash["name"], today.isoformat(), approver),
        )
        conn.execute(
            """UPDATE payment_requests SET status = 'paid', decided_by = ?, decided_on = ?, payment_id = ?,
                                           expected_arrival = ? WHERE id = ?""",
            (approver, today.isoformat(), pay.lastrowid, expected_arrival, request_id),
        )
        conn.commit()
        return {
            "ok": True,
            "request_id": request_id,
            "payment_id": pay.lastrowid,
            "kind": req["kind"],
            "payee": req["payee"],
            "amount": req["amount"],
            "approved_by": approver,
            "new_balance": new_balance,
            "expected_arrival": expected_arrival,
        }
    finally:
        if conn.in_transaction:
            conn.rollback()
        conn.close()


@mcp.tool(annotations=WRITES)
def reject_payment(request_id: int, decided_by: str, reason: str) -> dict[str, Any]:
    """HUMAN ONLY. Reject a pending payment request. No money moves."""
    decider = (decided_by or "").strip()
    if not decider or decider.lower() in AGENT_NAMES:
        return {"ok": False, "error": "A named human is required to reject a payment."}
    with _connect() as conn:
        today = _today(conn)
        req = conn.execute("SELECT status FROM payment_requests WHERE id = ?", (request_id,)).fetchone()
        if not req:
            return {"ok": False, "error": f"No payment request {request_id}"}
        if req["status"] != "pending":
            return {"ok": False, "error": f"Request {request_id} is already {req['status']}"}
        conn.execute(
            "UPDATE payment_requests SET status = 'rejected', decided_by = ?, decided_on = ?, decision_note = ? WHERE id = ?",
            (decider, today.isoformat(), reason, request_id),
        )
    return {"ok": True, "request_id": request_id, "status": "rejected"}


if __name__ == "__main__":
    mcp.run(show_banner=False)
