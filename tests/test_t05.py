from harness.tasks import ROOT,load_task


def queries():
    directory=ROOT/"reference/t05"
    return (directory/"solution.sql").read_text(),(directory/"alternative.sql").read_text()


def mutants():
    sql,_=queries()
    before=sql.replace("FROM order_versions\n  WHERE", "FROM order_versions o\n  WHERE NOT EXISTS (SELECT 1 FROM cancellations c WHERE c.tenant_id=o.tenant_id AND c.book_id=o.book_id AND c.cancellation_key=o.cancellation_key AND c.effective_at <= :effective_cutoff AND c.recorded_at <= :recorded_cutoff) AND")
    return {
        "window_loses_tenant":sql.replace("PARTITION BY tenant_id,book_id,order_id","PARTITION BY book_id,order_id"),
        "window_loses_book":sql.replace("PARTITION BY tenant_id,book_id,order_id","PARTITION BY tenant_id,order_id"),
        "cancel_loses_tenant":sql.replace("c.tenant_id=v.tenant_id AND ",""),
        "cancel_loses_book":sql.replace(" AND c.book_id=v.book_id",""),
        "cancel_ignores_key":sql.replace("AND c.cancellation_key=v.cancellation_key",""),
        "unknown_cancel_leaks":sql.replace(" AND c.recorded_at <= :recorded_cutoff",""),
        "future_cancel_leaks":sql.replace("c.effective_at <= :effective_cutoff AND ",""),
        "cancel_before_state_selection":before,
        "delete_removed_before_state":sql.replace("WHERE effective_at <=", "WHERE operation='UPSERT' AND effective_at <="),
    }


def test_t05_references_match_oracle_and_goldens():
    task=load_task("t05")
    assert len(task.cases)==32
    assert sum("expected" in case for case in task.cases)==16
    for sql in queries():
        report=task.grade(sql);assert report.passed,report.to_dict()


def test_t05_scope_and_state_mutations_fail_semantically():
    task=load_task("t05")
    for name,sql in mutants().items():
        report=task.grade(sql)
        assert not report.passed,name
        assert any(case.category=="wrong_outcome" for case in report.cases),name
        assert all(case.category in ("pass","wrong_outcome") for case in report.cases),(name,report.to_dict())
