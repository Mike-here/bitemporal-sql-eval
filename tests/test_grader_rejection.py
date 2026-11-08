import pytest
import json

from graders.normalize import OutputContractError, extract_sql, normalize_rows
from graders.sql_outcome import QueryExecutionError, execute_query, grade_sql
from tests.queries import MUTANTS


@pytest.mark.parametrize("name", MUTANTS)
def test_mutants_fail_for_semantics_not_parser_errors(task, name):
    report = task.grade(MUTANTS[name])
    assert not report.passed, name
    assert report.primary_score == 0
    assert report.fixture_pass_fraction < 1
    assert any(case.category == "wrong_outcome" for case in report.cases), report.to_dict()
    assert all(case.category in ("pass", "wrong_outcome") for case in report.cases), report.to_dict()


@pytest.mark.parametrize("response", ["", "```sql\nSELECT 1;\n```\nExplanation", "```sql\nSELECT 1;", "x" * 65_537])
def test_malformed_output_is_a_clean_contract_failure(task, response):
    report = task.grade(response)
    assert not report.passed
    assert {case.category for case in report.cases} == {"output_contract"}


def test_sql_syntax_error_is_clean_failure(task):
    report = task.grade("SELECT broken FROM;")
    assert not report.passed
    assert {case.category for case in report.cases} == {"query_error"}


@pytest.mark.parametrize("expression", ["CAST(symbol AS BLOB) AS symbol", "1e999 AS open_qty"])
def test_invalid_sqlite_result_types_still_have_serializable_failure_logs(task, reference_sql, expression):
    if "symbol" in expression:
        query=reference_sql.replace("SELECT order_id, symbol, side",f"SELECT order_id, {expression}, side")
    else:
        query=reference_sql.replace("side, open_qty, limit_price_cents\nFROM ranked",f"side, {expression}, limit_price_cents\nFROM ranked")
    report=task.grade(query)
    assert not report.passed
    assert any(case.category=="output_contract" for case in report.cases)
    json.dumps(report.to_dict(),allow_nan=False)


@pytest.mark.parametrize("values", [[None], ["10"], [10.5], [float("nan")], [float("inf")], [True]])
def test_invalid_integer_outputs_are_rejected(values):
    with pytest.raises(OutputContractError):
        normalize_rows(["qty"], [values], ["qty"], ["integer"])


def test_large_integer_comparison_never_loses_precision():
    expected = normalize_rows(["qty"], [(9_007_199_254_740_993,)], ["qty"], ["integer"])
    wrong = normalize_rows(["qty"], [(float(9_007_199_254_740_993),)], ["qty"], ["integer"])
    assert expected != wrong


def test_identifiers_are_not_trimmed_or_casefolded():
    expected = normalize_rows(["id"], [("A",)], ["id"], ["text"])
    for value in ["a", " A", "A "]:
        assert normalize_rows(["id"], [(value,)], ["id"], ["text"]) != expected


def test_missing_extra_or_reordered_columns_fail(task, reference_sql):
    for projection in ["order_id, symbol, side, open_qty", "symbol, order_id, side, open_qty, limit_price_cents", "order_id, symbol, side, open_qty, limit_price_cents, version_id"]:
        sql = reference_sql.replace("SELECT order_id, symbol, side, open_qty, limit_price_cents\nFROM ranked", f"SELECT {projection}\nFROM ranked")
        report = task.grade(sql)
        assert not report.passed
        assert {case.category for case in report.cases} == {"output_contract"}


@pytest.mark.parametrize("sql", [
    "DROP TABLE order_versions;",
    "DELETE FROM order_versions;",
    "UPDATE order_versions SET open_qty=0;",
    "INSERT INTO order_versions SELECT * FROM order_versions;",
    "ATTACH DATABASE '/tmp/asof-eval-must-not-create.db' AS external;",
    "PRAGMA database_list;",
    "SELECT name FROM sqlite_master;",
    "SELECT load_extension('unavailable');",
    "SELECT sqlite_version();",
    "SELECT random();",
    "SELECT 1; SELECT 2;",
])
def test_non_public_operations_are_denied(task, sql):
    with pytest.raises(QueryExecutionError):
        execute_query(sql, task.schema, task.cases[1])


def test_expensive_query_is_interrupted(task):
    sql = "WITH RECURSIVE x(n) AS (VALUES(1) UNION ALL SELECT n+1 FROM x) SELECT sum(n) FROM x;"
    with pytest.raises(QueryExecutionError, match="interrupted"):
        execute_query(sql, task.schema, task.cases[0])


def test_result_limit_is_enforced(task):
    sql = "WITH RECURSIVE x(n) AS (VALUES(1) UNION ALL SELECT n+1 FROM x WHERE n<10001) SELECT n FROM x;"
    with pytest.raises(QueryExecutionError, match="10,000"):
        execute_query(sql, task.schema, task.cases[0])


def test_bad_or_empty_grader_configuration_raises(task, reference_sql):
    with pytest.raises(ValueError):
        grade_sql(reference_sql, task.schema, [], {}, [], [])
    with pytest.raises(ValueError):
        grade_sql(reference_sql, task.schema, [task.cases[0], task.cases[0]], task.expected,
                  task.metadata["output_columns"], task.metadata["output_types"])
