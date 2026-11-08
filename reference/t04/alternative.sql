SELECT DISTINCT a.order_id,a.symbol,a.side,a.open_qty,a.limit_price_cents
FROM order_versions a
WHERE a.operation='UPSERT'
  AND a.effective_at <= :effective_cutoff AND a.recorded_at <= :recorded_cutoff
  AND NOT EXISTS (
    SELECT 1 FROM order_versions b
    WHERE b.order_id=a.order_id
      AND b.effective_at <= :effective_cutoff AND b.recorded_at <= :recorded_cutoff
      AND (b.effective_at,b.recorded_at,b.revision,b.source_seq) >
          (a.effective_at,a.recorded_at,a.revision,a.source_seq)
  );
