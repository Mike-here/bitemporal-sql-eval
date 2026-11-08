WITH logical_events AS (
  SELECT DISTINCT event_id,tenant_id,book_id,order_id,amendment_no,effective_at,
    recorded_at,revision,source_seq,operation,side,open_qty,limit_price_cents
  FROM order_versions
), meanings AS (
  SELECT a.* FROM logical_events a
  WHERE a.recorded_at <= :recorded_cutoff
    AND NOT EXISTS (
      SELECT 1 FROM logical_events b
      WHERE (b.tenant_id,b.book_id,b.order_id,b.amendment_no)=
            (a.tenant_id,a.book_id,a.order_id,a.amendment_no)
        AND b.recorded_at <= :recorded_cutoff
        AND (b.recorded_at,b.revision,b.source_seq)>(a.recorded_at,a.revision,a.source_seq)
    )
), winners AS (
  SELECT a.* FROM meanings a WHERE a.effective_at <= :effective_cutoff
    AND NOT EXISTS (
      SELECT 1 FROM meanings b
      WHERE (b.tenant_id,b.book_id,b.order_id)=(a.tenant_id,a.book_id,a.order_id)
        AND b.effective_at <= :effective_cutoff
        AND (b.effective_at,b.amendment_no)>(a.effective_at,a.amendment_no)
    )
)
SELECT r.tenant_id,COUNT(w.order_id) AS active_order_count,
  SUM(CASE WHEN w.side='BUY' THEN w.open_qty WHEN w.side='SELL' THEN -w.open_qty ELSE 0 END) AS net_qty,
  SUM(CASE WHEN w.side='BUY' THEN w.open_qty*w.limit_price_cents WHEN w.side='SELL' THEN -w.open_qty*w.limit_price_cents ELSE 0 END) AS net_notional_cents
FROM reporting_books r LEFT JOIN winners w
  ON w.tenant_id=r.tenant_id AND w.book_id=r.book_id AND w.operation='UPSERT'
GROUP BY r.tenant_id;
