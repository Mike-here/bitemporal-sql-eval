"""Run local SQL validation or explicitly selected live model trials.

Examples:
  uv run python -m harness.run --task t01 --sql reference/t01/solution.sql --output work/reference.json
  uv run python -m harness.run --task t01 --model astra --trials 3 --output results/pilot-astra.jsonl
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sqlite3
import subprocess
import time

from harness.providers import ProviderError, completion_status, generate, output_text, request_payload
from harness.credentials import load_credentials
from harness.tasks import ROOT, load_task


def now():
    return datetime.now(timezone.utc).isoformat()


def environment():
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, capture_output=True, text=True)
    if top.returncode != 0 or Path(top.stdout.strip()).resolve() != ROOT:
        return dict(python=platform.python_version(), sqlite=sqlite3.sqlite_version,
                    git_commit=None, git_dirty=None)
    process = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True)
    return dict(python=platform.python_version(), sqlite=sqlite3.sqlite_version,
                git_commit=process.stdout.strip() if process.returncode == 0 else None,
                git_dirty=bool(status.stdout.strip()))


def run_trial(task, model, api_key, trial, *, generate_fn=generate):
    record = dict(kind="model_trial", task=task.task_id, trial=trial, started_at=now(),
                  provider=model.get("provider", "openai"), requested_model=model["model"], environment=environment(),
                  artifact_hashes=task.artifact_hashes,
                  prompt_sha256=hashlib.sha256(task.model_input.encode()).hexdigest(),
                  request=request_payload(model, task.model_input))
    started = time.monotonic()
    try:
        payload, response = generate_fn(model, task.model_input, api_key)
        record.update(request=payload, response=response, returned_model=response.get("model", response.get("modelVersion")),
                      usage=response.get("usage", response.get("usageMetadata")))
        status = completion_status(response, model.get("provider", "openai"))
        if status == "incomplete":
            record.update(status="incomplete", error="Provider reported incomplete output; inspect incomplete_details.")
        elif status != "completed":
            record.update(status=status, error="Provider did not report a completed response.")
        else:
            candidate = output_text(response)
            record.update(status="graded", candidate_sql=candidate, grade=task.grade(candidate).to_dict())
    except ProviderError as error:
        record.update(status="api_error", error=str(error))
    record.update(finished_at=now(), elapsed_seconds=round(time.monotonic() - started, 6))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--sql", type=Path, help="Offline: grade a saved SQL response, no API call.")
    mode.add_argument("--model", help="Live: alias in configs/models.json; incurs provider usage.")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--phase", choices=["diagnostic", "formal"], default="diagnostic")
    parser.add_argument("--output", type=Path, required=True, help="New report file; existing files are never overwritten.")
    args = parser.parse_args()
    if args.trials < 1:
        parser.error("--trials must be positive")
    task = load_task(args.task)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.sql:
        report = dict(kind="local_sql_validation", task=args.task, created_at=now(),
                      environment=environment(), artifact_hashes=task.artifact_hashes,
                      candidate_sql=args.sql.read_text(), grade=task.grade(args.sql.read_text()).to_dict())
        with args.output.open("x") as file:
            json.dump(report, file, indent=2)
            file.write("\n")
        print(f"{args.task}: {sum(c['passed'] for c in report['grade']['cases'])}/{len(task.cases)} fixtures passed")
        return 0 if report["grade"]["passed"] else 1
    models = json.loads((ROOT / "configs/models.json").read_text())["models"]
    model = next((model for model in models if model["alias"] == args.model), None)
    if not model:
        parser.error(f"Unknown model alias {args.model!r}")
    key_name = "GEMINI_API_KEY" if model.get("provider") == "gemini" else "OPENAI_API_KEY"
    api_key = load_credentials(ROOT / ".env").get(key_name)
    if not api_key:
        parser.error(f"Set {key_name} in .env or your environment. No request was made.")
    # Exclusive creation occurs before any paid request. No overwrite/retry/hiding.
    with args.output.open("x") as file:
        for trial in range(1, args.trials + 1):
            record = run_trial(task, model, api_key, trial)
            record["phase"] = args.phase
            file.write(json.dumps(record) + "\n")
            file.flush()
            print(f"{args.task} {model['alias']} trial {trial}: {record['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
