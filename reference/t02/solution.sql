WITH report_state AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY order_id ORDER BY effective_at DESC, recorded_at DESC
  ) AS rn
  FROM order_versions
  WHERE effective_at <= :effective_cutoff AND recorded_at <= :recorded_cutoff
)
SELECT order_id, symbol, side, open_qty, limit_price_cents
FROM report_state WHERE rn=1 AND operation='UPSERT';
