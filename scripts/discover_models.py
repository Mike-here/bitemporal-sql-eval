"""Authenticated model catalog checks. Headers and credential values are never saved."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness.credentials import load_credentials


def main():
    keys = load_credentials(ROOT / ".env")
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "providers": {}}
    with httpx.Client(timeout=40) as client:
        for provider, key_name, endpoint in [
            ("openai", "OPENAI_API_KEY", "https://api.openai.com/v1/models"),
            ("gemini", "GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/models"),
        ]:
            if not keys.get(key_name):
                report["providers"][provider] = {"status": "missing_key"}
                continue
            headers = ({"Authorization": "Bearer " + keys[key_name]} if provider == "openai"
                       else {"x-goog-api-key": keys[key_name]})
            entries, next_token = [], None
            try:
                while True:
                    parameters = ({"pageSize": 1000} if provider == "gemini" else {})
                    if next_token:
                        parameters["pageToken"] = next_token
                    response = client.get(endpoint, headers=headers, params=parameters)
                    if not response.is_success:
                        report["providers"][provider] = {"status": "http_error", "http_status": response.status_code}
                        break
                    data = response.json()
                    if provider == "openai":
                        entries.extend({"id": item["id"]} for item in data.get("data", []))
                    else:
                        entries.extend({key: item[key] for key in ["name", "version", "displayName", "supportedGenerationMethods", "inputTokenLimit", "outputTokenLimit"] if key in item}
                                       for item in data.get("models", []))
                    next_token = data.get("nextPageToken")
                    if not next_token:
                        report["providers"][provider] = {"status": "listed", "endpoint": endpoint, "models": entries,
                                                          "note": "Catalog visibility alone does not prove generation quota. Pilot verifies inference."}
                        break
            except (httpx.TransportError, ValueError) as error:
                report["providers"][provider] = {"status": "transport_or_json_error", "error_type": type(error).__name__}
    output = ROOT / "results/model_discovery/catalog.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    for provider, info in report["providers"].items():
        print(provider, info["status"])
        for item in info.get("models", []):
            identifier = item.get("id", item.get("name"))
            if provider == "gemini" or identifier.startswith(("gpt-", "o3")):
                print(" ", identifier)


if __name__ == "__main__":
    main()
