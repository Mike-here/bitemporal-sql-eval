WITH logical_events AS (
  SELECT DISTINCT event_id,tenant_id,book_id,order_id,amendment_no,effective_at,
    recorded_at,revision,source_seq,operation,side,open_qty,limit_price_cents
  FROM order_versions
), known AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY tenant_id,book_id,order_id,amendment_no
    ORDER BY recorded_at DESC,revision DESC,source_seq DESC
  ) AS revision_rank
  FROM logical_events WHERE recorded_at <= :recorded_cutoff
), effective AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY tenant_id,book_id,order_id
    ORDER BY effective_at DESC,amendment_no DESC
  ) AS order_rank
  FROM known WHERE revision_rank=1 AND effective_at <= :effective_cutoff
), active AS (
  SELECT e.* FROM effective e
  JOIN reporting_books b ON b.tenant_id=e.tenant_id AND b.book_id=e.book_id
  WHERE order_rank=1 AND operation='UPSERT'
), totals AS (
  SELECT tenant_id,COUNT(*) AS active_order_count,
    SUM(CASE WHEN side='BUY' THEN open_qty ELSE -open_qty END) AS net_qty,
    SUM(CASE WHEN side='BUY' THEN open_qty*limit_price_cents ELSE -open_qty*limit_price_cents END) AS net_notional_cents
  FROM active GROUP BY tenant_id
), tenants AS (SELECT DISTINCT tenant_id FROM reporting_books)
SELECT t.tenant_id,COALESCE(s.active_order_count,0) AS active_order_count,
  COALESCE(s.net_qty,0) AS net_qty,COALESCE(s.net_notional_cents,0) AS net_notional_cents
FROM tenants t LEFT JOIN totals s ON s.tenant_id=t.tenant_id;
