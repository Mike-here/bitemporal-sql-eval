"""Composite reporting fixtures with independently supplied simple expected totals."""
import json
from pathlib import Path
import random

ROOT=Path(__file__).resolve().parents[1]


def ts(hour):return f"2026-10-30T{hour:02}:00:00Z"


def event(ingest,event_id,tenant="T1",book="B1",order="A",amendment=1,effective=8,recorded=8,revision=0,sequence=1,qty=3,price=100,side="BUY",op="UPSERT"):
    return dict(ingest_id=ingest,event_id=event_id,tenant_id=tenant,book_id=book,order_id=order,amendment_no=amendment,effective_at=ts(effective),recorded_at=ts(recorded),revision=revision,source_seq=sequence,operation=op,side=side,open_qty=qty,limit_price_cents=price)


def build():
    cases=[]
    roster=[("T1","B1")]
    def add(name,rows,expected,books=roster,t=10,k=12):
        cases.append(dict(name=name,parameters=dict(effective_cutoff=ts(t),recorded_cutoff=ts(k)),tables={"reporting_books":[dict(tenant_id=tenant,book_id=book) for tenant,book in books],"order_versions":rows},expected=expected))
    add("empty_roster",[],[],books=[])
    add("listed_tenants_without_orders",[],[["T1",0,0,0],["T2",0,0,0]],books=[("T1","B1"),("T1","B2"),("T2","B1")])
    add("single_buy",[event(1,"e1")],[["T1",1,3,300]])
    add("single_sell",[event(1,"e1",qty=4,price=150,side="SELL")],[["T1",1,-4,-600]])
    add("offset_is_not_empty",[event(1,"e1",order="A",qty=2),event(2,"e2",order="B",qty=2,price=120,side="SELL")],[["T1",2,0,-40]])
    add("zero_quantity_still_active",[event(1,"e1",qty=0)],[["T1",1,0,0]])
    add("withdrawn_order_empty_tenant",[event(1,"e1"),event(2,"e2",amendment=2,effective=9,recorded=9,op="DELETE",qty=999)],[["T1",0,0,0]])
    add("unknown_delete",[event(1,"e1"),event(2,"e2",amendment=2,effective=9,recorded=13,op="DELETE",qty=999)],[["T1",1,3,300]])
    add("unknown_retro_revision",[event(1,"e1"),event(2,"e2",effective=8,recorded=13,qty=999)],[["T1",1,3,300]])
    add("known_revision_moves_out",[event(1,"e1"),event(2,"e2",amendment=2,effective=9,recorded=9,qty=8),event(3,"e3",amendment=2,effective=11,recorded=10,qty=12)],[["T1",1,3,300]])
    first=event(1,"e1")
    add("duplicate_delivery_no_double_count",[first,{**first,"ingest_id":99}],[["T1",1,3,300]])
    add("revision_counter_tie",[event(1,"e1",revision=1,sequence=99),event(2,"e2",revision=2,sequence=1,qty=5)],[["T1",1,5,500]])
    add("source_sequence_tie",[event(1,"e1",revision=2,sequence=2),event(2,"e2",revision=2,sequence=10,qty=4)],[["T1",1,4,400]])
    add("composite_order_identity",[event(1,"e1"),event(2,"e2",book="B2",qty=5),event(3,"e3",tenant="T2",qty=7)],[["T1",2,8,800],["T2",1,7,700]],books=[("T1","B1"),("T1","B2"),("T2","B1")])
    add("unlisted_book_is_excluded",[event(1,"e1",book="B9",qty=100)],[["T1",0,0,0]])
    add("inclusive_cutoffs",[event(1,"e1",effective=10,recorded=12,qty=2)],[["T1",1,2,200]])
    add("old_amendment_arrives_later",[event(1,"e1",effective=8,recorded=11,qty=99),event(2,"e2",amendment=2,effective=9,recorded=9,qty=4)],[["T1",1,4,400]])
    add("amendment_priority_not_arrival_priority",[event(1,"e1",effective=9,recorded=11,qty=99),event(2,"e2",amendment=2,effective=9,recorded=9,qty=4)],[["T1",1,4,400]])
    add("recorded_clock_beats_revision",[event(1,"e1",recorded=8,revision=99,qty=99),event(2,"e2",recorded=9,revision=0,qty=4)],[["T1",1,4,400]])
    for seed in range(16):
        rng=random.Random(9600+seed);rows=[];ingest=1
        books=[("T1","B1"),("T1","B2"),("T2","B1"),("EMPTY","B1")]
        for tenant,book in [("T1","B1"),("T1","B2"),("T2","B1"),("T1","UNLISTED")]:
            for order in ["A","B"]:
                for amendment in [1,2,3]:
                    for source in range(3):
                        row=event(ingest,f"S{seed}-{ingest}",tenant,book,order,amendment,effective=rng.randrange(7,14),recorded=rng.randrange(7,15),revision=rng.choice([0,2,10]),sequence=source,qty=rng.randrange(0,21),price=rng.randrange(0,1001),side=rng.choice(["BUY","SELL"]),op=rng.choice(["UPSERT","UPSERT","DELETE"]))
                        rows.append(row);ingest+=1
                        if rng.randrange(3)==0:rows.append({**row,"ingest_id":ingest});ingest+=1
        rng.shuffle(rows)
        cases.append(dict(name=f"seed_{9600+seed}",parameters=dict(effective_cutoff=ts(rng.choice([8,10,13])),recorded_cutoff=ts(rng.choice([9,12,14]))),tables={"reporting_books":[dict(tenant_id=tenant,book_id=book) for tenant,book in books],"order_versions":rows}))
    directory=ROOT/"tasks/t06/fixtures";directory.mkdir(exist_ok=True)
    (directory/"cases.json").write_text(json.dumps(cases,indent=2)+"\n")
    metadata=dict(id="t06",title="Scoped historical net aggregation with restatements",status="implemented_pending_human_review",output_columns=["tenant_id","active_order_count","net_qty","net_notional_cents"],output_types=["text","integer","integer","integer"],fixture_files=["fixtures/cases.json"],failure_hypothesis="Models may aggregate deliveries or obsolete revisions instead of the reconstructed order snapshot, lose scoped identity, or omit listed tenants with empty/zero exposure.")
    (ROOT/"tasks/t06/metadata.json").write_text(json.dumps(metadata,indent=2)+"\n")


if __name__=="__main__":build()
