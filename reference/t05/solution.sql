WITH ranked AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY tenant_id,book_id,order_id
    ORDER BY effective_at DESC,recorded_at DESC
  ) AS rn
  FROM order_versions
  WHERE effective_at <= :effective_cutoff AND recorded_at <= :recorded_cutoff
)
SELECT v.tenant_id,v.book_id,v.order_id,v.symbol,v.side,v.open_qty,v.limit_price_cents
FROM ranked v
WHERE v.rn=1 AND v.operation='UPSERT'
  AND NOT EXISTS (
    SELECT 1 FROM cancellations c
    WHERE c.tenant_id=v.tenant_id AND c.book_id=v.book_id
      AND c.cancellation_key=v.cancellation_key
      AND c.effective_at <= :effective_cutoff AND c.recorded_at <= :recorded_cutoff
  );
