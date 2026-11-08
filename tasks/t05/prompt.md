# Scoped order state and exchange cancellation groups

Write one general SQLite SELECT using the appended public tables. Report the
historical order state at `:effective_cutoff`, using knowledge available at
`:recorded_cutoff`. Both cutoff boundaries are inclusive. Every timestamp and
parameter is non-NULL UTC whole-second TEXT in exactly `YYYY-MM-DDTHH:MM:SSZ`,
with no offsets/leap seconds; text comparison preserves chronology.

An order's identity is the complete `(tenant_id, book_id, order_id)` tuple. Book
names can repeat across tenants and order IDs can repeat across both tenants and
books. Within that identity, full replacement versions have business precedence
by greatest effective timestamp, then greatest recorded timestamp at the same
effective time. Only versions known by the knowledge instant and effective by the
business instant can govern the report. The schema removes unresolved ties.
Storage IDs and row order are irrelevant. All identifiers are case-sensitive.

A governing DELETE means absence; its payload is ignored and an earlier UPSERT
does not reappear. A governing UPSERT with zero quantity is still reportable.
Reopening requires a later governing UPSERT. Each state supplies its current
`cancellation_key`, which can change across order versions.

A row in `cancellations` is a durable withdrawal of the named cancellation group
within exactly its own `(tenant_id, book_id)`. It affects the report only when
known and effective by the two respective cutoffs. Within this report it removes
every otherwise reportable order whose CURRENT state has that cancellation key
in the SAME tenant and book. It never affects another tenant/book even if their
order IDs or cancellation keys collide. A cancellation attached to an obsolete
order-state key does not apply to a new current key. A cancellation of a current
key does not reveal an older order version with another key. Cancellation groups
do not expire or have revocation events in this task. Repeated cancellation facts
have no additional effect and must not multiply output rows.

Return exactly `tenant_id, book_id, order_id, symbol, side, open_qty,
limit_price_cents` in that column order, one complete state per surviving order.
Absent/cancelled orders are omitted. Empty inputs produce zero rows with those
columns. Text is exact; numeric fields are non-NULL exact integer-valued SQLite
numbers, not strings, with no tolerance. Alias case and row order are ignored;
extra or duplicate rows fail.

Return only one SELECT (CTEs allowed), raw or in one SQL fence. Comments, whitespace
and a trailing semicolon are accepted. Handle arbitrary conforming data and cutoff
pairs without hardcoded expected values. No writes, PRAGMAs, metadata, files,
extensions, randomness or environment inspection. Only deterministic public-table
operations are permitted. Per-fixture limits: 65,536 SQL UTF-8 bytes; 10,000 rows;
1,000,000 bytes per value; expression depth 100; 50 compound SELECT terms;
100 intermediate columns; 5,000,000 VM steps and about 2 seconds.
