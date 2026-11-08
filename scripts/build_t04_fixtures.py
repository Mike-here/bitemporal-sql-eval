"""Generate exact-clock tie and duplicate-delivery fixtures with explicit goldens."""
import json
from pathlib import Path
import random

ROOT=Path(__file__).resolve().parents[1]


def ts(hour):return f"2026-10-30T{hour:02}:00:00Z"


def event(ingest,event_id,order="A",effective=9,recorded=9,revision=0,sequence=1,qty=10,op="UPSERT"):
    return dict(ingest_id=ingest,event_id=event_id,order_id=order,effective_at=ts(effective),recorded_at=ts(recorded),revision=revision,source_seq=sequence,operation=op,symbol="XYZ",side="BUY",open_qty=qty,limit_price_cents=100)


def build():
    cases=[]
    def add(name,rows,expected,t=10,k=12):
        cases.append(dict(name=name,parameters=dict(effective_cutoff=ts(t),recorded_cutoff=ts(k)),tables={"order_versions":rows},expected=expected))
    out=lambda qty,order="A":[order,"XYZ","BUY",qty,100]
    duplicate=event(1,"e1")
    add("empty",[],[])
    add("duplicate_delivery_one_effect",[duplicate,{**duplicate,"ingest_id":99}],[out(10)])
    add("revision_wins_equal_clocks",[event(1,"e1",revision=1,sequence=90,qty=10),event(2,"e2",revision=2,sequence=1,qty=20)],[out(20)])
    add("source_sequence_breaks_revision_tie",[event(1,"e1",revision=2,sequence=2,qty=10),event(2,"e2",revision=2,sequence=10,qty=20)],[out(20)])
    add("revision_compared_numerically",[event(1,"e1",revision=2,qty=10),event(2,"e2",revision=10,qty=20)],[out(20)])
    add("business_time_beats_counter",[event(1,"e1",effective=8,revision=99,qty=99),event(2,"e2",effective=9,revision=0,qty=20)],[out(20)])
    add("knowledge_time_beats_counter",[event(1,"e1",recorded=8,revision=99,qty=99),event(2,"e2",recorded=9,revision=0,qty=20)],[out(20)])
    add("tie_resolves_to_delete",[event(1,"e1",revision=1),event(2,"e2",revision=2,op="DELETE",qty=999)],[])
    add("tie_reopens_delete",[event(1,"e1",revision=1,op="DELETE"),event(2,"e2",revision=2,qty=3)],[out(3)])
    add("unknown_high_counter",[event(1,"e1",recorded=9),event(2,"e2",recorded=13,revision=99,qty=999)],[out(10)])
    add("future_effective_high_counter",[event(1,"e1",effective=9),event(2,"e2",effective=11,revision=99,qty=999)],[out(10)])
    add("storage_order_not_priority",[event(900,"zzz",revision=1,qty=99),event(1,"aaa",revision=2,qty=20)],[out(20)])
    add("zero_is_reportable",[event(1,"e1",qty=0)],[out(0)])
    add("inclusive_clock_boundaries",[event(1,"e1",effective=10,recorded=12)],[out(10)])
    add("separate_orders_equal_clocks",[event(1,"e1",order="A",qty=10),event(2,"e2",order="B",qty=20)],[out(10),out(20,"B")])
    for seed in range(16):
        rng=random.Random(7400+seed);rows=[];ingest=1
        for order in range(4):
            for logical in range(6):
                row=event(ingest,f"S{seed}-{order}-{logical}",order=f"O{order}",effective=rng.randrange(7,14),recorded=rng.randrange(7,15),revision=rng.choice([0,2,10]),sequence=logical,qty=rng.randrange(0,100),op=rng.choice(["UPSERT","DELETE"]))
                rows.append(row);ingest+=1
                for _ in range(rng.randrange(0,3)):
                    rows.append({**row,"ingest_id":ingest});ingest+=1
        rng.shuffle(rows)
        cases.append(dict(name=f"seed_{7400+seed}",parameters=dict(effective_cutoff=ts(rng.choice([8,10,13])),recorded_cutoff=ts(rng.choice([9,12,14]))),tables={"order_versions":rows}))
    directory=ROOT/"tasks/t04/fixtures";directory.mkdir(exist_ok=True)
    (directory/"cases.json").write_text(json.dumps(cases,indent=2)+"\n")
    metadata=dict(id="t04",title="Source precedence and idempotent duplicate ingestion",status="implemented_pending_human_review",output_columns=["order_id","symbol","side","open_qty","limit_price_cents"],output_types=["text","text","text","integer","integer"],fixture_files=["fixtures/cases.json"],failure_hypothesis="Models may conflate storage order with source precedence or count repeated deliveries as independent states when timestamps tie.")
    (ROOT/"tasks/t04/metadata.json").write_text(json.dumps(metadata,indent=2)+"\n")


if __name__=="__main__":build()
