"""Independent event-replay oracle: Python datetimes, no SQL or SQLite imports.

AI-drafted; participant review is pending (see review.md).
"""

from datetime import datetime
from typing import Mapping, Sequence

OUTPUT_COLUMNS = ("order_id", "symbol", "side", "open_qty", "limit_price_cents")


def _instant(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")


def solve(rows: Sequence[Mapping], parameters: Mapping) -> list[tuple]:
    effective_cutoff = _instant(parameters["effective_cutoff"])
    recorded_cutoff = _instant(parameters["recorded_cutoff"])
    visible = [
        row for row in rows
        if _instant(row["recorded_at"]) <= recorded_cutoff
        and _instant(row["effective_at"]) <= effective_cutoff
    ]
    # Replay in business-time order, with corrections to the same business-time
    # state applied in knowledge-time order. Later states overwrite earlier ones.
    visible.sort(key=lambda row: (_instant(row["effective_at"]), _instant(row["recorded_at"])))
    state = {}
    for row in visible:
        state[row["order_id"]] = tuple(row[column] for column in OUTPUT_COLUMNS)
    return [state[key] for key in sorted(state)]
