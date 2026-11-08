import copy
from graders.sql_outcome import execute_query
from harness.tasks import ROOT,load_task
from reference.t06.oracle import solve


def queries():
    directory=ROOT/"reference/t06"
    return (directory/"solution.sql").read_text(),(directory/"alternative.sql").read_text()


def mutants():
    sql,_=queries()
    return {
        "effective_filter_before_revision_meaning":sql.replace("WHERE recorded_at <=", "WHERE effective_at <= :effective_cutoff AND recorded_at <="),
        "obsolete_revisions_survive":sql.replace("revision_rank=1 AND ",""),
        "delete_removed_before_meaning":sql.replace("FROM order_versions\n", "FROM order_versions WHERE operation='UPSERT'\n"),
        "all_amendments_aggregated":sql.replace("order_rank=1 AND ",""),
        "knowledge_leak":sql.replace(" WHERE recorded_at <= :recorded_cutoff",""),
        "scope_loses_tenant":sql.replace("PARTITION BY tenant_id,book_id,order_id","PARTITION BY book_id,order_id"),
        "scope_loses_book":sql.replace("PARTITION BY tenant_id,book_id,order_id","PARTITION BY tenant_id,order_id"),
        "roster_join_loses_book":sql.replace(" AND b.book_id=e.book_id",""),
        "empty_tenants_dropped":sql.replace("FROM tenants t LEFT JOIN totals s", "FROM tenants t JOIN totals s"),
        "sell_sign_ignored":sql.replace("ELSE -open_qty", "ELSE open_qty"),
        "zero_orders_dropped":sql.replace("WHERE order_rank=1 AND", "WHERE open_qty>0 AND order_rank=1 AND"),
        "revision_outranks_recorded_time":sql.replace("recorded_at DESC,revision DESC,source_seq DESC", "revision DESC,recorded_at DESC,source_seq DESC"),
        "source_sequence_missing":sql.replace(",source_seq DESC",""),
        "duplicate_events_rank_together":sql.replace("SELECT DISTINCT event_id", "SELECT event_id").replace("ROW_NUMBER() OVER", "RANK() OVER"),
    }


def test_t06_references_match_oracle_and_goldens():
    task=load_task("t06")
    assert len(task.cases)==35
    assert sum("expected" in case for case in task.cases)==19
    for sql in queries():
        report=task.grade(sql);assert report.passed,report.to_dict()


def test_t06_mutants_fail_semantically():
    task=load_task("t06")
    for name,sql in mutants().items():
        report=task.grade(sql)
        assert not report.passed,name
        assert any(case.category=="wrong_outcome" for case in report.cases),name
        assert all(case.category in ("pass","wrong_outcome") for case in report.cases),(name,report.to_dict())


def test_t06_duplicate_delivery_and_input_order_invariance():
    task=load_task("t06")
    for original in task.cases:
        case=copy.deepcopy(original);rows=case["tables"]["order_versions"]
        largest=max((row["ingest_id"] for row in rows),default=0)
        rows.extend({**row,"ingest_id":largest+i+1} for i,row in enumerate(list(rows)))
        rows.reverse()
        assert solve(case["tables"],case["parameters"])==task.expected[case["name"]]
        for sql in queries():
            _,actual=execute_query(sql,task.schema,case)
            assert sorted(actual)==task.expected[case["name"]]
