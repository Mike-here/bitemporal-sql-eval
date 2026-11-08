"""Scoped replay followed by cancellation-set membership; no SQL dependencies."""
from datetime import datetime

COLUMNS=("tenant_id","book_id","order_id","symbol","side","open_qty","limit_price_cents")


def solve(tables,parameters):
    instant=lambda text:datetime.strptime(text,"%Y-%m-%dT%H:%M:%SZ")
    business=instant(parameters["effective_cutoff"]);knowledge=instant(parameters["recorded_cutoff"])
    def visible(row):
        return instant(row["effective_at"])<=business and instant(row["recorded_at"])<=knowledge
    states={}
    history=sorted(tables["order_versions"],key=lambda row:(instant(row["effective_at"]),instant(row["recorded_at"])))
    for row in history:
        if visible(row):states[(row["tenant_id"],row["book_id"],row["order_id"])]=row
    withdrawn={(row["tenant_id"],row["book_id"],row["cancellation_key"])
               for row in tables["cancellations"] if visible(row)}
    return sorted(tuple(row[column] for column in COLUMNS) for row in states.values()
                  if row["operation"]=="UPSERT" and
                  (row["tenant_id"],row["book_id"],row["cancellation_key"]) not in withdrawn)
