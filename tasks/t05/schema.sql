CREATE TABLE order_versions (
    version_id INTEGER PRIMARY KEY,
    tenant_id TEXT NOT NULL COLLATE BINARY,
    book_id TEXT NOT NULL COLLATE BINARY,
    order_id TEXT NOT NULL COLLATE BINARY,
    effective_at TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    operation TEXT NOT NULL CHECK (operation IN ('UPSERT','DELETE')),
    cancellation_key TEXT NOT NULL COLLATE BINARY,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY','SELL')),
    open_qty INTEGER NOT NULL CHECK (typeof(open_qty)='integer' AND open_qty>=0),
    limit_price_cents INTEGER NOT NULL CHECK (typeof(limit_price_cents)='integer' AND limit_price_cents>=0),
    UNIQUE (tenant_id, book_id, order_id, effective_at, recorded_at)
);
CREATE TABLE cancellations (
    cancel_id INTEGER PRIMARY KEY,
    tenant_id TEXT NOT NULL COLLATE BINARY,
    book_id TEXT NOT NULL COLLATE BINARY,
    cancellation_key TEXT NOT NULL COLLATE BINARY,
    effective_at TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);
