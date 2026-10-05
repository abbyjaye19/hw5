"""Accounting: cash, invoices, margins; prepares payments and POs for human approval."""

from backend.agents.base import AgentRole
from backend.models import AgentReport

ROLE = AgentRole(
    name="accounting",
    title="Accounting / Controller",
    one_liner="Watches cash and invoices, checks margins, and prepares payment and purchase-order requests for human approval.",
    prompt_file="accounting.md",
    output_type=AgentReport,
    mcp_tools=frozenset(
        {
            "get_shop_today",
            "get_ticket",
            "get_cash_position",
            "list_open_invoices",
            "get_invoice_status",
            "get_lease_rent_due",
            "get_product_pricing",
            "check_margin",
            "list_vendors",
            "list_payment_requests",
            "request_payment_approval",
            "create_purchase_order_request",
        }
    ),
)
