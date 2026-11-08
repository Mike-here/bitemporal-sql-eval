"""Execute one candidate SELECT on a fresh, restricted in-memory DB per fixture.

This is a SQLite query boundary, not a general-purpose native-code sandbox.
No candidate Python, shell, extensions, filesystem DBs or tools are executed.
"""

from dataclasses import asdict, dataclass
import sqlite3
import time
import re
import math
from typing import Mapping, Sequence

from graders.normalize import OutputContractError, extract_sql, normalize_rows

MAX_ROWS = 10_000
MAX_STEPS = 5_000_000
MAX_SECONDS = 2.0


class QueryExecutionError(ValueError):
    pass


@dataclass
class CaseResult:
    name: str
    passed: bool
    category: str
    message: str
    expected: list
    actual: list | None = None


@dataclass
class GradeReport:
    passed: bool
    primary_score: int
    fixture_pass_fraction: float
    cases: list[CaseResult]

    def to_dict(self) -> dict:
        # Invalid candidate result types still need a durable JSON failure log.
        def serializable(value):
            if isinstance(value, bytes):
                return {"sqlite_blob_hex": value.hex()}
            if isinstance(value, float) and not math.isfinite(value):
                return {"non_finite_number": str(value)}
            if isinstance(value, (list, tuple)):
                return [serializable(item) for item in value]
            if isinstance(value, dict):
                return {key: serializable(item) for key, item in value.items()}
            return value
        return serializable(asdict(self))


def _authorize(action, arg1, arg2, database, source, *, public_tables):
    if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_RECURSIVE):
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ:
        return (sqlite3.SQLITE_OK if database == "main" and arg1 in public_tables
                else sqlite3.SQLITE_DENY)
    if action == sqlite3.SQLITE_FUNCTION:
        # Core functions have no filesystem access; extensions are never loaded.
        # Deny environment inspection and nondeterministic/environmental functions.
        blocked = {"load_extension", "readfile", "writefile", "sqlite_version",
                   "sqlite_source_id", "sqlite_compileoption_get", "sqlite_compileoption_used",
                   "random", "randomblob", "changes", "total_changes", "last_insert_rowid"}
        return sqlite3.SQLITE_DENY if (arg2 or "").lower() in blocked else sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def execute_query(sql: str, schema: str, case: Mapping) -> tuple[list[str], list[tuple]]:
    connection = sqlite3.connect(":memory:")
    try:
        connection.executescript(schema)
        # Introspect only the trusted schema, before installing the authorizer.
        # Candidate queries can read these public tables, not metadata or files.
        public_tables = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        tables = case["tables"] if "tables" in case else {"order_versions": case["rows"]}
        if not set(tables) <= public_tables:
            raise ValueError("Fixture refers to a table outside the public schema.")
        for table, records in tables.items():
            if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", table):
                raise ValueError("Invalid trusted table name.")
            columns = [column[1] for column in connection.execute(f'PRAGMA table_info("{table}")')]
            if not all(re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", name) for name in columns):
                raise ValueError("Invalid trusted column name.")
            names = ",".join(f'"{name}"' for name in columns)
            parameters = ",".join(f":{name}" for name in columns)
            connection.executemany(f'INSERT INTO "{table}" ({names}) VALUES ({parameters})', records)
        connection.commit()
        connection.execute("PRAGMA query_only = ON")
        connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 1_000_000)
        connection.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 65_536)
        connection.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 100)
        connection.setlimit(sqlite3.SQLITE_LIMIT_EXPR_DEPTH, 100)
        connection.setlimit(sqlite3.SQLITE_LIMIT_COMPOUND_SELECT, 50)
        connection.set_authorizer(lambda *args: _authorize(*args, public_tables=public_tables))
        started = time.monotonic()
        steps = 0

        def progress():
            nonlocal steps
            steps += 1000
            return int(steps >= MAX_STEPS or time.monotonic() - started > MAX_SECONDS)

        connection.set_progress_handler(progress, 1000)
        try:
            cursor = connection.execute(sql, dict(case["parameters"]))
            if cursor.description is None:
                raise QueryExecutionError("Expected one SELECT result.")
            columns = [c[0] for c in cursor.description]
            rows = cursor.fetchmany(MAX_ROWS + 1)
            if len(rows) > MAX_ROWS:
                raise QueryExecutionError("Result exceeds the published 10,000-row limit.")
            return columns, rows
        except sqlite3.Error as error:
            raise QueryExecutionError(str(error)) from error
    finally:
        connection.close()


def grade_sql(
    response: str,
    schema: str,
    cases: Sequence[Mapping],
    expected_rows: Mapping[str, Sequence[Sequence]],
    columns: Sequence[str],
    column_types: Sequence[str],
) -> GradeReport:
    if not cases or len({case["name"] for case in cases}) != len(cases):
        raise ValueError("Grader requires nonempty fixtures with unique names.")
    # Validate expected data before handling candidate failures; broken references
    # must raise an infrastructure error, never be counted as model failures.
    expected = {
        case["name"]: normalize_rows(columns, expected_rows[case["name"]], columns, column_types)
        for case in cases
    }
    results = []
    try:
        sql = extract_sql(response)
    except OutputContractError as error:
        for case in cases:
            results.append(CaseResult(case["name"], False, "output_contract", str(error),
                                      list(expected_rows[case["name"]])))
    else:
        for case in cases:
            name = case["name"]
            actual = None
            try:
                names, actual = execute_query(sql, schema, case)
                observed = normalize_rows(names, actual, columns, column_types)
                passed = observed == expected[name]
                category = "pass" if passed else "wrong_outcome"
                message = "Exact result multiset matches." if passed else "Result multiset differs from reference."
            except OutputContractError as error:
                passed, category, message = False, "output_contract", str(error)
            except QueryExecutionError as error:
                passed, category, message = False, "query_error", str(error)
            results.append(CaseResult(name, passed, category, message,
                                      list(expected_rows[name]), actual))
    successes = sum(case.passed for case in results)
    passed = successes == len(results)
    return GradeReport(passed, int(passed), successes / len(results), results)
