"""OpenAI Responses and native Gemini adapters; no requests happen on import."""

import httpx
import re


class ProviderError(RuntimeError):
    """Sanitized transport/API failure; never includes authorization headers."""


def request_payload(model: dict, prompt: str) -> dict:
    provider = model.get("provider", "openai")
    if provider == "openai":
        payload = {"model": model["model"], "input": prompt,
                   "max_output_tokens": model["max_output_tokens"], "store": False, "tools": []}
        if model.get("reasoning_effort"):
            payload["reasoning"] = {"effort": model["reasoning_effort"]}
        return payload
    if provider == "gemini":
        config = {"maxOutputTokens": model["max_output_tokens"], "candidateCount": 1}
        if model.get("thinking_config"):
            config["thinkingConfig"] = model["thinking_config"]
        return {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": config}
    raise ValueError(f"Unsupported provider {provider!r}")


def generate(model: dict, prompt: str, api_key: str, *, transport=None) -> tuple[dict, dict]:
    payload = request_payload(model, prompt)
    provider = model.get("provider", "openai")
    if provider == "openai":
        endpoint = "https://api.openai.com/v1/responses"
        headers = {"Authorization": f"Bearer {api_key}"}
    else:
        if not re.fullmatch(r"[A-Za-z0-9._-]+", model["model"]):
            raise ValueError("Invalid Gemini model ID.")
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model['model']}:generateContent"
        headers = {"x-goog-api-key": api_key}
    try:
        with httpx.Client(timeout=180.0, transport=transport) as client:
            response = client.post(endpoint, json=payload, headers=headers)
    except httpx.TransportError as error:
        raise ProviderError(f"Transport failure: {type(error).__name__}; no automatic retry.") from None
    if not response.is_success:
        # Save identifier-like error codes, never arbitrary server messages or keys.
        details = []
        try:
            error = response.json().get("error", {})
            if isinstance(error, dict):
                for field in ("code", "type", "status"):
                    value = error.get(field)
                    if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", value):
                        details.append(f"{field}={value}")
        except ValueError:
            pass
        raise ProviderError(f"HTTP {response.status_code}; {'; '.join(details)}; request_id={response.headers.get('x-request-id', 'unavailable')}")
    try:
        data = response.json()
    except ValueError:
        raise ProviderError("Provider returned invalid JSON.") from None
    if not isinstance(data, dict):
        raise ProviderError("Provider returned a non-object response.")
    return payload, data


def output_text(response: dict) -> str:
    if "candidates" in response:
        return "\n".join(part["text"] for candidate in response["candidates"]
                         for part in candidate.get("content", {}).get("parts", [])
                         if "text" in part and not part.get("thought", False))
    parts = []
    for item in response.get("output", []):
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    parts.append(content["text"])
    return "\n".join(parts)


def completion_status(response: dict, provider: str) -> str:
    if provider == "openai":
        return {"completed": "completed", "incomplete": "incomplete"}.get(response.get("status"), "api_error")
    candidates = response.get("candidates", [])
    if len(candidates) == 1 and candidates[0].get("finishReason") == "STOP":
        return "completed"
    if any(candidate.get("finishReason") == "MAX_TOKENS" for candidate in candidates):
        return "incomplete"
    return "provider_blocked_or_error"
