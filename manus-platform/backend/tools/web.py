"""
Web fetch tool.

Performs HTTP GET requests and returns response text.
Used by the agent to retrieve web pages and APIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx

from config import TOOL_TIMEOUT


@dataclass
class WebResult:
    """Result of a web fetch operation."""

    success: bool
    content: str = ""
    status_code: int = 0
    error: str = ""
    url: str = ""

    def to_observation(self) -> str:
        """Format as an observation string for the agent context."""
        if not self.success:
            return f"[Web fetch failed: {self.error}]"
        header = f"[Fetched {self.url} — HTTP {self.status_code}, {len(self.content)} chars]"
        return f"{header}\n\n{self.content}"


async def web_fetch(url: str, *, timeout: Optional[int] = None, max_chars: int = 50_000) -> WebResult:
    """
    Fetch a URL and return the response body as text.

    Args:
        url: The HTTP(S) URL to fetch.
        timeout: Override default timeout (seconds).
        max_chars: Truncate response body to this many characters.

    Returns:
        :class:`WebResult` with the page content.
    """
    effective_timeout = timeout or TOOL_TIMEOUT

    try:
        async with httpx.AsyncClient(
            timeout=effective_timeout,
            follow_redirects=True,
            headers={"User-Agent": "ManusAgent/1.0"},
        ) as client:
            response = await client.get(url)
            content = response.text

            if len(content) > max_chars:
                content = content[:max_chars] + f"\n\n[... truncated at {max_chars} chars ...]"

            return WebResult(
                success=response.is_success,
                content=content,
                status_code=response.status_code,
                url=str(response.url),
            )

    except httpx.TimeoutException:
        return WebResult(
            success=False,
            error=f"Request timed out after {effective_timeout}s",
            url=url,
        )
    except httpx.ConnectError as exc:
        return WebResult(success=False, error=f"Connection failed: {exc}", url=url)
    except Exception as exc:
        return WebResult(success=False, error=f"Fetch error: {exc}", url=url)
