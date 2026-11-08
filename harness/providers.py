"""Minimal Responses API adapter. Importing this module never makes a request."""

import httpx


class ProviderError(RuntimeError):
    """Sanitized transport/API failure; never includes authorization headers."""


def request_payload(model: dict, prompt: str) -> dict:
    return {"model": model["model"], "input": prompt,
            "reasoning": {"effort": model["reasoning_effort"]},
            "max_output_tokens": model["max_output_tokens"], "store": False, "tools": []}


def generate(model: dict, prompt: str, api_key: str, *, transport=None) -> tuple[dict, dict]:
    payload = request_payload(model, prompt)
    try:
        with httpx.Client(timeout=180.0, transport=transport) as client:
            response = client.post("https://api.openai.com/v1/responses", json=payload,
                                   headers={"Authorization": f"Bearer {api_key}"})
    except httpx.TransportError as error:
        raise ProviderError(f"Transport failure: {type(error).__name__}; no automatic retry.") from None
    if not response.is_success:
        # Do not serialize server error bodies that might echo request data.
        raise ProviderError(f"HTTP {response.status_code}; request_id={response.headers.get('x-request-id', 'unavailable')}")
    try:
        data = response.json()
    except ValueError:
        raise ProviderError("Provider returned invalid JSON.") from None
    if not isinstance(data, dict):
        raise ProviderError("Provider returned a non-object response.")
    return payload, data


def output_text(response: dict) -> str:
    parts = []
    for item in response.get("output", []):
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    parts.append(content["text"])
    return "\n".join(parts)
