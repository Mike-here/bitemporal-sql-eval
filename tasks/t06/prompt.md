# Point-in-time net order exposure across reporting books

Write one general SQLite SELECT for the appended schema. The reporting service
needs net open-order inventory and signed limit-price notional per tenant at
`:effective_cutoff`, reconstructed using knowledge available at `:recorded_cutoff`.
All books concern the same instrument XYZ and currency USD, so their quantities
and cents are comparable. This is an order-state calculation, not a cash ledger.

The reporting universe is `reporting_books`. Return EVERY tenant appearing there
exactly once, combining only that tenant's listed books. An unlisted book never
contributes, even if its tenant has another listed book. A listed tenant with no
reportable orders has count and both totals equal to integer zero. An empty
reporting roster produces no rows. Book IDs repeat across tenants.

An order is identified by `(tenant_id, book_id, order_id)`. Within an order,
`amendment_no` identifies a single business amendment. Each source event is a
recorded revision of that amendment. `event_id` identifies that source event
globally; delivery retries can duplicate it with a different `ingest_id` and ALL
other fields identical. Those copies have one business effect. Storage/event IDs
do not establish precedence. Distinct source events for the same amendment have
distinct `(recorded_at, revision, source_seq)` tuples.

At a knowledge instant, an amendment means what its greatest known
`(recorded_at, revision, source_seq)` tuple says: recorded timestamp dominates,
then integer revision, then integer source sequence. That meaning includes the
effective timestamp, operation and entire payload. Older recorded revisions do
not survive as independent amendments. A correction may move effective time
forward or backward; an unknown correction cannot change historical knowledge.

At a business instant, an order's controlling amendment is the one with greatest
`(effective_at, amendment_no)` among the amendments whose current meanings have
taken effect by that instant. Amendment numbers compare as integers and only
resolve equal effective timestamps. A later arrival for an earlier-effective
amendment does not automatically dominate a later-effective amendment. A known
correction moving an amendment beyond the business instant does not preserve its
obsolete earlier effective state.

A controlling DELETE means the order is absent. Its non-NULL placeholder payload
is ignored and earlier order states are not resurrected. A controlling UPSERT is
one active/reportable order, including when its quantity is zero. All quantities
and prices are full replacement values, not deltas. There are no independent
cancellation-group facts in this task.

For each tenant, `active_order_count` is the number of reportable orders across
its listed books (not deliveries, revisions or amendments). `net_qty` adds BUY
open quantities and subtracts SELL open quantities. `net_notional_cents` adds
`open_qty * limit_price_cents` for BUY and subtracts that product for SELL.
Offsetting positions still count as active orders; a zero net total is not an
empty tenant. All inputs are integers. Every individual product and the sum of
absolute products/quantities across all input rows fit signed 64-bit integers.

Both cutoffs include equality. All timestamps/cutoffs are non-NULL UTC TEXT in
exact `YYYY-MM-DDTHH:MM:SSZ` whole-second format, no offsets/leap seconds; text
comparison preserves chronology. No ordering between cutoffs is assumed.
Identifiers/text compare exactly and case-sensitively.

Return exactly `tenant_id, active_order_count, net_qty, net_notional_cents` in that
column order. All numeric outputs must be non-NULL exact integer-valued SQLite
numbers, not strings; no rounding/tolerance. Alias case and result row order are
ignored; missing, extra or duplicate tenant rows fail.

Return only one SELECT (CTEs allowed), optionally in one SQL fence. Whitespace,
SQL comments and a semicolon are accepted. Handle arbitrary conforming data and
bound cutoffs; no hardcoded expected values. Only deterministic public-schema
queries: no writes, PRAGMAs, metadata, files, extensions, randomness or environment
inspection. Limits per fixture: 65,536 SQL UTF-8 bytes; 10,000 rows; 1,000,000 bytes
per value; expression depth 100; 50 compound SELECT terms; 100 intermediate
columns; 5,000,000 VM steps and about 2 seconds.
