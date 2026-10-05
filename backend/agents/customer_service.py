"""Customer Service: answers questions and drafts customer messages (never sends)."""

from backend.agents.base import AgentRole
from backend.models import AgentReport

ROLE = AgentRole(
    name="customer_service",
    title="Customer Service",
    one_liner="Answers customer questions and drafts customer messages on the board (never sends them).",
    prompt_file="customer_service.md",
    output_type=AgentReport,
    mcp_tools=frozenset(
        {"get_shop_today", "get_ticket", "check_stock", "get_product_pricing", "list_vendors", "save_customer_draft", "list_drafts"}
    ),
)
