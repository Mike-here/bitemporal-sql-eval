import copy
from itertools import combinations, permutations

import pytest

from graders.sql_outcome import execute_query
from reference.t01.oracle import solve
from tests.queries import ALTERNATIVES


@pytest.mark.parametrize("case_index", range(40))
def test_sql_and_independent_oracle_match_every_fixture(task, reference_sql, case_index):
    case = task.cases[case_index]
    columns, rows = execute_query(reference_sql, task.schema, case)
    assert columns == task.metadata["output_columns"]
    assert sorted(rows) == solve(case["rows"], case["parameters"])
    if "expected" in case:
        assert sorted(rows) == sorted(tuple(row) for row in case["expected"])


@pytest.mark.parametrize("name", ALTERNATIVES)
def test_alternative_algorithms_pass_entire_suite(task, name):
    report = task.grade(ALTERNATIVES[name])
    assert report.passed, report.to_dict()


def test_reference_passes_all_graders(task, reference_sql):
    report = task.grade(reference_sql)
    assert report.passed
    assert report.primary_score == 1
    assert report.fixture_pass_fraction == 1
    assert len(report.cases) == 40


def test_ascending_replay_keeps_last_newest_state_not_first(task, reference_sql):
    # Explicit golden independent of either implementation. The late-arriving
    # retro-correction (qty 88) must not replace the later business state (qty 25).
    # Reversing the oracle sort with its current overwrite loop fails this test.
    def event(version, order, effective, recorded, quantity):
        return dict(version_id=version, order_id=order,
                    effective_at=f"2026-10-30T{effective}:00Z",
                    recorded_at=f"2026-10-30T{recorded}:00Z",
                    symbol="XYZ", side="BUY", open_qty=quantity, limit_price_cents=100)

    history = [event(900, "A", "08:00", "08:00", 10),
               event(700, "A", "08:00", "11:00", 88),
               event(5, "A", "09:00", "09:00", 20),
               event(1, "A", "09:00", "10:00", 25),
               event(2, "B", "08:30", "09:30", 7)]
    parameters = dict(effective_cutoff="2026-10-30T10:00:00Z",
                      recorded_cutoff="2026-10-30T12:00:00Z")
    expected = [("A", "XYZ", "BUY", 25, 100), ("B", "XYZ", "BUY", 7, 100)]
    for ordering in permutations(history):
        assert solve(ordering, parameters) == expected
    _, actual = execute_query(reference_sql, task.schema, {"rows": history, "parameters": parameters})
    assert sorted(actual) == expected


def test_physical_insertion_order_is_irrelevant(task, reference_sql):
    for original in task.cases:
        case = copy.deepcopy(original)
        case["rows"].reverse()
        _, rows = execute_query(reference_sql, task.schema, case)
        assert sorted(rows) == task.expected[case["name"]]
        assert solve(case["rows"], case["parameters"]) == task.expected[case["name"]]


def test_all_subhistories_and_cutoff_pairs_for_small_bounded_domain(task, reference_sql):
    # Exhaust all 16 subsets of a four-event history and 9 cutoff pairs.
    # One order has a retro-correction; another independently becomes effective.
    events = [
        dict(version_id=7, order_id="A", effective_at="2026-10-30T08:00:00Z", recorded_at="2026-10-30T08:00:00Z", symbol="X", side="BUY", open_qty=1, limit_price_cents=100),
        dict(version_id=2, order_id="A", effective_at="2026-10-30T09:00:00Z", recorded_at="2026-10-30T09:00:00Z", symbol="X", side="BUY", open_qty=2, limit_price_cents=200),
        dict(version_id=9, order_id="A", effective_at="2026-10-30T08:00:00Z", recorded_at="2026-10-30T10:00:00Z", symbol="X", side="SELL", open_qty=0, limit_price_cents=300),
        dict(version_id=1, order_id="B", effective_at="2026-10-30T09:00:00Z", recorded_at="2026-10-30T08:00:00Z", symbol="Y", side="SELL", open_qty=3, limit_price_cents=400),
    ]
    cutoffs = ["2026-10-30T08:00:00Z", "2026-10-30T09:00:00Z", "2026-10-30T10:00:00Z"]
    for size in range(5):
        for selected in combinations(events, size):
            for effective in cutoffs:
                for recorded in cutoffs:
                    case = {"rows": list(selected), "parameters": {"effective_cutoff": effective, "recorded_cutoff": recorded}}
                    expected = solve(case["rows"], case["parameters"])
                    for sql in [reference_sql, ALTERNATIVES["correlated_not_exists"]]:
                        _, result = execute_query(sql, task.schema, case)
                        assert sorted(result) == expected
