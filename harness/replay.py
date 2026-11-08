"""Regrade saved completed model outputs without calling an API."""

import argparse
import json
from pathlib import Path
import sqlite3

from harness.tasks import load_task


def replay(record):
    task = load_task(record["task"])
    if record.get("artifact_hashes") != task.artifact_hashes:
        raise ValueError("Artifact hashes changed; refusing to label this an exact replay.")
    if record.get("environment", {}).get("sqlite") != sqlite3.sqlite_version:
        raise ValueError("SQLite runtime differs; use the recorded runtime for an exact replay.")
    if record.get("status") != "graded":
        return dict(status=record.get("status"), skipped=True)
    grade = task.grade(record["candidate_sql"]).to_dict()
    # JSON round-trip makes tuples/lists comparable to deserialized transcripts.
    if json.loads(json.dumps(grade)) != record["grade"]:
        raise ValueError("Saved and replayed grades differ.")
    return dict(task=task.task_id, trial=record["trial"], passed=grade["passed"], replay_matches=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", type=Path)
    args = parser.parse_args()
    for line in args.transcript.read_text().splitlines():
        if line.strip():
            print(json.dumps(replay(json.loads(line))))


if __name__ == "__main__":
    main()
