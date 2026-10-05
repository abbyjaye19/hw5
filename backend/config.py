"""Model + Portkey configuration. Every agent uses ONLY gpt-6-luna through Portkey."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

HW_ROOT = Path(__file__).resolve().parent.parent
for folder in [HW_ROOT, *HW_ROOT.parents]:
    if (folder / ".env").exists():
        load_dotenv(folder / ".env", override=False)

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

MODEL_NAME = "gpt-6-luna"  # the only model this assignment allows, for every agent
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

MCP_SERVER = HW_ROOT / "mcp_server" / "server.py"
AUDIT_PATH = Path(os.getenv("CAMPUS_AUDIT_PATH", HW_ROOT / "output" / "audit_trail.json"))

# Token guardrails (per ticket, shared across every delegated agent run).
TICKET_REQUEST_LIMIT = int(os.getenv("TICKET_REQUEST_LIMIT", "30"))
TICKET_TOKEN_LIMIT = int(os.getenv("TICKET_TOKEN_LIMIT", "150000"))
# Output cap per model response (reasoning tokens count toward it, so leave headroom).
MODEL_SETTINGS = ModelSettings(max_tokens=4000)


class ModelGuardError(RuntimeError):
    """Raised when a response comes back from any model other than gpt-6-luna."""


def check_response_model(model_name: str | None) -> None:
    """Portkey reports the deployment that answered (e.g. 'gpt-6-luna-global'); anything else stops the run."""
    if not model_name or not model_name.startswith(MODEL_NAME):
        raise ModelGuardError(
            f"Portkey answered with model {model_name!r}, not {MODEL_NAME}. "
            "Run stopped so no other model is used."
        )


def explain_route_error(exc: Exception) -> ModelGuardError | None:
    """Kept for the run loop: provider errors are reported as-is (no rerouting is expected)."""
    return None


def require_api_key() -> str:
    key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is missing; add it to .env in HW5 or a parent folder.")
    return key


def build_model() -> OpenAIResponsesModel:
    # Responses API: on Portkey, gpt-6-luna only supports function tools on /v1/responses.
    client = AsyncOpenAI(api_key=require_api_key(), base_url=PORTKEY_BASE_URL, timeout=90, max_retries=2)
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))
