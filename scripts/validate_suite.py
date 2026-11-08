"""Validate all references/alternatives/mutations offline and summarize real API attempts."""

from datetime import datetime,timezone
import importlib
import json
from pathlib import Path
import sqlite3
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from harness.tasks import load_task
from tests.queries import ALTERNATIVES,MUTANTS


def main():
    report={"kind":"offline_suite_validation_not_model_scores","created_at":datetime.now(timezone.utc).isoformat(),"sqlite":sqlite3.sqlite_version,"tasks":{}}
    lines=["# Six-task implementation checkpoint","", "All results below are offline reference/grader checks, not model performance.", ""]
    junit=ROOT/"results/local_validation/pytest.xml"
    if junit.exists():
        suites=ET.parse(junit).getroot().findall("testsuite")
        report["unit_tests"]={key:sum(int(suite.attrib.get(key,0)) for suite in suites) for key in ["tests","failures","errors","skipped"]}
        counts=report["unit_tests"]
        lines += [f"Unit suite: {counts['tests']} tests; {counts['failures']} failures, {counts['errors']} errors, {counts['skipped']} skipped.", ""]
    for index in range(1,7):
        task_id=f"t{index:02}";task=load_task(task_id)
        reference=(ROOT/"reference"/task_id/"solution.sql").read_text()
        if index==1:alternatives=ALTERNATIVES;mutants=MUTANTS
        else:
            alternatives={"correlated_alternative":(ROOT/"reference"/task_id/"alternative.sql").read_text()}
            mutants=importlib.import_module(f"tests.test_{task_id}").mutants()
        assert task.grade(reference).passed,task_id
        for name,sql in alternatives.items():assert task.grade(sql).passed,(task_id,name)
        mutation_evidence={}
        for name,sql in mutants.items():
            grade=task.grade(sql)
            assert not grade.passed,(task_id,name)
            assert all(case.category in ("pass","wrong_outcome") for case in grade.cases),(task_id,name)
            failures=[case for case in grade.cases if not case.passed]
            first=failures[0]
            mutation_evidence[name]=dict(rejected=True,failed_fixtures=len(failures),example_fixture=first.name,
                                          expected=first.expected,actual=first.actual,candidate_sql=sql)
        review=task.metadata.get("participant_review",{"status":"pending"})
        report["tasks"][task_id]=dict(fixtures=len(task.cases),explicit_goldens=sum("expected" in case for case in task.cases),
                                      reference_passes=True,accepted_alternatives=list(alternatives),
                                      mutations=mutation_evidence,participant_review=review,artifact_hashes=task.artifact_hashes)
        lines.append(f"- {task_id}: {len(task.cases)} fixtures; {report['tasks'][task_id]['explicit_goldens']} explicit goldens; {len(alternatives)} accepted alternatives; {len(mutants)} semantic mutants rejected. Review: {review['status']}.")
    attempts=[]
    for path in sorted((ROOT/"transcripts/diagnostic").glob("*.jsonl")):
        for line in path.read_text().splitlines():
            record=json.loads(line)
            attempts.append({key:record.get(key) for key in ["provider","requested_model","phase","status","error","elapsed_seconds"]})
    report["diagnostic_attempts"]=attempts
    lines += ["", "## Live pilot status", "", f"{len(attempts)} diagnostic attempts are preserved. The replacement keys authenticated to both catalogs. The OpenAI attempts returned credit_balance_exhausted / insufficient_quota; Gemini Pro returned RESOURCE_EXHAUSTED. No SQL was produced.", "", "No successful model output, model pass rate, or capability conclusion is available. These errors are not failed task scores. Formal runs have not started.", "", "## Human review", "", "Michael Acheampong human-verified t01's prompt, SQL reference and Python oracle. t02–t06 are AI-drafted and await participant audit of their contracts, references, fixture expectations and graders."]
    (ROOT/"results/local_validation/suite.json").write_text(json.dumps(report,indent=2)+"\n")
    (ROOT/"outputs").mkdir(exist_ok=True)
    (ROOT/"outputs/suite-verification.md").write_text("\n".join(lines)+"\n")
    print(json.dumps({"fixtures":sum(t["fixtures"] for t in report["tasks"].values()),"explicit_goldens":sum(t["explicit_goldens"] for t in report["tasks"].values()),"mutants_rejected":sum(len(t["mutations"]) for t in report["tasks"].values()),"diagnostic_api_errors":sum(a["status"]=="api_error" for a in attempts)}))


if __name__=="__main__":main()
