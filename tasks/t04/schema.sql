CREATE TABLE order_versions (
    ingest_id INTEGER PRIMARY KEY,
    event_id TEXT NOT NULL COLLATE BINARY,
    order_id TEXT NOT NULL COLLATE BINARY,
    effective_at TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (typeof(revision)='integer' AND revision>=0),
    source_seq INTEGER NOT NULL CHECK (typeof(source_seq)='integer' AND source_seq>=0),
    operation TEXT NOT NULL CHECK (operation IN ('UPSERT','DELETE')),
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY','SELL')),
    open_qty INTEGER NOT NULL CHECK (typeof(open_qty)='integer' AND open_qty>=0),
    limit_price_cents INTEGER NOT NULL CHECK (typeof(limit_price_cents)='integer' AND limit_price_cents>=0)
);
