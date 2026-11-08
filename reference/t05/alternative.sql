SELECT a.tenant_id,a.book_id,a.order_id,a.symbol,a.side,a.open_qty,a.limit_price_cents
FROM order_versions a
WHERE a.effective_at <= :effective_cutoff AND a.recorded_at <= :recorded_cutoff
  AND a.operation='UPSERT'
  AND NOT EXISTS (
    SELECT 1 FROM order_versions b
    WHERE b.tenant_id=a.tenant_id AND b.book_id=a.book_id AND b.order_id=a.order_id
      AND b.effective_at <= :effective_cutoff AND b.recorded_at <= :recorded_cutoff
      AND (b.effective_at,b.recorded_at) > (a.effective_at,a.recorded_at)
  )
  AND NOT EXISTS (
    SELECT 1 FROM cancellations c
    WHERE (c.tenant_id,c.book_id,c.cancellation_key)=(a.tenant_id,a.book_id,a.cancellation_key)
      AND c.effective_at <= :effective_cutoff AND c.recorded_at <= :recorded_cutoff
  );
