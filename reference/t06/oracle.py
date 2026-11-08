"""Independent staged Python reconstruction and arbitrary-precision aggregation."""
from datetime import datetime


def solve(tables,parameters):
    instant=lambda text:datetime.strptime(text,"%Y-%m-%dT%H:%M:%SZ")
    business=instant(parameters["effective_cutoff"]);knowledge=instant(parameters["recorded_cutoff"])
    books={(row["tenant_id"],row["book_id"]) for row in tables["reporting_books"]}
    totals={tenant:[0,0,0] for tenant,_ in books}
    events={}
    for row in tables["order_versions"]:
        payload={key:value for key,value in row.items() if key!="ingest_id"}
        if row["event_id"] in events and events[row["event_id"]]!=payload:
            raise ValueError("Conflicting event copies in fixture.")
        events[row["event_id"]]=payload
    meanings={};priorities={}
    for row in events.values():
        order=(row["tenant_id"],row["book_id"],row["order_id"])
        amendment=(*order,row["amendment_no"])
        priority=(instant(row["recorded_at"]),row["revision"],row["source_seq"])
        identity=(amendment,priority)
        if identity in priorities and priorities[identity]!=row["event_id"]:
            raise ValueError("Unresolved amendment revision tie in fixture.")
        priorities[identity]=row["event_id"]
        if priority[0]<=knowledge and (amendment not in meanings or priority>meanings[amendment][0]):
            meanings[amendment]=(priority,row)
    state={}
    for _,row in meanings.values():
        effective=instant(row["effective_at"])
        identity=(row["tenant_id"],row["book_id"],row["order_id"])
        priority=(effective,row["amendment_no"])
        if effective<=business and (identity not in state or priority>state[identity][0]):
            state[identity]=(priority,row)
    for _,row in state.values():
        if (row["tenant_id"],row["book_id"]) in books and row["operation"]=="UPSERT":
            values=totals[row["tenant_id"]];sign=1 if row["side"]=="BUY" else -1
            values[0]+=1;values[1]+=sign*row["open_qty"]
            values[2]+=sign*row["open_qty"]*row["limit_price_cents"]
    return [(tenant,*totals[tenant]) for tenant in sorted(totals)]
