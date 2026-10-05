"""Wires the five Campus Customs agents into a fully connected team.

- Every agent gets the shared MCP server (filtered to its role's allowlist) and a
  `delegate` tool that can reach any other agent (full mesh).
- Every agent-loop step (model request, model response, tool call/result,
  delegation, start/end) is appended to output/audit_trail.json.
- Guardrails: human-only money tools are never exposed, identity fields on write
  tools are stamped by the server-side hook (agents can't impersonate), delegation
  depth/count caps, no delegation cycles, per-ticket token/request limits, and a
  model guard that stops the run if any response isn't from gpt-6-luna.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections.abc import Callable
from typing import Any

from fastmcp.client.transports import StdioTransport
from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import CallToolFunc, MCPToolset
from pydantic_ai.models import Model
from pydantic_ai.usage import RunUsage, UsageLimits

from backend import config
from backend.agents import ROLES, AgentRole
from backend.agents.base import HUMAN_ONLY_TOOLS, PROMPTS_DIR
from backend.audit import AuditTrail
from backend.models import AgentDeps, AgentName, TeamRun, TicketOutcome

# Write tools whose "who did this" argument is stamped by the backend, not trusted from the model.
IDENTITY_ARGS = {
    "request_payment_approval": "requested_by",
    "create_purchase_order_request": "requested_by",
    "save_customer_draft": "author",
    "update_ticket_status": "updated_by",
}


def _roster() -> str:
    return "\n".join(f"- **{r.name}** ({r.title}): {r.one_liner}" for r in ROLES.values())


def _instructions(role: AgentRole) -> str:
    charter = (PROMPTS_DIR / "team_charter.md").read_text(encoding="utf-8").replace("{roster}", _roster())
    return f"{charter}\n\n---\n\n{role.prompt()}\n\nYou are the **{role.name}** agent."


def _describe_parts(parts: Any) -> list[dict[str, Any]]:
    out = []
    for p in parts:
        d: dict[str, Any] = {"kind": getattr(p, "part_kind", type(p).__name__)}
        for attr in ("tool_name", "tool_call_id", "args", "content"):
            if hasattr(p, attr):
                d[attr] = getattr(p, attr)
        out.append(d)
    return out


class CampusTeam:
    """Async context manager that owns the MCP connection and the five agents.

    Usage:
        async with CampusTeam() as team:
            outcome = await team.run_ticket(101)
    """

    def __init__(
        self,
        model: Model | None = None,
        audit: AuditTrail | None = None,
        enforce_model_guard: bool = True,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ):
        self.model = model or config.build_model()
        self.enforce_model_guard = enforce_model_guard
        self.audit = audit or AuditTrail()
        if on_event:
            self.audit.listeners.append(on_event)
        env = {k: os.environ[k] for k in ("CAMPUS_CUSTOMS_DB",) if k in os.environ} or None
        transport = StdioTransport(command=sys.executable, args=[str(config.MCP_SERVER)], cwd=str(config.HW_ROOT), env=env)
        self.mcp = MCPToolset(transport, process_tool_call=self._process_tool_call, max_retries=1)
        self.agents: dict[str, Agent[AgentDeps, Any]] = {name: self._build_agent(role) for name, role in ROLES.items()}

    async def __aenter__(self) -> CampusTeam:
        await self.mcp.__aenter__()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.mcp.__aexit__(*exc)

    # ------------------------------------------------------------ building

    def _build_agent(self, role: AgentRole) -> Agent[AgentDeps, Any]:
        allowed = role.mcp_tools

        agent: Agent[AgentDeps, Any] = Agent(
            self.model,
            name=role.name,
            deps_type=AgentDeps,
            output_type=role.output_type,
            instructions=_instructions(role),
            model_settings=config.MODEL_SETTINGS,
            toolsets=[self.mcp.filtered(lambda ctx, td: td.name in allowed and td.name not in HUMAN_ONLY_TOOLS)],
            retries=2,
        )

        @agent.tool
        async def delegate(ctx: RunContext[AgentDeps], to_agent: AgentName, task: str) -> str:
            """Hand a specific, self-contained task to another agent on the team and get their report back.

            Args:
                to_agent: One of boss, inventory, accounting, facilities, customer_service (not yourself).
                task: Everything they need: ticket id, SKU/size/qty or invoice/lease ids, and exactly what to report.
            """
            return await self._delegate(ctx, to_agent, task)

        return agent

    # ------------------------------------------------------------ MCP hook

    async def _process_tool_call(
        self, ctx: RunContext[Any], call_tool: CallToolFunc, name: str, args: dict[str, Any]
    ) -> Any:
        deps: AgentDeps = ctx.deps
        if name in HUMAN_ONLY_TOOLS:  # second line of defence; these are filtered out already
            await self.audit.record(deps, "guard_block", tool=name, args=args, reason="human-only tool")
            return {"ok": False, "error": f"{name} is human-only. Agents may only request payments."}
        if name in IDENTITY_ARGS:
            args = {**args, IDENTITY_ARGS[name]: deps.agent}
        await self.audit.record(deps, "tool_call", tool=name, args=args, tool_call_id=ctx.tool_call_id)
        t0 = time.perf_counter()
        try:
            result = await call_tool(name, args)
        except Exception as exc:
            await self.audit.record(deps, "tool_result", tool=name, error=str(exc), tool_call_id=ctx.tool_call_id)
            raise
        await self.audit.record(
            deps,
            "tool_result",
            tool=name,
            result=result,
            elapsed_ms=round(1000 * (time.perf_counter() - t0)),
            tool_call_id=ctx.tool_call_id,
        )
        return result

    # ------------------------------------------------------------ delegation

    async def _delegate(self, ctx: RunContext[AgentDeps], to_agent: str, task: str) -> str:
        deps = ctx.deps
        team = deps.team
        refusal = None
        if to_agent not in ROLES:
            refusal = f"Unknown agent {to_agent!r}."
        elif to_agent == deps.agent:
            refusal = "You can't delegate to yourself; do the task with your own tools."
        elif to_agent in deps.chain:
            refusal = f"{to_agent} is already working upstream of you ({' -> '.join(deps.chain)}); answer with what you have."
        elif deps.depth >= team.max_depth:
            refusal = f"Delegation depth limit ({team.max_depth}) reached; answer with what you have."
        elif team.delegations >= team.max_delegations:
            refusal = f"Ticket delegation budget ({team.max_delegations}) used up; answer with what you have."
        if refusal:
            await self.audit.record(deps, "guard_block", to_agent=to_agent, task=task, reason=refusal)
            return f"DELEGATION REFUSED: {refusal}"

        team.delegations += 1
        await self.audit.record(deps, "delegation", to_agent=to_agent, task=task, delegation_no=team.delegations)
        child = AgentDeps(agent=to_agent, team=team, depth=deps.depth + 1, chain=[*deps.chain, to_agent])  # type: ignore[arg-type]
        try:
            report = await self.run_agent(to_agent, task, child, usage=ctx.usage)
        except config.ModelGuardError:
            raise
        except Exception as exc:  # report the failure upstream instead of crashing the whole ticket
            await self.audit.record(child, "error", error=str(exc))
            return f"{to_agent} failed: {exc}"
        return json.dumps(report.model_dump() if hasattr(report, "model_dump") else report, ensure_ascii=False)

    # ------------------------------------------------------------ agent loop

    async def run_agent(self, name: str, prompt: str, deps: AgentDeps, usage: RunUsage | None = None) -> Any:
        """Run one agent node-by-node, auditing every step of its loop."""
        agent = self.agents[name]
        limits = UsageLimits(request_limit=config.TICKET_REQUEST_LIMIT, total_tokens_limit=config.TICKET_TOKEN_LIMIT)
        await self.audit.record(deps, "run_start", prompt=prompt, model=config.MODEL_NAME)
        step = 0
        t0 = time.perf_counter()
        async with agent.iter(prompt, deps=deps, usage=usage, usage_limits=limits) as run:
            async for node in run:
                step += 1
                if Agent.is_model_request_node(node):
                    await self.audit.record(deps, "model_request", step, parts=_describe_parts(node.request.parts))
                elif Agent.is_call_tools_node(node):
                    resp = node.model_response
                    await self.audit.record(
                        deps,
                        "model_response",
                        step,
                        model_name=resp.model_name,
                        parts=_describe_parts(resp.parts),
                        usage={"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens},
                    )
                    if self.enforce_model_guard:
                        try:
                            config.check_response_model(resp.model_name)
                        except config.ModelGuardError as exc:
                            await self.audit.record(deps, "guard_block", step, reason=str(exc))
                            raise
            result = run.result
        output = result.output
        total = run.usage() if callable(run.usage) else run.usage
        await self.audit.record(
            deps,
            "run_end",
            step,
            output=output.model_dump() if hasattr(output, "model_dump") else output,
            elapsed_s=round(time.perf_counter() - t0, 2),
            ticket_usage_so_far={"requests": total.requests, "input_tokens": total.input_tokens, "output_tokens": total.output_tokens},
        )
        return output

    async def run_ticket(self, ticket_id: int, max_delegations: int = 6, run_id: str | None = None) -> TicketOutcome:
        """Boss works one ticket end to end (specialists join via delegation)."""
        team = TeamRun(ticket_id=ticket_id, max_delegations=max_delegations)
        if run_id:
            team.run_id = run_id
        deps = AgentDeps(agent="boss", team=team, depth=0, chain=["boss"])
        ticket = await self.mcp.direct_call_tool("get_ticket", {"ticket_id": ticket_id})
        today = await self.mcp.direct_call_tool("get_shop_today", {})
        prompt = (
            f"Shop today: {json.dumps(today)}\n"
            f"Work this ticket to a final decision:\n{json.dumps(ticket, indent=2)}"
        )
        try:
            return await self.run_agent("boss", prompt, deps)
        except Exception as exc:
            friendly = config.explain_route_error(exc) if self.enforce_model_guard else None
            if friendly:
                await self.audit.record(deps, "guard_block", reason=str(friendly), raw_error=str(exc))
                raise friendly from exc
            await self.audit.record(deps, "error", error=f"{type(exc).__name__}: {exc}")
            raise
