"""Inventory: stock by SKU/size, shortfalls, and which vendor can restock."""

from backend.agents.base import AgentRole
from backend.models import AgentReport

ROLE = AgentRole(
    name="inventory",
    title="Inventory Lead",
    one_liner="Checks stock by SKU and size, finds shortfalls, and identifies which vendor can restock and when.",
    prompt_file="inventory.md",
    output_type=AgentReport,
    mcp_tools=frozenset(
        {"get_shop_today", "get_ticket", "check_stock", "get_product_pricing", "list_vendors", "get_invoice_status"}
    ),
)
