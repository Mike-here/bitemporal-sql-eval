"""Datetime event replay with explicit withdrawal; no SQL or SQLite dependency."""

from datetime import datetime

COLUMNS = ("order_id", "symbol", "side", "open_qty", "limit_price_cents")


def solve(tables, parameters):
    instant = lambda value: datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    effective = instant(parameters["effective_cutoff"])
    recorded = instant(parameters["recorded_cutoff"])
    history = sorted(tables["order_versions"], key=lambda row: (instant(row["effective_at"]), instant(row["recorded_at"])))
    state = {}
    for row in history:
        if instant(row["recorded_at"]) <= recorded and instant(row["effective_at"]) <= effective:
            state[row["order_id"]] = None if row["operation"] == "DELETE" else tuple(row[key] for key in COLUMNS)
    return sorted(value for value in state.values() if value is not None)
