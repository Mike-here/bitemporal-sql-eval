"""Logical-event deduplication and tuple comparison with Python datetimes."""
from datetime import datetime

COLUMNS=("order_id","symbol","side","open_qty","limit_price_cents")


def solve(tables,parameters):
    instant=lambda text:datetime.strptime(text,"%Y-%m-%dT%H:%M:%SZ")
    logical={}
    for row in tables["order_versions"]:
        payload={key:value for key,value in row.items() if key!="ingest_id"}
        if row["event_id"] in logical and logical[row["event_id"]]!=payload:
            raise ValueError("Conflicting payload for duplicate event_id in fixture.")
        logical[row["event_id"]]=payload
    knowledge=instant(parameters["recorded_cutoff"]);business=instant(parameters["effective_cutoff"])
    winners={};priorities={}
    for row in logical.values():
        priority=(instant(row["effective_at"]),instant(row["recorded_at"]),row["revision"],row["source_seq"])
        identity=(row["order_id"],priority)
        if identity in priorities and priorities[identity]!=row["event_id"]:
            raise ValueError("Unresolved logical-event precedence tie in fixture.")
        priorities[identity]=row["event_id"]
        if priority[0]<=business and priority[1]<=knowledge:
            order=row["order_id"]
            if order not in winners or priority>winners[order][0]:
                winners[order]=(priority,row)
    return sorted(tuple(row[column] for column in COLUMNS)
                  for _,row in winners.values() if row["operation"]=="UPSERT")
