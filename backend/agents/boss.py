"""Boss: reads each ticket, routes it, and makes the final call."""

from backend.agents.base import AgentRole
from backend.models import TicketOutcome

ROLE = AgentRole(
    name="boss",
    title="Boss (Shop Manager)",
    one_liner="Reads tickets, decides who works on them, makes the final call and sets ticket status.",
    prompt_file="boss.md",
    output_type=TicketOutcome,
    mcp_tools=frozenset(
        {
            "get_shop_today",
            "list_open_tickets",
            "get_ticket",
            "get_cash_position",
            "list_payment_requests",
            "list_drafts",
            "update_ticket_status",
        }
    ),
)
