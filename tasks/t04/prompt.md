# Idempotent source events with equal timestamps

Write a general SQLite SELECT for the appended order-state ingestion log.
`:effective_cutoff` is the business reporting instant; `:recorded_cutoff` is the
knowledge instant. Both include equality. Times are non-NULL UTC whole-second
TEXT in exactly `YYYY-MM-DDTHH:MM:SSZ`, with no offsets or leap seconds.

Each source event is a complete replacement state. `event_id` identifies that
event globally. Delivery retries may store it multiple times with different
`ingest_id` values; all other columns of those copies are identical. Repeated
delivery has no additional business effect. Ingestion IDs and physical row order
have no business precedence. Event IDs are identity labels, not precedence keys.

An event can affect this report only if it was known by the knowledge instant and
its effective time is not after the business instant. For events of one order,
business precedence is lexicographic greatest `(effective_at, recorded_at,
revision, source_seq)`, comparing the last two fields as integers. A revision
counter only resolves equal effective AND recorded timestamps; source sequence
only resolves equality in those first three fields. A higher counter on an older
effective state does not supersede a newer effective state. Distinct logical
events for the same order never have equal complete precedence tuples.

An authoritative DELETE means that order is absent; older states do not reappear.
DELETE payload fields are ignored. A subsequent authoritative UPSERT can reopen
an order. A zero-quantity UPSERT is retained. Quantities/prices are replacements,
not deltas. No tenants or separate amendment-revision identities exist here.

Return exactly `order_id, symbol, side, open_qty, limit_price_cents` in that order,
one full winning UPSERT state per order. No eligible state means no output row.
An empty log returns zero rows with the stated columns. Order IDs and text values
are case-sensitive and preserved exactly. Column alias case and result row order
are ignored. Extra or duplicate result rows fail; numeric fields must be non-NULL
exact integer-valued SQLite numbers, not strings, with no numeric tolerance.

Return only one SELECT (CTEs allowed), optionally in one SQL fence. A semicolon,
comments and whitespace are accepted. Handle any conforming dataset/cutoff pair,
without hardcoded expected data. Only deterministic queries over public data and
parameters: no writes, PRAGMAs, metadata, files, extensions or environment access.
Per-fixture limits: SQL 65,536 UTF-8 bytes; 10,000 rows; 1,000,000 bytes per value;
expression depth 100; 50 compound SELECT terms; 100 intermediate columns;
5,000,000 VM steps and about 2 seconds.
