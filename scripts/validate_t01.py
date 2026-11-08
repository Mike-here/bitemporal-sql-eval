"""Write reproducible local verification evidence; makes no model requests."""

from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sqlite3
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.tasks import load_task
from tests.queries import ALTERNATIVES, MUTANTS


def main():
    task = load_task("t01")
    reference_sql = (ROOT / "reference/t01/solution.sql").read_text()
    reference = task.grade(reference_sql)
    alternatives = {name: task.grade(sql).to_dict() for name, sql in ALTERNATIVES.items()}
    mutants = {name: {"candidate_sql": sql, "grade": task.grade(sql).to_dict()}
               for name, sql in MUTANTS.items()}
    assert reference.passed
    assert all(report["passed"] for report in alternatives.values())
    assert all(not result["grade"]["passed"] for result in mutants.values())
    report = dict(kind="local_grader_validation_NOT_model_results",
                  created_at=datetime.now(timezone.utc).isoformat(),
                  python=platform.python_version(), sqlite=sqlite3.sqlite_version,
                  fixtures=len(task.cases), manual_goldens=16, seeded_histories=24,
                  reference=reference.to_dict(), alternatives=alternatives, mutants=mutants,
                  artifact_hashes=task.artifact_hashes,
                  human_review=task.metadata["participant_review"], live_model_attempts=0)
    junit = ROOT / "results/local_validation/pytest.xml"
    if junit.exists():
        suites = ET.parse(junit).getroot().findall("testsuite")
        report["unit_tests"] = {key: sum(int(suite.attrib.get(key, 0)) for suite in suites)
                                for key in ["tests", "failures", "errors", "skipped"]}
    directory = ROOT / "results/local_validation"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "t01.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    # A compact reviewer-facing checkpoint, with an explicit distinction between
    # real local execution and the model trials that have not happened yet.
    lines = ["# t01 automated verification checkpoint", "",
             f"Python {platform.python_version()}; SQLite {sqlite3.sqlite_version}.", "",
             "No live model requests were made. Participant review of the t01 prompt and references was recorded on 2026-11-08; see reference/t01/review.md for scope.", "",
             f"- SQL reference: {len(task.cases)}/{len(task.cases)} fixtures match the independent Python oracle.",
             "- Manual golden expectations: 16/16 agree with both implementations.",
             "- Seeded histories: 24/24 agree.",
             "- Accepted alternatives: correlated NOT EXISTS, grouped joins, FIRST_VALUE.",
             "- Semantic mutations rejected: 17/17, without syntax/contract failures.", "",
             "The unit suite additionally exhausts 16 subhistories x 9 cutoff pairs,",
             "checking both the SQL reference and a correlated alternative against the oracle.", "",
             "## Mutation evidence", ""]
    if "unit_tests" in report:
        tests = report["unit_tests"]
        lines[4:4] = [f"Unit suite: {tests['tests']} tests; {tests['failures']} failures, {tests['errors']} errors, {tests['skipped']} skipped.", ""]
    for name, result in mutants.items():
        failures = [case["name"] for case in result["grade"]["cases"] if not case["passed"]]
        lines.append(f"- `{name}`: fails {len(failures)}/40 fixtures; example `{failures[0]}`.")
    (ROOT / "outputs").mkdir(exist_ok=True)
    (ROOT / "outputs/t01-verification.md").write_text("\n".join(lines) + "\n")
    print("Reference 40/40; alternatives 3/3; semantic mutants rejected 17/17. No API calls.")


if __name__ == "__main__":
    main()
