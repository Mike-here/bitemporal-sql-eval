WITH logical_events AS (
  SELECT DISTINCT event_id, order_id, effective_at, recorded_at, revision, source_seq,
                  operation, symbol, side, open_qty, limit_price_cents
  FROM order_versions
), ranked AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY order_id
    ORDER BY effective_at DESC, recorded_at DESC, revision DESC, source_seq DESC
  ) AS rn
  FROM logical_events
  WHERE effective_at <= :effective_cutoff AND recorded_at <= :recorded_cutoff
)
SELECT order_id, symbol, side, open_qty, limit_price_cents
FROM ranked WHERE rn=1 AND operation='UPSERT';
