"""
Configuration for the Manus-like platform backend.

Reads API keys and settings from environment variables / .env file.
All model providers use OpenAI-compatible chat completions API.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

# Load .env if present
load_dotenv()


# ── Model providers ────────────────────────────────────────────────

@dataclass(frozen=True)
class ModelProvider:
    """An OpenAI-compatible model provider."""

    name: str
    base_url: str
    api_key: str
    default_model: str


def _build_providers() -> dict[str, ModelProvider]:
    """Build the provider registry from environment variables."""
    providers: dict[str, ModelProvider] = {}

    # Claude (Anthropic — via OpenAI-compatible endpoint if available)
    claude_key = os.getenv("ANTHROPIC_API_KEY", "")
    if claude_key:
        providers["claude"] = ModelProvider(
            name="claude",
            base_url=os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1"),
            api_key=claude_key,
            default_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        )

    # GLM (Zhipu)
    glm_key = os.getenv("GLM_API_KEY", os.getenv("ZHIPU_API_KEY", ""))
    if glm_key:
        providers["glm"] = ModelProvider(
            name="glm",
            base_url=os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
            api_key=glm_key,
            default_model=os.getenv("GLM_MODEL", "glm-4-plus"),
        )

    # Kimi (Moonshot)
    kimi_key = os.getenv("KIMI_API_KEY", os.getenv("MOONSHOT_API_KEY", ""))
    if kimi_key:
        providers["kimi"] = ModelProvider(
            name="kimi",
            base_url=os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1"),
            api_key=kimi_key,
            default_model=os.getenv("KIMI_MODEL", "moonshot-v1-32k"),
        )

    # OpenAI (fallback / universal)
    openai_key = os.getenv("OPENAI_API_KEY", "")
    if openai_key:
        providers["openai"] = ModelProvider(
            name="openai",
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_key=openai_key,
            default_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        )

    # Generic OpenAI-compatible (custom endpoint)
    generic_key = os.getenv("LLM_API_KEY", "")
    generic_url = os.getenv("LLM_BASE_URL", "")
    if generic_key and generic_url:
        providers["custom"] = ModelProvider(
            name="custom",
            base_url=generic_url,
            api_key=generic_key,
            default_model=os.getenv("LLM_MODEL", "default"),
        )

    return providers


PROVIDERS: dict[str, ModelProvider] = _build_providers()

# Default model to use when routing doesn't specify
DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "")
if DEFAULT_PROVIDER and DEFAULT_PROVIDER in PROVIDERS:
    ACTIVE_PROVIDER = PROVIDERS[DEFAULT_PROVIDER]
elif PROVIDERS:
    # Pick first available
    ACTIVE_PROVIDER = next(iter(PROVIDERS.values()))
else:
    # Null provider for testing — will raise on actual API call
    ACTIVE_PROVIDER = ModelProvider(
        name="none",
        base_url="http://localhost:9999/v1",
        api_key="missing",
        default_model="none",
    )


# ── Sandbox ────────────────────────────────────────────────────────

SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "ubuntu:24.04")
SANDBOX_WORKSPACE = "/workspace"
SANDBOX_TIMEOUT = int(os.getenv("SANDBOX_TIMEOUT", "300"))  # 5 min default


# ── Server ─────────────────────────────────────────────────────────

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# WebSocket settings
WS_PING_INTERVAL = int(os.getenv("WS_PING_INTERVAL", "20"))
WS_PING_TIMEOUT = int(os.getenv("WS_PING_TIMEOUT", "60"))
WS_MAX_MESSAGE_SIZE = int(os.getenv("WS_MAX_MESSAGE_SIZE", str(2 * 1024 * 1024)))  # 2 MiB

# Session settings
SESSION_WORKSPACE_ROOT = os.getenv(
    "SESSION_WORKSPACE_ROOT",
    os.path.join(os.path.dirname(__file__), "sessions"),
)

# Agent loop settings
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "50"))
TOOL_TIMEOUT = int(os.getenv("TOOL_TIMEOUT", "120"))  # seconds
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "120"))  # seconds
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))


def get_provider(model_name: str | None = None) -> ModelProvider:
    """
    Resolve a model name to a provider.

    Routing logic:
    - If *model_name* starts with a known provider prefix (e.g. "claude-...",
      "glm-...", "kimi-..."), route to that provider.
    - Otherwise return the active default provider.

    Args:
        model_name: Model identifier or None for default.

    Returns:
        The resolved :class:`ModelProvider`.

    Raises:
        KeyError: If the requested provider is not configured.
    """
    if not model_name:
        return ACTIVE_PROVIDER

    lower = model_name.lower()
    for key, provider in PROVIDERS.items():
        if lower.startswith(key):
            return provider

    # If "provider/model" notation is used
    if "/" in model_name:
        prefix = model_name.split("/", 1)[0]
        if prefix in PROVIDERS:
            return PROVIDERS[prefix]

    return ACTIVE_PROVIDER
