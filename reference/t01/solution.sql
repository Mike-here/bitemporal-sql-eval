WITH eligible AS (
    SELECT *
    FROM order_versions
    WHERE effective_at <= :effective_cutoff
      AND recorded_at <= :recorded_cutoff
), ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY order_id
               ORDER BY effective_at DESC, recorded_at DESC
           ) AS position
    FROM eligible
)
SELECT order_id, symbol, side, open_qty, limit_price_cents
FROM ranked
WHERE position = 1;
