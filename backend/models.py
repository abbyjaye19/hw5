"""Data types shared by the Campus Customs agent team and (later) the FastAPI routes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
TicketStatus = Literal["open", "in_progress", "waiting_approval", "blocked", "resolved"]


# ------------------------------------------------------------ agent outputs


class AgentReport(BaseModel):
    """What a specialist (Inventory, Accounting, Facilities, Customer Service) hands back."""

    agent: AgentName
    summary: str = Field(description="2-4 sentence answer to the task you were given.")
    facts: list[str] = Field(
        default_factory=list,
        description="Facts you relied on, each with its source tool, e.g. 'CC-HOOD-NAVY M qty_on_hand=8 (check_stock)'.",
    )
    actions_taken: list[str] = Field(
        default_factory=list, description="Anything you wrote to the board (payment requests, POs, drafts)."
    )
    recommendations: list[str] = Field(default_factory=list, description="What you advise the Boss to do next.")
    needs_human_approval: bool = Field(False, description="True if any payment or PO is waiting for a human.")
    payment_request_ids: list[int] = Field(default_factory=list)
    draft_ids: list[int] = Field(default_factory=list)


class TicketOutcome(BaseModel):
    """The Boss's final call on one ticket."""

    ticket_id: int
    decision: str = Field(description="The final call in 1-3 sentences.")
    final_status: TicketStatus
    actions_taken: list[str] = Field(default_factory=list)
    payment_request_ids: list[int] = Field(default_factory=list, description="Requests waiting for human approval.")
    draft_ids: list[int] = Field(default_factory=list, description="Customer drafts saved on the board.")
    human_next_steps: list[str] = Field(
        default_factory=list, description="What the human approver needs to do, in order."
    )
    risks_or_open_questions: list[str] = Field(default_factory=list)


# ------------------------------------------------------------ run state


@dataclass
class TeamRun:
    """State shared by every agent working on one ticket."""

    ticket_id: int | None
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    delegations: int = 0
    max_delegations: int = 6
    max_depth: int = 2
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class AgentDeps:
    """Per-agent-run dependencies. `chain` is the delegation path, e.g. ["boss", "inventory"]."""

    agent: AgentName
    team: TeamRun
    depth: int = 0
    chain: list[str] = field(default_factory=list)


class AuditEntry(BaseModel):
    """One line in output/audit_trail.json."""

    ts: str
    run_id: str
    ticket_id: int | None
    agent: str
    depth: int
    chain: list[str]
    event: str  # run_start | model_request | model_response | tool_call | tool_result | delegation | run_end | guard_block | error
    step_no: int | None = None
    details: dict[str, Any] = Field(default_factory=dict)
