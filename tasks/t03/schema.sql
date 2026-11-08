CREATE TABLE order_versions (
    record_id INTEGER PRIMARY KEY,
    order_id TEXT NOT NULL COLLATE BINARY,
    amendment_no INTEGER NOT NULL CHECK (typeof(amendment_no)='integer' AND amendment_no>0),
    effective_at TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY','SELL')),
    open_qty INTEGER NOT NULL CHECK (typeof(open_qty)='integer' AND open_qty>=0),
    limit_price_cents INTEGER NOT NULL CHECK (typeof(limit_price_cents)='integer' AND limit_price_cents>=0),
    UNIQUE (order_id, amendment_no, recorded_at)
);
