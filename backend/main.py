"""Campus Customs FastAPI backend: the API the React dashboard calls.

Start (from the backend/ folder):
    uvicorn main:app --reload --port 8000

Every shop fact and every database change goes through the MCP server (one
long-lived stdio connection opened at startup); this file never touches SQLite
directly. Agents only *prepare* payments. The approve route below is the only
place cash changes, and only after a human clicks Approve.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

HW_ROOT = Path(__file__).resolve().parent.parent
if str(HW_ROOT) not in sys.path:  # so `uvicorn main:app` from backend/ can import the backend package
    sys.path.insert(0, str(HW_ROOT))

from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from backend import config  # noqa: E402
from backend.agents.team import CampusTeam  # noqa: E402
from backend.models import AgentDeps, TeamRun  # noqa: E402
from backend.reset_db import reset_working_db  # noqa: E402

TEAM: CampusTeam | None = None
RUNS: dict[str, dict[str, Any]] = {}  # run_id -> {ticket_id, status, outcome, error, started_at, finished_at}
RUN_LOCK = asyncio.Lock()  # one ticket run at a time: they share one cash account


@asynccontextmanager
async def lifespan(app: FastAPI):
    global TEAM
    if os.getenv("CAMPUS_SCRIPTED_DEMO"):  # UI testing only: scripted stand-in, no LLM is called
        from tests.scripted_demo import scripted_model

        TEAM = CampusTeam(model=scripted_model(), enforce_model_guard=False)
    else:
        TEAM = CampusTeam()
    async with TEAM:
        yield
    TEAM = None


app = FastAPI(title="Campus Customs Multi-Agent Operations", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def team() -> CampusTeam:
    if TEAM is None:
        raise HTTPException(503, "Agent team is not ready")
    return TEAM


async def mcp(tool: str, **args: Any) -> Any:
    """Call an MCP tool directly (human / dashboard path, not an agent)."""
    return await team().mcp.direct_call_tool(tool, args)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _human_deps(name: str) -> AgentDeps:
    return AgentDeps(agent=name, team=TeamRun(ticket_id=None), depth=0, chain=[name])  # type: ignore[arg-type]


# ------------------------------------------------------------------ models


class ApproveBody(BaseModel):
    approved_by: str = Field(min_length=2, description="Name of the human approving the payment.")


class RejectBody(BaseModel):
    decided_by: str = Field(min_length=2)
    reason: str = Field("", max_length=500)


# ------------------------------------------------------------------ routes


@app.get("/api/health")
async def health() -> dict[str, Any]:
    model = "scripted-demo (no LLM)" if os.getenv("CAMPUS_SCRIPTED_DEMO") else config.MODEL_NAME
    return {"ok": True, "model": model, "db": "campus_customs_new.db", "team_ready": TEAM is not None}


@app.get("/api/tickets")
async def list_tickets() -> dict[str, Any]:
    """The tickets on the board and whether each is open or resolved."""
    tickets = await mcp("list_tickets")
    return {
        "tickets": [
            {**t, "state": "resolved" if t["is_resolved"] else "open"} for t in tickets
        ]
    }


async def _run_ticket(run_id: str, ticket_id: int) -> None:
    run = RUNS[run_id]
    async with RUN_LOCK:
        run["status"] = "running"
        try:
            outcome = await team().run_ticket(ticket_id, run_id=run_id)
            # The run finished: the team has made its call, so the ticket is resolved on the board.
            # Anything still needed from the human (approvals, sending drafts) stays in the outcome.
            ticket = await mcp("get_ticket", ticket_id=ticket_id)
            if ticket.get("status") != "resolved":
                await mcp("update_ticket_status", ticket_id=ticket_id, status="resolved", updated_by="desk",
                          note=f"Run {run_id} finished. Boss decision: {outcome.decision}")
            run.update(status="done", outcome=outcome.model_dump())
        except config.ModelGuardError as exc:
            run.update(status="error", error=str(exc))
        except Exception as exc:
            run.update(status="error", error=f"{type(exc).__name__}: {exc}")
        finally:
            run["finished_at"] = _now()


@app.post("/api/tickets/{ticket_id}/run", status_code=202)
async def run_ticket(ticket_id: int) -> dict[str, Any]:
    """Start the agent team on one ticket. Poll /api/runs/{run_id} and /api/events while it works."""
    found = await mcp("get_ticket", ticket_id=ticket_id)
    if not found.get("found"):
        raise HTTPException(404, f"No ticket {ticket_id}")
    if any(r["ticket_id"] == ticket_id and r["status"] in ("queued", "running") for r in RUNS.values()):
        raise HTTPException(409, f"Ticket {ticket_id} is already being worked")
    run_id = uuid.uuid4().hex[:12]
    RUNS[run_id] = {"run_id": run_id, "ticket_id": ticket_id, "status": "queued", "started_at": _now(),
                    "finished_at": None, "outcome": None, "error": None}
    asyncio.create_task(_run_ticket(run_id, ticket_id))
    return RUNS[run_id]


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> dict[str, Any]:
    """Status of a ticket run: queued | running | done (with the Boss's outcome) | error."""
    if run_id not in RUNS:
        raise HTTPException(404, f"No run {run_id}")
    return RUNS[run_id]


def _summarize(idx: int, e: dict[str, Any]) -> dict[str, Any]:
    """Board-friendly view of one audit entry: what the agent said and which tools it used."""
    d = e.get("details", {})
    out: dict[str, Any] = {
        "id": idx,
        "ts": e["ts"],
        "run_id": e["run_id"],
        "ticket_id": e["ticket_id"],
        "agent": e["agent"],
        "event": e["event"],
        "depth": e.get("depth"),
        "chain": e.get("chain"),
    }
    if e["event"] == "model_response":
        parts = d.get("parts", [])
        out["said"] = " ".join(p.get("content", "") for p in parts if p.get("kind") == "text").strip() or None
        out["tool_calls"] = [{"tool": p.get("tool_name"), "args": p.get("args")} for p in parts if p.get("kind") == "tool-call"]
        out["model"] = d.get("model_name")
        out["usage"] = d.get("usage")
    elif e["event"] in ("tool_call", "tool_result"):
        out["tool"] = d.get("tool")
        out["args" if e["event"] == "tool_call" else "result"] = d.get("args") if e["event"] == "tool_call" else d.get("result", d.get("error"))
    elif e["event"] == "delegation":
        out.update(to_agent=d.get("to_agent"), task=d.get("task"))
    elif e["event"] == "run_start":
        out["task"] = d.get("prompt")
    elif e["event"] == "run_end":
        out["output"] = d.get("output")
        out["ticket_usage_so_far"] = d.get("ticket_usage_so_far")
    elif e["event"] in ("guard_block", "error", "human_approval", "human_rejection", "db_reset"):
        out["details"] = d
    return out


@app.get("/api/events")
async def events(
    since: int = Query(-1, description="Return events with id greater than this (for polling)."),
    ticket_id: int | None = None,
    run_id: str | None = None,
    limit: int = Query(200, le=1000),
) -> dict[str, Any]:
    """Recent agent events from output/audit_trail.json: who said what and which tools they used."""
    path = config.AUDIT_PATH
    trail = json.loads(path.read_text(encoding="utf-8")) if path.exists() and path.stat().st_size else []
    rows = [
        _summarize(i, e)
        for i, e in enumerate(trail)
        if i > since
        and (ticket_id is None or e.get("ticket_id") == ticket_id)
        and (run_id is None or e.get("run_id") == run_id)
    ]
    return {"events": rows[-limit:], "last_id": len(trail) - 1}


@app.get("/api/payments")
async def payment_requests(status: Literal["pending", "paid", "rejected"] | None = None) -> dict[str, Any]:
    """Payment and purchase-order requests the agents prepared (the approval queue)."""
    args = {"status": status} if status else {}
    return {"requests": await mcp("list_payment_requests", **args)}


@app.post("/api/payments/{request_id}/approve")
async def approve_payment(request_id: int, body: ApproveBody) -> dict[str, Any]:
    """HUMAN approval: pays a pending request and updates cash, payments and the invoice/lease.
    Refuses on insufficient cash (no negative balances) or a PO to a vendor with an open invoice."""
    result = await mcp("approve_payment", request_id=request_id, approved_by=body.approved_by)
    await team().audit.record(_human_deps(body.approved_by), "human_approval", request_id=request_id, result=result)
    if not result.get("ok"):
        raise HTTPException(409 if result.get("refused") else 400, result.get("error", "Approval failed"))
    return result


@app.post("/api/payments/{request_id}/reject")
async def reject_payment(request_id: int, body: RejectBody) -> dict[str, Any]:
    """HUMAN rejection of a pending request. No money moves."""
    result = await mcp("reject_payment", request_id=request_id, decided_by=body.decided_by, reason=body.reason)
    await team().audit.record(_human_deps(body.decided_by), "human_rejection", request_id=request_id, result=result)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "Rejection failed"))
    return result


@app.get("/api/cash")
async def cash() -> dict[str, Any]:
    """Current checking balance from cash_accounts (plus what's pending approval)."""
    return await mcp("get_cash_position", account="checking")


@app.get("/api/drafts")
async def drafts(ticket_id: int | None = None) -> dict[str, Any]:
    """Customer message drafts the agents left on the board (never sent)."""
    args = {"ticket_id": ticket_id} if ticket_id is not None else {}
    return {"drafts": await mcp("list_drafts", **args)}


@app.post("/api/reset")
async def reset() -> dict[str, Any]:
    """Reset data/campus_customs_new.db to the original campus_customs.db for a fresh run.
    The audit trail is NOT wiped (it's append-only); a db_reset event is logged instead."""
    if RUN_LOCK.locked():
        raise HTTPException(409, "A ticket run is in progress; wait for it to finish before resetting.")
    reset_working_db()
    RUNS.clear()
    await team().audit.record(_human_deps("human"), "db_reset", note="working DB restored from original")
    return {"ok": True, "cash": await mcp("get_cash_position", account="checking"), "tickets": await mcp("list_tickets")}
