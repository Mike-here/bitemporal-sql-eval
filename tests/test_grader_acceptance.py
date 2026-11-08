import pytest

from graders.normalize import normalize_rows


@pytest.mark.parametrize("wrapper", [
    lambda sql: sql,
    lambda sql: "\n  " + sql + "\n",
    lambda sql: "```sql\n" + sql + "\n```",
    lambda sql: "```SQL\r\n" + sql + "\r\n```",
    lambda sql: "-- A different explanation in an SQL comment is fine.\n" + sql,
    lambda sql: sql + "\n-- trailing comment\n",
])
def test_presentation_variations_pass(task, reference_sql, wrapper):
    assert task.grade(wrapper(reference_sql)).passed


def test_alias_case_is_ignored(task, reference_sql):
    sql = reference_sql.replace(
        "SELECT order_id, symbol, side, open_qty, limit_price_cents\nFROM ranked",
        "SELECT order_id AS ORDER_ID, symbol AS SYMBOL, side AS SIDE, open_qty AS OPEN_QTY, limit_price_cents AS LIMIT_PRICE_CENTS\nFROM ranked",
    )
    assert task.grade(sql).passed


def test_integral_real_values_are_accepted_when_exact(task, reference_sql):
    sql = reference_sql.replace(
        "SELECT order_id, symbol, side, open_qty, limit_price_cents\nFROM ranked",
        "SELECT order_id, symbol, side, open_qty * 1.0 AS open_qty, limit_price_cents * 1.0 AS limit_price_cents\nFROM ranked",
    )
    assert task.grade(sql).passed


def test_row_order_ignored_and_multiplicity_preserved():
    columns, types = ["id", "qty"], ["text", "integer"]
    assert normalize_rows(columns, [("B", 2), ("A", 1)], columns, types) == normalize_rows(columns, [("A", 1), ("B", 2)], columns, types)
    assert normalize_rows(columns, [("A", 1), ("A", 1)], columns, types) != normalize_rows(columns, [("A", 1)], columns, types)
