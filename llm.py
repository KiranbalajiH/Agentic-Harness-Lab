"""Lightweight, configurable LLM provider adapter.

Provides llm_json(messages) -> dict interface as specified in
Budgeted_Doc_Agent_Implementation_Plan.txt.

Supports OpenAI-compatible endpoints (OpenAI, Ollama, vLLM, Groq, Azure, etc.)
via standard library urllib.request without external dependencies.
"""

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional


class LLMError(Exception):
    """Base exception for LLM provider errors."""


class LLMConfigurationError(LLMError):
    """Raised when required credentials or endpoint configuration are missing."""


class LLMAuthError(LLMError):
    """Raised on authentication or authorization failure (HTTP 401/403)."""


class LLMRateLimitError(LLMError):
    """Raised when rate limit is exceeded (HTTP 429)."""


class LLMTimeoutError(LLMError):
    """Raised when the LLM request times out."""


class LLMMalformedResponseError(LLMError):
    """Raised when the LLM response cannot be parsed as valid JSON."""


def extract_json_from_text(text: str) -> Dict[str, Any]:
    """Extract a JSON object from raw LLM output, handling markdown fences and prose."""
    if not text or not text.strip():
        raise LLMMalformedResponseError("Received empty response from LLM")

    cleaned = text.strip()

    # Check for markdown code fences ```json ... ``` or ``` ... ```
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    # Direct JSON parse attempt
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # Find first '{' and last '}'
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = cleaned[start : end + 1]
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except Exception as e:
            raise LLMMalformedResponseError(
                f"Failed to parse JSON substring from LLM response: {e}"
            ) from e

    raise LLMMalformedResponseError(
        f"No valid JSON object found in LLM response: {cleaned[:200]!r}"
    )


def llm_json(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.0,
    timeout: Optional[float] = None,
) -> Dict[str, Any]:
    """Execute an OpenAI-compatible chat completion request and return parsed JSON dict.

    Environment variables:
        OPENAI_API_KEY: Authentication token.
        OPENAI_BASE_URL or OPENAI_API_BASE: Endpoint base URL (default: https://api.openai.com/v1).
        OPENAI_MODEL or LLM_MODEL: Model name (default: gpt-4o-mini).
        LLM_TIMEOUT: Request timeout in seconds (default: 30).
    """
    api_key = (
        os.environ.get("OPENAI_API_KEY", "").strip()
        or os.environ.get("OPENROUTER_API_KEY", "").strip()
    )
    base_url = (
        os.environ.get("OPENAI_BASE_URL")
        or os.environ.get("OPENAI_API_BASE")
        or os.environ.get("OPENROUTER_BASE_URL")
        or ("https://openrouter.ai/api/v1" if os.environ.get("OPENROUTER_API_KEY") else "https://api.openai.com/v1")
    ).rstrip("/")
    selected_model = (
        model
        or os.environ.get("OPENAI_MODEL")
        or os.environ.get("LLM_MODEL")
        or os.environ.get("OPENROUTER_MODEL")
        or ("google/gemini-2.5-flash-lite" if "openrouter.ai" in base_url.lower() else "gpt-4o-mini")
    )
    request_timeout = timeout or float(os.environ.get("LLM_TIMEOUT", "30.0"))

    # Local endpoints (e.g. Ollama, LMStudio) may not require an API key
    is_local_endpoint = any(
        host in base_url.lower()
        for host in ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
    )
    if not api_key and not is_local_endpoint:
        raise LLMConfigurationError(
            "LLM provider is not configured. Set OPENAI_API_KEY (and optionally "
            "OPENAI_BASE_URL and OPENAI_MODEL) in your environment to enable live LLM reasoning."
        )

    endpoint = f"{base_url}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if "openrouter.ai" in base_url.lower():
        headers["HTTP-Referer"] = os.environ.get("OPENROUTER_HTTP_REFERER", "https://github.com/Agentic-Harness-Lab")
        headers["X-Title"] = os.environ.get("OPENROUTER_TITLE", "Agentic Harness Lab")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": selected_model,
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=request_timeout) as resp:
            status_code = resp.getcode()
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            pass
        if e.code in (401, 403):
            raise LLMAuthError(
                f"LLM authentication failed (HTTP {e.code}): {err_body[:200]}"
            ) from e
        if e.code == 429:
            raise LLMRateLimitError(
                f"LLM rate limit exceeded (HTTP 429): {err_body[:200]}"
            ) from e
        raise LLMError(f"LLM request failed with HTTP {e.code}: {err_body[:200]}") from e
    except urllib.error.URLError as e:
        if "timed out" in str(e).lower():
            raise LLMTimeoutError(f"LLM request timed out after {request_timeout}s") from e
        raise LLMError(f"Failed to reach LLM endpoint: {e}") from e
    except TimeoutError as e:
        raise LLMTimeoutError(f"LLM request timed out after {request_timeout}s") from e
    except Exception as e:
        raise LLMError(f"Unexpected error communicating with LLM: {e}") from e

    try:
        response_data = json.loads(body)
        choices = response_data.get("choices", [])
        if not choices:
            raise LLMMalformedResponseError("LLM response contains no choices")
        content = choices[0].get("message", {}).get("content", "")
    except Exception as e:
        if isinstance(e, LLMError):
            raise
        raise LLMMalformedResponseError(f"Failed to read LLM response payload: {e}") from e

    return extract_json_from_text(content)
