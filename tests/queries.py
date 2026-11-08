"""Semantically valid alternatives and deliberately wrong, executable queries."""

PROJECTION = "order_id, symbol, side, open_qty, limit_price_cents"
ELIGIBLE = "effective_at <= :effective_cutoff AND recorded_at <= :recorded_cutoff"

NOT_EXISTS = f"""
SELECT a.order_id, a.symbol, a.side, a.open_qty, a.limit_price_cents
FROM order_versions AS a
WHERE a.effective_at <= :effective_cutoff AND a.recorded_at <= :recorded_cutoff
AND NOT EXISTS (
    SELECT 1 FROM order_versions AS b
    WHERE b.order_id = a.order_id
      AND b.effective_at <= :effective_cutoff AND b.recorded_at <= :recorded_cutoff
      AND (b.effective_at > a.effective_at
           OR (b.effective_at = a.effective_at AND b.recorded_at > a.recorded_at))
)
ORDER BY a.order_id DESC;
"""

GROUPED_JOINS = f"""
WITH eligible AS (SELECT * FROM order_versions WHERE {ELIGIBLE}),
latest_effective AS (
  SELECT order_id, MAX(effective_at) AS effective_at FROM eligible GROUP BY order_id
), latest_recorded AS (
  SELECT e.order_id, e.effective_at, MAX(e.recorded_at) AS recorded_at
  FROM eligible e JOIN latest_effective l
    ON e.order_id = l.order_id AND e.effective_at = l.effective_at
  GROUP BY e.order_id, e.effective_at
)
SELECT e.order_id, e.symbol, e.side, e.open_qty, e.limit_price_cents
FROM eligible e JOIN latest_recorded l
  ON e.order_id = l.order_id AND e.effective_at = l.effective_at AND e.recorded_at = l.recorded_at;
"""

FIRST_VALUE = f"""
WITH eligible AS (SELECT * FROM order_versions WHERE {ELIGIBLE})
SELECT DISTINCT order_id,
  FIRST_VALUE(symbol) OVER w AS symbol,
  FIRST_VALUE(side) OVER w AS side,
  FIRST_VALUE(open_qty) OVER w AS open_qty,
  FIRST_VALUE(limit_price_cents) OVER w AS limit_price_cents
FROM eligible
WINDOW w AS (PARTITION BY order_id ORDER BY effective_at DESC, recorded_at DESC);
"""

ALTERNATIVES = {"correlated_not_exists": NOT_EXISTS, "grouped_joins": GROUPED_JOINS,
                "first_value": FIRST_VALUE}


def ranked(predicate=ELIGIBLE, ordering="effective_at DESC, recorded_at DESC", partition="order_id", extra=""):
    return f"""
WITH ranked AS (
 SELECT *, ROW_NUMBER() OVER (PARTITION BY {partition} ORDER BY {ordering}) AS rn
 FROM order_versions WHERE {predicate}
)
SELECT {PROJECTION} FROM ranked WHERE rn = 1 {extra};
"""


MUTANTS = {
    "missing_recorded_cutoff": ranked("effective_at <= :effective_cutoff"),
    "missing_effective_cutoff": ranked("recorded_at <= :recorded_cutoff"),
    "swapped_cutoffs": ranked("effective_at <= :recorded_cutoff AND recorded_at <= :effective_cutoff"),
    "either_cutoff_instead_of_both": ranked("effective_at <= :effective_cutoff OR recorded_at <= :recorded_cutoff"),
    "recorded_time_first": ranked(ordering="recorded_at DESC, effective_at DESC"),
    "earliest_effective": ranked(ordering="effective_at ASC, recorded_at DESC"),
    "earliest_correction": ranked(ordering="effective_at DESC, recorded_at ASC"),
    "storage_id_precedence": ranked(ordering="version_id DESC"),
    "exclude_exact_effective_boundary": ranked("effective_at < :effective_cutoff AND recorded_at <= :recorded_cutoff"),
    "exclude_exact_recorded_boundary": ranked("effective_at <= :effective_cutoff AND recorded_at < :recorded_cutoff"),
    "drop_zero_quantity": ranked(extra="AND open_qty > 0"),
    "partition_by_symbol": ranked(partition="symbol"),
    "rank_before_eligibility": f"""
      WITH ranked AS (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY effective_at DESC, recorded_at DESC) AS rn
        FROM order_versions
      ) SELECT {PROJECTION} FROM ranked WHERE rn = 1 AND {ELIGIBLE};
    """,
    "return_all_eligible": f"SELECT {PROJECTION} FROM order_versions WHERE {ELIGIBLE};",
    "duplicate_winners": ranked().rstrip(";\n ") + f" UNION ALL SELECT {PROJECTION} FROM ranked WHERE rn = 1;",
    "independent_column_maxima": f"""
      SELECT order_id, MAX(symbol) AS symbol, MAX(side) AS side,
             MAX(open_qty) AS open_qty, MAX(limit_price_cents) AS limit_price_cents
      FROM order_versions WHERE {ELIGIBLE} GROUP BY order_id;
    """,
    "sum_replacements_as_deltas": f"""
      SELECT order_id, MAX(symbol) AS symbol, MAX(side) AS side,
             SUM(open_qty) AS open_qty, MAX(limit_price_cents) AS limit_price_cents
      FROM order_versions WHERE {ELIGIBLE} GROUP BY order_id;
    """,
}
