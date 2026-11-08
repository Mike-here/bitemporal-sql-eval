"""Two-level Python amendment reconstruction; independent of SQL evaluation."""
from datetime import datetime

COLUMNS=("order_id","symbol","side","open_qty","limit_price_cents")


def solve(tables, parameters):
    instant=lambda text: datetime.strptime(text,"%Y-%m-%dT%H:%M:%SZ")
    knowledge=instant(parameters["recorded_cutoff"])
    business=instant(parameters["effective_cutoff"])
    amendments={}
    for row in tables["order_versions"]:
        recorded=instant(row["recorded_at"])
        identity=(row["order_id"],row["amendment_no"])
        if recorded<=knowledge and (identity not in amendments or recorded>instant(amendments[identity]["recorded_at"])):
            amendments[identity]=row
    orders={}
    for row in amendments.values():
        effective=instant(row["effective_at"])
        if effective<=business:
            key=(effective,row["amendment_no"])
            order=row["order_id"]
            if order not in orders or key>orders[order][0]:
                orders[order]=(key,tuple(row[column] for column in COLUMNS))
    return sorted(value[1] for value in orders.values())
