WITH known_revisions AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY order_id, amendment_no ORDER BY recorded_at DESC
  ) AS revision_rank
  FROM order_versions WHERE recorded_at <= :recorded_cutoff
), applicable_amendments AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY order_id ORDER BY effective_at DESC, amendment_no DESC
  ) AS order_rank
  FROM known_revisions WHERE revision_rank=1 AND effective_at <= :effective_cutoff
)
SELECT order_id, symbol, side, open_qty, limit_price_cents
FROM applicable_amendments WHERE order_rank=1;
