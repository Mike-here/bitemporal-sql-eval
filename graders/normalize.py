"""Normalize presentation only; preserve semantic differences and row multiplicity."""

from collections import Counter
import math
import re
from typing import Iterable, Sequence


class OutputContractError(ValueError):
    """A candidate cannot be interpreted under the published output contract."""


def extract_sql(response: str) -> str:
    if not isinstance(response, str):
        raise OutputContractError("Response must be text.")
    sql = response.strip()
    if sql.startswith("```"):
        match = re.fullmatch(r"```(?:sql|sqlite)?[ \t]*\r?\n(.*?)\r?\n```", sql, re.I | re.S)
        if not match:
            raise OutputContractError("Return raw SQL or one complete SQL code fence without surrounding prose.")
        sql = match.group(1).strip()
    if not sql:
        raise OutputContractError("Empty SQL response.")
    if len(sql.encode("utf-8")) > 65_536:
        raise OutputContractError("SQL exceeds the published 65,536-byte limit.")
    return sql


def normalize_rows(
    columns: Sequence[str],
    rows: Iterable[Sequence[object]],
    expected_columns: Sequence[str],
    column_types: Sequence[str],
) -> Counter:
    # Column order matters; alias capitalization and output row order do not.
    if tuple(c.casefold() for c in columns) != tuple(c.casefold() for c in expected_columns):
        raise OutputContractError(f"Expected columns {list(expected_columns)}; got {list(columns)}.")
    if len(column_types) != len(expected_columns):
        raise ValueError("Invalid grader configuration: column/type count differs.")
    result = Counter()
    for row in rows:
        if len(row) != len(column_types):
            raise OutputContractError("Wrong number of values in result row.")
        normalized = []
        for value, kind in zip(row, column_types, strict=True):
            if kind == "text":
                if not isinstance(value, str):
                    raise OutputContractError("Text output must be non-NULL SQLite TEXT.")
                normalized.append(value)  # No case-folding or trimming identifiers.
            elif kind == "integer":
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise OutputContractError("Integer-valued output must be a non-NULL number, not text.")
                if isinstance(value, float):
                    if not math.isfinite(value) or not value.is_integer():
                        raise OutputContractError("Expected an exact integer-valued number.")
                    value = int(value)
                normalized.append(value)  # Never coerce expected integers to float.
            else:
                raise ValueError(f"Unknown configured column type: {kind}")
        result[tuple(normalized)] += 1
    return result
