WITH current_amendments AS (
  SELECT a.* FROM order_versions a
  WHERE a.recorded_at <= :recorded_cutoff
    AND NOT EXISTS (
      SELECT 1 FROM order_versions b
      WHERE b.order_id=a.order_id AND b.amendment_no=a.amendment_no
        AND b.recorded_at <= :recorded_cutoff AND b.recorded_at>a.recorded_at
    )
)
SELECT a.order_id, a.symbol, a.side, a.open_qty, a.limit_price_cents
FROM current_amendments a
WHERE a.effective_at <= :effective_cutoff
  AND NOT EXISTS (
    SELECT 1 FROM current_amendments b
    WHERE b.order_id=a.order_id AND b.effective_at <= :effective_cutoff
      AND (b.effective_at>a.effective_at OR
           (b.effective_at=a.effective_at AND b.amendment_no>a.amendment_no))
  );
