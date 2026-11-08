from pathlib import Path
from harness.tasks import ROOT, load_task


def queries():
    directory = ROOT / "reference/t02"
    return (directory/"solution.sql").read_text(), (directory/"alternative.sql").read_text()


def mutants():
    solution, _ = queries()
    return {
        "delete_filtered_before_winner": solution.replace("WHERE effective_at <=", "WHERE operation='UPSERT' AND effective_at <="),
        "delete_ignored": solution.replace("AND operation='UPSERT'", ""),
        "missing_knowledge_cutoff": solution.replace(" AND recorded_at <= :recorded_cutoff", ""),
        "missing_effective_cutoff": solution.replace("effective_at <= :effective_cutoff AND ", ""),
        "recorded_first": solution.replace("effective_at DESC, recorded_at DESC", "recorded_at DESC, effective_at DESC"),
        "zero_dropped": solution.replace("rn=1 AND", "rn=1 AND open_qty>0 AND"),
        "boundary_exclusive": solution.replace("effective_at <=", "effective_at <"),
    }


def test_t02_reference_and_alternative_match_oracle_and_goldens():
    task=load_task("t02")
    assert len(task.cases)==28
    assert sum("expected" in case for case in task.cases)==12
    for query in queries():
        report=task.grade(query)
        assert report.passed, report.to_dict()


def test_t02_mutations_are_rejected_semantically():
    task=load_task("t02")
    for name, sql in mutants().items():
        report=task.grade(sql)
        assert not report.passed, name
        assert any(case.category=="wrong_outcome" for case in report.cases), name
        assert all(case.category in ("pass","wrong_outcome") for case in report.cases), (name,report.to_dict())
