"""Synthetic tenant/book scope collisions and cancellation goldens."""
import json
from pathlib import Path
import random

ROOT=Path(__file__).resolve().parents[1]


def ts(hour):return f"2026-10-30T{hour:02}:00:00Z"


def event(version,tenant="T1",book="B1",order="A",effective=8,recorded=8,qty=10,key="K",op="UPSERT"):
    return dict(version_id=version,tenant_id=tenant,book_id=book,order_id=order,effective_at=ts(effective),recorded_at=ts(recorded),operation=op,cancellation_key=key,symbol="XYZ",side="BUY",open_qty=qty,limit_price_cents=100)


def cancel(identifier,tenant="T1",book="B1",key="K",effective=9,recorded=9):
    return dict(cancel_id=identifier,tenant_id=tenant,book_id=book,cancellation_key=key,effective_at=ts(effective),recorded_at=ts(recorded))


def build():
    cases=[]
    def add(name,rows,cancels,expected,t=10,k=12):
        cases.append(dict(name=name,parameters=dict(effective_cutoff=ts(t),recorded_cutoff=ts(k)),tables={"order_versions":rows,"cancellations":cancels},expected=expected))
    out=lambda tenant="T1",book="B1",order="A",qty=10:[tenant,book,order,"XYZ","BUY",qty,100]
    add("empty",[],[],[])
    add("same_order_across_tenants",[event(1),event(2,tenant="T2",effective=9,qty=20)],[],[out(),out("T2",qty=20)])
    add("same_order_across_books",[event(1),event(2,book="B2",effective=9,qty=20)],[],[out(),out(book="B2",qty=20)])
    add("cancel_key_collision_tenant",[event(1),event(2,tenant="T2",qty=20)],[cancel(1)],[out("T2",qty=20)])
    add("cancel_key_collision_book",[event(1),event(2,book="B2",qty=20)],[cancel(1)],[out(book="B2",qty=20)])
    add("cancel_other_key",[event(1)],[cancel(1,key="OTHER")],[out()])
    add("future_cancellation",[event(1)],[cancel(1,effective=11)],[out()])
    add("unknown_cancellation",[event(1)],[cancel(1,recorded=13)],[out()])
    add("cancel_exact_boundaries",[event(1)],[cancel(1,effective=10,recorded=12)],[])
    add("current_key_replaced",[event(1,key="OLD"),event(2,effective=9,recorded=9,qty=4,key="NEW")],[cancel(1,key="OLD")],[out(qty=4)])
    add("cancel_current_no_older_fallback",[event(1,key="OLD"),event(2,effective=9,recorded=9,qty=4,key="NEW")],[cancel(1,key="NEW")],[])
    add("group_cancels_all_current_members",[event(1),event(2,order="B",qty=20)],[cancel(1)],[])
    add("repeated_cancels_no_multiplication",[event(1),event(2,order="B",key="OTHER",qty=20)],[cancel(1),cancel(2)],[out(order="B",qty=20)])
    add("delete_scoped_by_book",[event(1),event(2,effective=9,recorded=9,op="DELETE"),event(3,book="B2",qty=20)],[],[out(book="B2",qty=20)])
    add("zero_active_survives",[event(1,qty=0)],[],[out(qty=0)])
    add("case_sensitive_scope",[event(1),event(2,tenant="t1",qty=20)],[cancel(1)],[out("t1",qty=20)])
    for seed in range(16):
        rng=random.Random(8500+seed);rows=[];cancels=[];identifier=1
        for tenant,book in [("T1","B1"),("T1","B2"),("T2","B1"),("T2","B2")]:
            for order in ["A","B"]:
                seen=set()
                for _ in range(4):
                    while True:
                        pair=(rng.randrange(7,14),rng.randrange(7,15))
                        if pair not in seen:seen.add(pair);break
                    rows.append(event(identifier,tenant,book,order,*pair,qty=rng.randrange(0,100),key=rng.choice(["K1","K2","K3"]),op=rng.choice(["UPSERT","UPSERT","DELETE"])));identifier+=1
            for _ in range(3):
                cancels.append(cancel(len(cancels)+1,tenant,book,rng.choice(["K1","K2","K3"]),rng.randrange(7,14),rng.randrange(7,15)))
        rng.shuffle(rows)
        cases.append(dict(name=f"seed_{8500+seed}",parameters=dict(effective_cutoff=ts(rng.choice([8,10,13])),recorded_cutoff=ts(rng.choice([9,12,14]))),tables={"order_versions":rows,"cancellations":cancels}))
    directory=ROOT/"tasks/t05/fixtures";directory.mkdir(exist_ok=True)
    (directory/"cases.json").write_text(json.dumps(cases,indent=2)+"\n")
    metadata=dict(id="t05",title="Tenant/book identity and current cancellation scope",status="implemented_pending_human_review",output_columns=["tenant_id","book_id","order_id","symbol","side","open_qty","limit_price_cents"],output_types=["text","text","text","text","text","integer","integer"],fixture_files=["fixtures/cases.json"],failure_hypothesis="Models may preserve order identity in a window but drop part of tenant/book identity in cancellation joins, or cancel obsolete rather than current state keys.")
    (ROOT/"tasks/t05/metadata.json").write_text(json.dumps(metadata,indent=2)+"\n")


if __name__=="__main__":build()
