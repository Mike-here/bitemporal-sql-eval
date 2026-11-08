from harness.tasks import ROOT,load_task


def queries():
    directory=ROOT/"reference/t03"
    return (directory/"solution.sql").read_text(),(directory/"alternative.sql").read_text()


def mutants():
    sql,_=queries()
    return {
        "effective_filter_before_restatement":sql.replace("WHERE recorded_at <=", "WHERE effective_at <= :effective_cutoff AND recorded_at <="),
        "all_revisions_are_events":sql.replace("revision_rank=1 AND ",""),
        "future_knowledge_leaks":sql.replace(" WHERE recorded_at <= :recorded_cutoff",""),
        "first_recorded_revision":sql.replace("ORDER BY recorded_at DESC","ORDER BY recorded_at ASC"),
        "latest_arrival_over_business_time":sql.replace("ORDER BY effective_at DESC, amendment_no DESC","ORDER BY recorded_at DESC, amendment_no DESC"),
        "amendment_scope_leak":sql.replace("PARTITION BY order_id, amendment_no","PARTITION BY amendment_no"),
        "wrong_amendment_tie":sql.replace("effective_at DESC, amendment_no DESC","effective_at DESC, amendment_no ASC"),
        "exclusive_knowledge_boundary":sql.replace("recorded_at <=","recorded_at <"),
    }


def test_t03_references_match_oracle_and_explicit_goldens():
    task=load_task("t03")
    assert len(task.cases)==29
    assert sum("expected" in case for case in task.cases)==13
    for sql in queries():
        report=task.grade(sql);assert report.passed,report.to_dict()


def test_t03_mutants_fail_for_semantics():
    task=load_task("t03")
    for name,sql in mutants().items():
        report=task.grade(sql)
        assert not report.passed,name
        assert any(case.category=="wrong_outcome" for case in report.cases),name
        assert all(case.category in ("pass","wrong_outcome") for case in report.cases),(name,report.to_dict())
