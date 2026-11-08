# Point-in-time order state for a reporting cutoff

You maintain an order-state report used to reconcile a trading application's
historical view. Write ONE general SQLite SELECT query (CTEs/window functions are
allowed) over `order_versions`. The schema is appended below. The query will be
executed on multiple unseen datasets and cutoff pairs that obey this contract.
Do not hardcode sample IDs, timestamps or expected rows.

Each row is a COMPLETE replacement state for one globally scoped `order_id`,
not a quantity/price delta. `effective_at` is when that business state takes
effect. `recorded_at` is when the reporting system first knew that version.
Records can arrive out of effective-time order. A later recorded version of an
earlier effective state does not supersede a later effective state. Future-effective
rows may already have been recorded. `version_id` is only a storage identifier:
its numeric magnitude and insertion order do not establish business precedence.

Two named TEXT parameters are supplied by the caller:

- `:effective_cutoff`: report the business state at this instant.
- `:recorded_cutoff`: use only knowledge available at this instant.

All timestamps and parameters are non-NULL UTC TEXT in exactly
`YYYY-MM-DDTHH:MM:SSZ` format, with whole seconds, four-digit years, no leap
seconds, and no timezone offsets. Direct text comparison orders these instants.
There is no required ordering between the two cutoffs, nor between a row's
effective and recorded timestamps.

For EACH order:

1. Consider only rows with `effective_at <= :effective_cutoff` AND
   `recorded_at <= :recorded_cutoff`. Both bounds are inclusive.
2. Among those eligible rows choose the greatest `effective_at`. If multiple
   versions share that effective time, choose the greatest `recorded_at`.
   The schema guarantees `(order_id, effective_at, recorded_at)` is unique, so
   there is no unresolved tie in this task.
3. Return the complete state from that ONE winning row. If no row is eligible,
   omit the order. Keep winning rows whose `open_qty` is zero.

Return exactly these columns, in this order, with these aliases (alias case is
ignored): `order_id, symbol, side, open_qty, limit_price_cents`.
Text values are case-sensitive and must be preserved exactly. Quantity and price
must be non-NULL exact integer-valued SQLite numbers, not numeric strings. There
is no rounding or floating-point tolerance. Exactly one row per eligible order is
required; extra rows and duplicate rows fail. Result ROW order is ignored.
There are no tombstones, cancellation rows, tenants or delta events in this task.

Return only the query, optionally enclosed in ONE `sql` code fence, with no
surrounding explanation. A trailing semicolon, SQL comments and whitespace are
accepted. The query must work for any conforming input; the empty input returns
zero rows with the stated columns. No temporary tables, writes, PRAGMAs, external
files, extensions, database metadata, randomness or environment introspection.
Use deterministic SQLite operations based on the supplied table and parameters.
Execution limits: SQL <= 65,536 UTF-8 bytes; result <= 10,000 rows; individual
SQLite values <= 1,000,000 bytes; <= 5,000,000 SQLite VM steps and about 2 seconds
per fixture; expression depth <= 100; compound SELECT terms <= 50; intermediate
result columns <= 100. The small test datasets do not require expensive computation.
