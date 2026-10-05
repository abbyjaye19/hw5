"""The five Campus Customs agents. Each role file declares its prompt, output type and MCP tool allowlist."""

from backend.agents.accounting import ROLE as ACCOUNTING
from backend.agents.base import AgentRole
from backend.agents.boss import ROLE as BOSS
from backend.agents.customer_service import ROLE as CUSTOMER_SERVICE
from backend.agents.facilities import ROLE as FACILITIES
from backend.agents.inventory import ROLE as INVENTORY

ROLES: dict[str, AgentRole] = {r.name: r for r in (BOSS, INVENTORY, ACCOUNTING, FACILITIES, CUSTOMER_SERVICE)}

__all__ = ["ROLES", "AgentRole"]
