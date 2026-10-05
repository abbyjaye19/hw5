"""Scripted stand-in for the LLM, for UI testing only (no model is called).

Enable with CAMPUS_SCRIPTED_DEMO=1 when starting the backend, ideally with
CAMPUS_CUSTOMS_DB / CAMPUS_AUDIT_PATH pointed at scratch copies. The dashboard
header then shows "scripted-demo (no LLM)". Real runs never use this.
"""

from __future__ import annotations

import asyncio
import re

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

MODEL_LABEL = "scripted-demo (no LLM)"

FINAL = "__final__"

SCRIPTS: dict[int, dict[str, list[tuple[str, dict, str]]]] = {
    101: {
        "boss": [
            ("delegate", {"to_agent": "inventory", "task": "Ticket 101: check CC-TEE-WHITE size S against qty 1; who can restock, lead time, blocked?"}, "Customer order. Inventory first: can we fill size S today?"),
            ("delegate", {"to_agent": "accounting", "task": "Ticket 101: invoice 501 is overdue and blocks Bulldog Print Co. Check cash and queue it for human approval."}, "Out of stock and the vendor is blocked by invoice 501. Accounting next."),
            ("delegate", {"to_agent": "customer_service", "task": "Ticket 101: draft a reply to Tauhid Zaman. Size S is out of stock; a reprint is being arranged once a vendor bill is settled; no firm date yet."}, "Payment is queued. Customer Service drafts the reply last."),
            ("update_ticket_status", {"ticket_id": 101, "status": "resolved", "note": "Invoice 501 request awaiting human approval; draft to Tauhid on the board.", "updated_by": "boss"}, ""),
            (FINAL, {"ticket_id": 101, "decision": "Pay overdue invoice 501 ($840) so Bulldog Print Co releases the rush reprint; tell Tauhid honestly that size S is coming but has no firm date yet.", "final_status": "resolved", "actions_taken": ["Inventory confirmed 0 on hand", "Accounting queued invoice 501", "Customer Service drafted reply"], "payment_request_ids": [1], "draft_ids": [1], "human_next_steps": ["Approve cheque #1: invoice 501, $840 to Bulldog Print Co", "Review and send draft #1 to Tauhid"]}, ""),
        ],
        "inventory": [
            ("check_stock", {"sku": "CC-TEE-WHITE", "size": "S", "qty_needed": 1}, ""),
            ("list_vendors", {}, "Size S is at 0. Checking which vendor can reprint."),
            (FINAL, {"agent": "inventory", "summary": "CC-TEE-WHITE size S: 0 on hand, short 1. Bulldog Print Co (5-day lead) is blocked by open invoice 501.", "facts": ["qty_on_hand=0 (check_stock)", "Bulldog lead_days=5, blocked by invoice 501 (list_vendors)"], "recommendations": ["Pay invoice 501, then expect the reprint by about 2026-09-05."]}, ""),
        ],
        "accounting": [
            ("get_invoice_status", {"invoice_id": 501}, ""),
            ("get_cash_position", {}, "Invoice 501: $840, 3 days overdue. Checking cash."),
            ("request_payment_approval", {"kind": "invoice", "ref_id": 501, "requested_by": "x", "reason": "Overdue 3 days; blocks Bulldog from shipping the size S reprint for ticket 101.", "ticket_id": 101}, "$3,400 covers it. Queuing for human approval."),
            (FINAL, {"agent": "accounting", "summary": "Queued invoice 501 ($840) for approval as request #1. Cash $3,400 covers it.", "facts": ["amount=840, days_overdue=3 (get_invoice_status)", "balance=3400 (get_cash_position)"], "actions_taken": ["Payment request #1"], "needs_human_approval": True, "payment_request_ids": [1]}, ""),
        ],
        "customer_service": [
            ("save_customer_draft", {"ticket_id": 101, "recipient": "Tauhid Zaman", "subject": "Your Classic Bulldog Tee (size S)", "body": "Hi Tauhid,\n\nThanks for your order! Our Classic Bulldog Tee in size S is out of stock right now. We're arranging a reprint with our supplier and will confirm a pickup date as soon as it's scheduled.\n\nThank you for your patience,\nCampus Customs", "author": "x"}, ""),
            (FINAL, {"agent": "customer_service", "summary": "Saved draft #1 to Tauhid: size S out of stock, reprint being arranged, no date promised.", "actions_taken": ["Saved draft #1"], "draft_ids": [1]}, ""),
        ],
    },
    102: {
        "boss": [
            ("delegate", {"to_agent": "facilities", "task": "Ticket 102: verify the rent notice against lease 1 and get rent queued for approval."}, "Rent notice. Facilities owns the space."),
            ("update_ticket_status", {"ticket_id": 102, "status": "resolved", "note": "Rent request awaiting human approval.", "updated_by": "boss"}, ""),
            (FINAL, {"ticket_id": 102, "decision": "Rent of $2,400 for the Chapel Street shop is due 2026-09-02. Queued for approval.", "final_status": "resolved", "payment_request_ids": [2], "human_next_steps": ["Approve cheque #2: rent, $2,400 to Elm City Properties, before 09-02"]}, ""),
        ],
        "facilities": [
            ("get_lease_rent_due", {"lease_id": 1}, ""),
            ("delegate", {"to_agent": "accounting", "task": "Ticket 102: request approval to pay rent for lease 1, due 2026-09-02."}, "Lease confirms $2,400 due 09-02, two days out. Handing the payment to Accounting."),
            (FINAL, {"agent": "facilities", "summary": "Lease 1: $2,400 due 2026-09-02 (2 days). Accounting queued the rent.", "facts": ["monthly_rent=2400, days_until_due=2 (get_lease_rent_due)"]}, ""),
        ],
        "accounting": [
            ("get_cash_position", {}, ""),
            ("request_payment_approval", {"kind": "rent", "ref_id": 1, "requested_by": "x", "reason": "Rent for Chapel Street shop due 2026-09-02.", "ticket_id": 102}, "Cash covers it with pending items. Queuing rent."),
            (FINAL, {"agent": "accounting", "summary": "Queued rent ($2,400) as a pending request.", "needs_human_approval": True}, ""),
        ],
    },
}


def _ticket(messages: list[ModelMessage]) -> int | None:
    text = " ".join(str(getattr(p, "content", "")) for m in messages for p in m.parts)
    hit = re.search(r"Ticket (\d{3})", text) or re.search(r'"id":\s*(\d{3})', text)
    return int(hit.group(1)) if hit else None


async def _respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    await asyncio.sleep(0.9)  # so the dashboard visibly streams
    agent = re.search(r"You are the \*\*(\w+)\*\* agent", info.instructions or "")
    name = agent.group(1) if agent else "boss"
    ticket = _ticket(messages)
    script = SCRIPTS.get(ticket or 0, {}).get(name)
    output_tool = info.output_tools[0].name
    if not script:
        return ModelResponse(parts=[ToolCallPart(output_tool, {"agent": name, "summary": "No demo script for this ticket.", "ticket_id": ticket or 0, "decision": "Demo has no script for this ticket.", "final_status": "blocked"})])
    step = sum(1 for m in messages for p in m.parts if isinstance(p, ToolReturnPart))
    tool, args, said = script[min(step, len(script) - 1)]
    parts = [TextPart(said)] if said else []
    parts.append(ToolCallPart(output_tool if tool == FINAL else tool, args))
    return ModelResponse(parts=parts, model_name=MODEL_LABEL)


def scripted_model() -> FunctionModel:
    return FunctionModel(_respond, model_name=MODEL_LABEL)
