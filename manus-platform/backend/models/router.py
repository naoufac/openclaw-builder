"""
Multi-model router.

All providers expose an OpenAI-compatible ``/chat/completions`` endpoint.
We use ``httpx`` directly — no SDK dependencies — for full control over
headers, timeouts, and streaming.

Routing logic:
    1. The caller passes a ``model`` string (e.g. ``"claude-sonnet-4-20250514"``).
    2. :func:`config.get_provider` resolves it to a :class:`ModelProvider`.
    3. This module calls the provider's chat-completions endpoint.

Streaming: ``stream_chat_completion`` yields content chunks as they arrive.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

import httpx

from config import LLM_MAX_TOKENS, LLM_TIMEOUT, get_provider


# ── Data structures ────────────────────────────────────────────────

@dataclass
class ChatMessage:
    """A single chat message in OpenAI format."""

    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    name: str | None = None
    tool_call_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to OpenAI message dict."""
        msg: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name:
            msg["name"] = self.name
        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id
        return msg


@dataclass
class LLMResponse:
    """Unified response from any model provider."""

    content: str
    model: str
    provider: str
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)
    raw: dict[str, Any] | None = None


# ── Non-streaming ──────────────────────────────────────────────────

async def chat_completion(
    messages: list[ChatMessage],
    *,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: Optional[int] = None,
    stop: list[str] | None = None,
) -> LLMResponse:
    """
    Call the model's chat completion endpoint (non-streaming).

    Args:
        messages: Conversation messages.
        model: Model identifier (routes to the correct provider).
        temperature: Sampling temperature.
        max_tokens: Max output tokens.
        stop: Stop sequences.

    Returns:
        :class:`LLMResponse` with the generated content.

    Raises:
        RuntimeError: If the API call fails.
    """
    provider = get_provider(model)
    effective_model = model or provider.default_model
    url = f"{provider.base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": effective_model,
        "messages": [m.to_dict() for m in messages],
        "temperature": temperature,
        "max_tokens": max_tokens or LLM_MAX_TOKENS,
        "stream": False,
    }
    if stop:
        payload["stop"] = stop

    async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
        response = await client.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            raise RuntimeError(
                f"LLM API error ({response.status_code}) from {provider.name}: "
                f"{response.text[:500]}"
            )

        data = response.json()
        choice = data["choices"][0]
        return LLMResponse(
            content=choice["message"]["content"],
            model=data.get("model", effective_model),
            provider=provider.name,
            finish_reason=choice.get("finish_reason", "stop"),
            usage=data.get("usage", {}),
            raw=data,
        )


# ── Streaming ──────────────────────────────────────────────────────

async def stream_chat_completion(
    messages: list[ChatMessage],
    *,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: Optional[int] = None,
    stop: list[str] | None = None,
) -> AsyncIterator[str]:
    """
    Stream the model's response token-by-token.

    Yields content chunks (strings) as they arrive from the API.

    Args:
        messages: Conversation messages.
        model: Model identifier.
        temperature: Sampling temperature.
        max_tokens: Max output tokens.
        stop: Stop sequences.

    Yields:
        Content delta strings.

    Raises:
        RuntimeError: If the API call fails.
    """
    provider = get_provider(model)
    effective_model = model or provider.default_model
    url = f"{provider.base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": effective_model,
        "messages": [m.to_dict() for m in messages],
        "temperature": temperature,
        "max_tokens": max_tokens or LLM_MAX_TOKENS,
        "stream": True,
    }
    if stop:
        payload["stop"] = stop

    async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
        async with client.stream(
            "POST", url, json=payload, headers=headers
        ) as response:
            if response.status_code != 200:
                body = await response.aread()
                raise RuntimeError(
                    f"LLM streaming error ({response.status_code}) from "
                    f"{provider.name}: {body.decode('utf-8', errors='replace')[:500]}"
                )

            async for line in response.aiter_lines():
                line = line.strip()
                if not line or not line.startswith("data: "):
                    continue

                data_str = line[6:]  # strip "data: " prefix
                if data_str == "[DONE]":
                    break

                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue
