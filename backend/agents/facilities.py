"""Facilities: the shop's real-estate side (lease, rent, landlord)."""

from backend.agents.base import AgentRole
from backend.models import AgentReport

ROLE = AgentRole(
    name="facilities",
    title="Facilities / Real Estate",
    one_liner="Owns the shop space: lease terms, rent due dates and the landlord relationship.",
    prompt_file="facilities.md",
    output_type=AgentReport,
    mcp_tools=frozenset({"get_shop_today", "get_ticket", "get_lease_rent_due", "get_cash_position", "list_payment_requests"}),
)
