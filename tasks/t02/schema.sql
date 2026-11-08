CREATE TABLE order_versions (
    version_id INTEGER PRIMARY KEY,
    order_id TEXT NOT NULL COLLATE BINARY,
    effective_at TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    operation TEXT NOT NULL CHECK (operation IN ('UPSERT', 'DELETE')),
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    open_qty INTEGER NOT NULL CHECK (typeof(open_qty)='integer' AND open_qty>=0),
    limit_price_cents INTEGER NOT NULL CHECK (typeof(limit_price_cents)='integer' AND limit_price_cents>=0),
    UNIQUE (order_id, effective_at, recorded_at)
);
