"""Explicit restatement goldens plus deterministic amendment-revision histories."""
import json
from pathlib import Path
import random

ROOT=Path(__file__).resolve().parents[1]


def ts(hour): return f"2026-10-30T{hour:02}:00:00Z"


def event(record,order,amendment,effective,recorded,qty=10):
    return dict(record_id=record,order_id=order,amendment_no=amendment,effective_at=ts(effective),
                recorded_at=ts(recorded),symbol="XYZ",side="BUY",open_qty=qty,limit_price_cents=100)


def build():
    cases=[]
    def add(name,rows,expected,t=10,k=12):
        cases.append(dict(name=name,parameters=dict(effective_cutoff=ts(t),recorded_cutoff=ts(k)),tables={"order_versions":rows},expected=expected))
    out=lambda order,qty:[order,"XYZ","BUY",qty,100]
    add("empty",[],[])
    add("simple_amendment",[event(1,"A",1,8,8)],[out("A",10)])
    add("unknown_retro_correction",[event(1,"A",1,8,8,10),event(2,"A",1,8,13,99)],[out("A",10)])
    add("known_retro_correction",[event(1,"A",1,8,8,10),event(2,"A",1,8,11,12)],[out("A",12)])
    add("correction_moves_amendment_out",[event(1,"A",1,7,7,5),event(2,"A",2,9,9,20),event(3,"A",2,11,10,30)],[out("A",5)])
    add("only_amendment_moves_out",[event(1,"A",1,8,8,10),event(2,"A",1,11,10,12)],[])
    add("correction_moves_amendment_in",[event(1,"A",1,11,8,10),event(2,"A",1,9,11,12)],[out("A",12)])
    add("unknown_move_out_keeps_old_meaning",[event(1,"A",1,8,8,10),event(2,"A",1,11,13,99)],[out("A",10)])
    add("old_amendment_arrives_later",[event(1,"A",1,8,8,10),event(2,"A",1,8,11,12),event(3,"A",2,9,9,20)],[out("A",20)])
    add("equal_effective_amendment_priority",[event(9,"A",1,9,11,10),event(1,"A",2,9,9,20)],[out("A",20)])
    add("inclusive_both_boundaries",[event(1,"A",1,10,12,0)],[out("A",0)])
    add("amendment_numbers_scoped_by_order",[event(1,"A",1,8,8,10),event(2,"B",1,8,9,20)],[out("A",10),out("B",20)])
    add("knowledge_before_business",[event(1,"A",1,8,8,10),event(2,"A",1,9,11,20),event(3,"B",1,10,8,4)],[out("A",10),out("B",4)],k=9)
    for seed in range(16):
        rng=random.Random(6300+seed); rows=[]; identity=1
        for order in range(4):
            for amendment in range(1,4):
                for recorded in rng.sample(range(7,16),3):
                    rows.append(event(identity,f"S{seed}-{order}",amendment,rng.randrange(7,15),recorded,rng.randrange(0,100)))
                    identity+=1
        rng.shuffle(rows)
        cases.append(dict(name=f"seed_{6300+seed}",parameters=dict(effective_cutoff=ts(rng.choice([8,10,13])),recorded_cutoff=ts(rng.choice([8,12,15]))),tables={"order_versions":rows}))
    directory=ROOT/"tasks/t03/fixtures";directory.mkdir(exist_ok=True)
    (directory/"cases.json").write_text(json.dumps(cases,indent=2)+"\n")
    metadata=dict(id="t03",title="Historical restatement of amendment identity",status="implemented_pending_human_review",output_columns=["order_id","symbol","side","open_qty","limit_price_cents"],output_types=["text","text","text","integer","integer"],fixture_files=["fixtures/cases.json"],failure_hypothesis="Models may treat superseded amendment revisions as independent effective events or let later knowledge leak into earlier reports.")
    (ROOT/"tasks/t03/metadata.json").write_text(json.dumps(metadata,indent=2)+"\n")


if __name__=="__main__":build()
