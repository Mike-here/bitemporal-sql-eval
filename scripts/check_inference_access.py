"""One minimal setup probe, explicitly separate from benchmark trials."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness.credentials import load_credentials
from harness.providers import generate, ProviderError


if __name__ == "__main__":
    selected = dict(provider="openai", model="gpt-6-luna", max_output_tokens=32, reasoning_effort="low")
    record = dict(kind="setup_probe_not_benchmark_trial", timestamp=datetime.now(timezone.utc).isoformat(), model=selected["model"])
    try:
        _, response = generate(selected, "Reply OK.", load_credentials(ROOT / ".env")["OPENAI_API_KEY"])
        record.update(status=response.get("status"), usage=response.get("usage"))
    except ProviderError as error:
        record.update(status="api_error", error=str(error))
    path = ROOT / "results/model_discovery/inference-probe.json"
    path.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record))
