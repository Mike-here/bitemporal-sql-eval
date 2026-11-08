import copy
import pytest
from graders.sql_outcome import execute_query
from harness.tasks import ROOT,load_task
from reference.t04.oracle import solve


def queries():
    directory=ROOT/"reference/t04"
    return (directory/"solution.sql").read_text(),(directory/"alternative.sql").read_text()


def mutants():
    sql,_=queries()
    alternative=queries()[1]
    return {
        "missing_revision":sql.replace("revision DESC, ",""),
        "missing_source_sequence":sql.replace(", source_seq DESC",""),
        "counter_before_business_time":sql.replace("effective_at DESC, recorded_at DESC, revision DESC, source_seq DESC","revision DESC, source_seq DESC, effective_at DESC, recorded_at DESC"),
        "source_sequence_before_revision":sql.replace("revision DESC, source_seq DESC","source_seq DESC, revision DESC"),
        "numeric_revision_as_text":sql.replace("revision DESC","CAST(revision AS TEXT) DESC"),
        "duplicate_winners_not_removed":alternative.replace("SELECT DISTINCT a.order_id","SELECT a.order_id"),
        "delete_removed_before_ranking":sql.replace("WHERE effective_at <=","WHERE operation='UPSERT' AND effective_at <="),
        "missing_knowledge_cutoff":sql.replace(" AND recorded_at <= :recorded_cutoff",""),
        "event_label_as_priority":sql.replace("revision DESC, source_seq DESC","event_id DESC"),
    }


def test_t04_references_match_goldens_and_oracle():
    task=load_task("t04")
    assert len(task.cases)==31
    assert sum("expected" in case for case in task.cases)==15
    for sql in queries():
        report=task.grade(sql);assert report.passed,report.to_dict()


def test_t04_mutants_fail_semantically():
    task=load_task("t04")
    for name,sql in mutants().items():
        report=task.grade(sql)
        assert not report.passed,name
        assert any(case.category=="wrong_outcome" for case in report.cases),name
        assert all(case.category in ("pass","wrong_outcome") for case in report.cases),(name,report.to_dict())


def test_t04_adding_retries_and_reversing_input_cannot_change_outcome():
    task=load_task("t04")
    for original in task.cases:
        case=copy.deepcopy(original);rows=case["tables"]["order_versions"]
        largest=max((row["ingest_id"] for row in rows),default=0)
        rows.extend({**row,"ingest_id":largest+i+1} for i,row in enumerate(list(rows)))
        rows.reverse()
        assert solve(case["tables"],case["parameters"])==task.expected[case["name"]]
        for sql in queries():
            _,actual=execute_query(sql,task.schema,case)
            assert sorted(actual)==task.expected[case["name"]]


def test_t04_fixture_validator_rejects_conflicting_duplicate_payload():
    task=load_task("t04");case=copy.deepcopy(task.cases[1])
    case["tables"]["order_versions"][1]["open_qty"]=99
    with pytest.raises(ValueError,match="Conflicting"):
        solve(case["tables"],case["parameters"])
