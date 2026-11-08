# Restated amendments in a historical order ledger

Write one general SQLite SELECT for the appended schema. An order's full-state
amendments can be corrected after ingestion, including corrections to their
effective timestamp. The report is at business instant `:effective_cutoff`, using
only knowledge available at `:recorded_cutoff`.

`(order_id, amendment_no)` identifies ONE business amendment. Rows sharing that
identity are successive recorded revisions of that amendment, not additional
business amendments. At any knowledge instant, the amendment means exactly what
its most recently recorded revision known at that instant says, including its
effective timestamp and entire payload. An older recorded revision is not a
fallback business event. An amendment with no known revision does not yet exist.

An order's state at the business instant is the full payload of the amendment
with the latest effective timestamp not after that instant, as understood at
the specified knowledge instant. Where different amendments have equal effective
timestamps, the greater `amendment_no` has business precedence. A later recorded
correction to an earlier-effective amendment does not automatically override a
later-effective amendment of the same order. If a known correction moves an
amendment into the future, its obsolete earlier effective timestamp no longer
gives it force in this report. Conversely, a correction not yet recorded must not
change what an earlier report knew, even if its effective timestamp is in the past.

Every amendment is a complete replacement state, not a delta. Zero quantity is
retained. There are no deletes or tenants. `record_id` and physical row order are
storage details. `amendment_no` is stable across revisions; it resolves effective
ties only. The schema guarantees distinct recorded timestamps for the revisions
of one amendment. IDs and other TEXT values are exact and case-sensitive.

Both cutoff boundaries include equality. All timestamps and parameters are
non-NULL UTC TEXT with exactly `YYYY-MM-DDTHH:MM:SSZ`, whole seconds, no offsets or
leap seconds. Text comparison preserves chronology. Timestamp/cutoff ordering is
otherwise unrestricted.

Return exactly `order_id, symbol, side, open_qty, limit_price_cents` in that column
order, one complete state per reportable order. Omit orders with no applicable
amendment. Empty input gives zero rows with the stated columns. Alias case and
row order are ignored; duplicate rows fail. Quantity and price must be non-NULL
exact integer-valued SQLite numbers, not strings; text is preserved exactly.

Return only one SELECT (CTEs allowed), optionally in one SQL fence. A semicolon,
comments and whitespace are accepted. Do not hardcode fixture IDs, values or
cutoffs. No writes, PRAGMAs, metadata/files/extensions, randomness or environment
inspection; only deterministic operations over public data and bound parameters.
Per-fixture limits: SQL 65,536 UTF-8 bytes; 10,000 output rows; 1,000,000 bytes per
value; expression depth 100; 50 compound SELECT terms; 100 intermediate columns;
5,000,000 VM steps and about 2 seconds.
