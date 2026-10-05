"""Offline wiring test: no LLM calls. A scripted FunctionModel plays the agents so we can check
MCP tool access, full-mesh delegation, guardrails and the audit trail against a scratch DB copy.

    python -m tests.test_team_wiring
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

HW_ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="cc_test_"))
shutil.copyfile(HW_ROOT / "data" / "campus_customs.db", TMP / "test.db")
os.environ["CAMPUS_CUSTOMS_DB"] = str(TMP / "test.db")
os.environ["CAMPUS_AUDIT_PATH"] = str(TMP / "audit_trail.json")
os.environ.setdefault("PORTKEY_API_KEY", "offline-test")

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart  # noqa: E402
from pydantic_ai.models.function import AgentInfo, FunctionModel  # noqa: E402

from backend.agents.team import CampusTeam  # noqa: E402

SCRIPTS = {
    # agent -> list of (tool_name, args) calls, in order; the last one is the final output tool.
    "boss": [
        ("delegate", {"to_agent": "inventory", "task": "Ticket 103: check CC-HOOD-NAVY M vs qty 20; ask accounting to price a PO."}),
        ("delegate", {"to_agent": "boss", "task": "self-delegation should be refused"}),
        ("update_ticket_status", {"ticket_id": 103, "status": "waiting_approval", "note": "PO pending", "updated_by": "accounting"}),
        ("approve_payment", {"request_id": 1, "approved_by": "boss"}),
        ("final_result", {"ticket_id": 103, "decision": "Fill 8, restock 12 after approval.", "final_status": "waiting_approval", "payment_request_ids": [1]}),
    ],
    "inventory": [
        ("check_stock", {"sku": "CC-HOOD-NAVY", "size": "M", "qty_needed": 20}),
        ("delegate", {"to_agent": "accounting", "task": "Create PO: vendor 1, CC-HOOD-NAVY M qty 12 for ticket 103."}),
        ("final_result", {"agent": "inventory", "summary": "8 on hand, short 12.", "facts": ["qty_on_hand=8 (check_stock)"]}),
    ],
    "accounting": [
        ("create_purchase_order_request", {"vendor_id": 1, "sku": "CC-HOOD-NAVY", "size": "M", "qty": 12, "requested_by": "boss", "reason": "restock", "ticket_id": 103}),
        ("delegate", {"to_agent": "inventory", "task": "cycle back upstream should be refused"}),
        ("final_result", {"agent": "accounting", "summary": "PO request #1 created ($264).", "payment_request_ids": [1], "needs_human_approval": True}),
    ],
}


def scripted(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    agent = next(a for a in SCRIPTS if f"You are the **{a}** agent." in (info.instructions or ""))
    calls_done = sum(1 for m in messages for p in m.parts if isinstance(p, ToolReturnPart))
    name, args = SCRIPTS[agent][calls_done]
    if name == "final_result":
        name = info.output_tools[0].name
    available = {t.name for t in info.function_tools} | {t.name for t in info.output_tools}
    if name not in available:  # e.g. approve_payment is hidden from agents -> model can only "say" it
        return ModelResponse(parts=[TextPart(f"(tried hidden tool {name})"), ToolCallPart(info.output_tools[0].name, SCRIPTS[agent][-1][1])])
    return ModelResponse(parts=[ToolCallPart(name, args)])


async def main() -> None:
    async with CampusTeam(model=FunctionModel(scripted), enforce_model_guard=False) as team:
        tool_names = {n: sorted(t for t in team.agents[n]._function_toolset.tools) for n in team.agents}
        outcome = await team.run_ticket(103)

    print("OUTCOME:", outcome.model_dump_json())
    trail = json.loads((TMP / "audit_trail.json").read_text(encoding="utf-8"))
    events = [(e["agent"], e["event"], e["details"].get("tool") or e["details"].get("to_agent") or "") for e in trail]
    for e in events:
        print("  ", e)
    db = sqlite3.connect(TMP / "test.db")
    req = db.execute("SELECT id, kind, amount, requested_by, status FROM payment_requests").fetchall()
    tick = db.execute("SELECT status, notes FROM tickets WHERE id = 103").fetchone()
    pays = db.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
    print("payment_requests:", req)
    print("ticket 103:", tick)

    assert req == [(1, "purchase_order", 264.0, "accounting", "pending")], "PO stamped with real agent identity"
    assert pays == 0, "no payment without a human"
    assert tick[0] == "waiting_approval" and "boss] waiting_approval" in tick[1], "status stamped as boss"
    blocks = [e for e in trail if e["event"] == "guard_block"]
    assert len(blocks) == 2, f"self + cycle delegation refused, got {len(blocks)}"
    assert any(e["event"] == "delegation" and e["agent"] == "inventory" for e in trail), "specialist->specialist delegation"
    boss_tools = tool_names["boss"]
    assert "delegate" in boss_tools
    assert all(e["run_id"] == trail[0]["run_id"] for e in trail)
    print("\nALL WIRING CHECKS PASSED  (audit entries:", len(trail), ")")


if __name__ == "__main__":
    asyncio.run(main())
