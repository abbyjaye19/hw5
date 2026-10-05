"""AgentRole: the declarative spec for one agent on the team."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# Never given to any agent: only the human approval endpoint may call these MCP tools.
HUMAN_ONLY_TOOLS = frozenset({"approve_payment", "reject_payment"})


@dataclass(frozen=True)
class AgentRole:
    name: str
    title: str
    one_liner: str  # shown to every other agent in the roster so they know whom to delegate to
    prompt_file: str
    output_type: type[BaseModel]
    mcp_tools: frozenset[str]

    def __post_init__(self) -> None:
        leaked = self.mcp_tools & HUMAN_ONLY_TOOLS
        if leaked:
            raise ValueError(f"{self.name} may not hold human-only tools: {sorted(leaked)}")

    def prompt(self) -> str:
        return (PROMPTS_DIR / self.prompt_file).read_text(encoding="utf-8")
