# Orders withdrawn from a historical report

Produce a general SQLite SELECT for a historical order-state report. The appended
schema describes full replacement versions, including withdrawal markers.

`:effective_cutoff` is the business instant being reported. `:recorded_cutoff`
is the latest knowledge the report may use. A version is known only when its
recorded timestamp is at or before that knowledge instant. A known version has
business force from its effective timestamp onward. A later effective state
supersedes an earlier effective state of the same order; a later recorded
correction to the SAME effective timestamp replaces the earlier correction.
The unique key in the schema removes all remaining precedence ties.

`operation = 'DELETE'` is a full withdrawal state: the order is absent while
that state has business force. It is not a missing data row and does not uncover
an earlier UPSERT. A later effective UPSERT can reopen the order. A DELETE not
yet known, or not yet effective, has no effect on this report. Payload fields on
DELETE rows are arbitrary non-NULL placeholders and must not appear in the output.
An UPSERT with zero quantity remains a reportable order. Values are replacements,
not deltas. Order IDs are globally scoped, exact and case-sensitive; storage
`version_id` and insertion order have no precedence meaning.

Both time boundaries include equality. All timestamps and supplied cutoffs use
exact UTC `YYYY-MM-DDTHH:MM:SSZ` whole-second TEXT, so text comparison preserves
chronology. There are no NULLs, offsets or leap seconds, and no required ordering
between the two cutoffs or between a version's timestamps.

Return exactly `order_id, symbol, side, open_qty, limit_price_cents`, in that column
order, one row for each reportable order and none for absent orders. Aliases are
case-insensitive; row order is ignored; duplicate rows fail. Text must match
exactly. Quantity/price must be non-NULL exact integer-valued SQLite numbers,
not numeric strings; there is no numeric tolerance.

Return one SELECT (CTEs allowed), raw or in a single SQL fence, without surrounding
prose. The query must handle arbitrary conforming datasets and cutoff pairs,
including an empty input, without hardcoded data. Comments/whitespace and a
trailing semicolon are accepted. Only deterministic queries over the public
schema/parameters are permitted: no writes, PRAGMAs, metadata, files, extensions,
randomness or environment inspection. Limits per fixture: 65,536 SQL UTF-8 bytes,
10,000 result rows, 1,000,000 bytes per value, expression depth 100, 50 compound
SELECT terms, 100 intermediate columns, 5,000,000 VM steps and about 2 seconds.
