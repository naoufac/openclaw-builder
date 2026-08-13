"""
Configuration for the Manus-like platform backend.

Reads API keys and settings from environment variables / .env file first,
then falls back to the OpenClaw host configuration (``~/.openclaw/openclaw.json``)
if no environment variables are set. All model providers use OpenAI-compatible
chat completions API.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env if present
load_dotenv()


# ── OpenClaw host config fallback ─────────────────────────────────

def _load_openclaw_providers() -> dict[str, dict[str, str]]:
    """
    Read provider keys from the OpenClaw host configuration file.

    Returns a mapping of provider name -> {base_url, api_key, default_model}.
    Keys are never logged or printed.
    """
    openclaw_path = Path.home() / ".openclaw" / "openclaw.json"
    if not openclaw_path.exists():
        return {}

    try:
        with open(openclaw_path, encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        return {}

    providers: dict[str, dict[str, str]] = {}
    models_cfg = cfg.get("models", {})
    providers_cfg = models_cfg.get("providers", {}) if isinstance(models_cfg, dict) else {}

    for name, p in providers_cfg.items():
        if not isinstance(p, dict):
            continue
        api_key = p.get("apiKey", "")
        if not api_key:
            continue
        base_url = p.get("baseUrl", "")
        if not base_url:
            continue
        models = p.get("models", [])
        default_model = models[0].get("id", "default") if isinstance(models, list) and models else "default"
        providers[name] = {
            "base_url": base_url,
            "api_key": api_key,
            "default_model": default_model,
        }

    return providers


_OPENCLAW_PROVIDERS = _load_openclaw_providers()


# ── Model providers ────────────────────────────────────────────────

@dataclass(frozen=True)
class ModelProvider:
    """An OpenAI-compatible model provider."""

    name: str
    base_url: str
    api_key: str
    default_model: str


def _build_providers() -> dict[str, ModelProvider]:
    """Build the provider registry from environment variables and OpenClaw config."""
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

    # Zhipu (zai/glm) — OpenAI-compatible
    zai_cfg = _OPENCLAW_PROVIDERS.get("zai")
    zai_key = os.getenv("ZAI_API_KEY", "")
    zai_url = os.getenv("ZAI_BASE_URL", "")
    if zai_key or zai_cfg:
        providers["zai"] = ModelProvider(
            name="zai",
            base_url=zai_url or (zai_cfg["base_url"] if zai_cfg else "https://api.z.ai/api/coding/paas/v4"),
            api_key=zai_key or (zai_cfg["api_key"] if zai_cfg else ""),
            default_model=os.getenv("ZAI_MODEL", zai_cfg["default_model"] if zai_cfg else "glm-5.2"),
        )
        # Also register as "glm" for backward compatibility
        providers["glm"] = ModelProvider(
            name="glm",
            base_url=providers["zai"].base_url,
            api_key=providers["zai"].api_key,
            default_model=os.getenv("GLM_MODEL", providers["zai"].default_model),
        )

    # Kimi (Moonshot)
    kimi_cfg = _OPENCLAW_PROVIDERS.get("kimi")
    kimi_key = os.getenv("KIMI_API_KEY", os.getenv("MOONSHOT_API_KEY", ""))
    kimi_url = os.getenv("KIMI_BASE_URL", "")
    if kimi_key or kimi_cfg:
        providers["kimi"] = ModelProvider(
            name="kimi",
            base_url=kimi_url or (kimi_cfg["base_url"] if kimi_cfg else "https://api.moonshot.cn/v1"),
            api_key=kimi_key or (kimi_cfg["api_key"] if kimi_cfg else ""),
            default_model=os.getenv("KIMI_MODEL", kimi_cfg["default_model"] if kimi_cfg else "moonshot-v1-32k"),
        )

    # OpenAI
    openai_cfg = _OPENCLAW_PROVIDERS.get("openai")
    openai_key = os.getenv("OPENAI_API_KEY", "")
    openai_url = os.getenv("OPENAI_BASE_URL", "")
    if openai_key or openai_cfg:
        providers["openai"] = ModelProvider(
            name="openai",
            base_url=openai_url or (openai_cfg["base_url"] if openai_cfg else "https://api.openai.com/v1"),
            api_key=openai_key or (openai_cfg["api_key"] if openai_cfg else ""),
            default_model=os.getenv("OPENAI_MODEL", openai_cfg["default_model"] if openai_cfg else "gpt-4o"),
        )

    # Mistral (embeddings + small models)
    mistral_cfg = _OPENCLAW_PROVIDERS.get("mistral")
    mistral_key = os.getenv("MISTRAL_API_KEY", "")
    mistral_url = os.getenv("MISTRAL_BASE_URL", "")
    if mistral_key or mistral_cfg:
        providers["mistral"] = ModelProvider(
            name="mistral",
            base_url=mistral_url or (mistral_cfg["base_url"] if mistral_cfg else "https://api.mistral.ai/v1"),
            api_key=mistral_key or (mistral_cfg["api_key"] if mistral_cfg else ""),
            default_model=os.getenv("MISTRAL_MODEL", mistral_cfg["default_model"] if mistral_cfg else "mistral-small"),
        )

    # xAI (Grok) — OpenAI-compatible; no key in OpenClaw config, env only
    xai_key = os.getenv("XAI_API_KEY", "")
    xai_url = os.getenv("XAI_BASE_URL", "")
    if xai_key:
        providers["xai"] = ModelProvider(
            name="xai",
            base_url=xai_url or "https://api.x.ai/v1",
            api_key=xai_key,
            default_model=os.getenv("XAI_MODEL", "grok-4"),
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
    # Prefer zai, then kimi, then openai, then mistral
    for preferred in ("zai", "kimi", "openai", "mistral"):
        if preferred in PROVIDERS:
            ACTIVE_PROVIDER = PROVIDERS[preferred]
            break
    else:
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

# Docker sandbox image — built from docker/sandbox/Dockerfile
SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "manus-sandbox:latest")
SANDBOX_WORKSPACE = os.getenv("SANDBOX_WORKSPACE", "/workspace")
SANDBOX_TIMEOUT = int(os.getenv("SANDBOX_TIMEOUT", "300"))  # 5 min default
# Whether sandbox is enabled (set to "0" to run tools on host directly)
SANDBOX_ENABLED = os.getenv("SANDBOX_ENABLED", "1") != "0"


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
    - If *model_name* starts with a known provider prefix (e.g. "zai/...",
      "kimi-...", "openai-..."), route to that provider.
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

    # "provider/model" notation takes precedence
    if "/" in lower:
        prefix = lower.split("/", 1)[0]
        if prefix in PROVIDERS:
            return PROVIDERS[prefix]

    # Prefix match on provider name
    for key, provider in PROVIDERS.items():
        if lower.startswith(key):
            return provider

    # Model ID might contain provider name as substring (e.g. "glm-5.2")
    for key, provider in PROVIDERS.items():
        if key in lower:
            return provider

    return ACTIVE_PROVIDER
