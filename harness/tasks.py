"""Task registry and explicit separation of public input from verifier state."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from graders.sql_outcome import grade_sql
from reference.t01.oracle import solve as solve_t01

ROOT = Path(__file__).resolve().parents[1]
ORACLES = {"t01": solve_t01}


@dataclass
class Task:
    task_id: str
    prompt: str
    schema: str
    metadata: dict
    cases: list
    expected: dict
    artifact_hashes: dict

    @property
    def model_input(self) -> str:
        # Only these two public files enter the request. No fixtures/reference.
        return self.prompt + "\n\n## SQLite schema\n\n```sql\n" + self.schema + "\n```\n"

    def grade(self, response: str):
        return grade_sql(response, self.schema, self.cases, self.expected,
                         self.metadata["output_columns"], self.metadata["output_types"])


def load_task(task_id: str) -> Task:
    if task_id not in ORACLES:
        raise ValueError(f"Task {task_id!r} is not implemented; currently available: {list(ORACLES)}")
    directory = ROOT / "tasks" / task_id
    meta_path = directory / "metadata.json"
    metadata = json.loads(meta_path.read_text())
    prompt_path, schema_path = directory / "prompt.md", directory / "schema.sql"
    cases, files = [], [meta_path, prompt_path, schema_path]
    for relative in metadata["fixture_files"]:
        path = directory / relative
        files.append(path)
        cases.extend(json.loads(path.read_text()))
    expected = {}
    for case in cases:
        expected[case["name"]] = ORACLES[task_id](case["rows"], case["parameters"])
        if "expected" in case:
            manual = sorted(tuple(row) for row in case["expected"])
            if sorted(expected[case["name"]]) != manual:
                raise ValueError(f"Oracle disagrees with manual golden: {case['name']}")
    files += sorted((ROOT / "graders").glob("*.py"))
    files += sorted((ROOT / "harness").glob("*.py"))
    files += sorted((ROOT / "reference" / task_id).glob("*.py"))
    files += [ROOT / "reference" / task_id / "solution.sql", ROOT / "configs/models.json",
              ROOT / "configs/experiment.json", ROOT / "pyproject.toml", ROOT / ".python-version"]
    if (ROOT / "uv.lock").exists():
        files.append(ROOT / "uv.lock")
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    return Task(task_id, prompt_path.read_text(), schema_path.read_text(), metadata, cases, expected, hashes)
