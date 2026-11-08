"""Synthetic t02 histories; explicit golden outcomes are independent of the oracle."""
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]


def stamp(hour):
    return f"2026-10-30T{hour:02}:00:00Z"


def event(version, order, effective, recorded, qty=10, op="UPSERT"):
    return dict(version_id=version, order_id=order, effective_at=stamp(effective),
                recorded_at=stamp(recorded), operation=op, symbol="XYZ", side="BUY",
                open_qty=qty, limit_price_cents=100)


def build():
    cases = []
    def add(name, rows, expected, t=10, k=12):
        cases.append(dict(name=name, parameters=dict(effective_cutoff=stamp(t), recorded_cutoff=stamp(k)),
                          tables={"order_versions": rows}, expected=expected))
    out = lambda order, qty: [order, "XYZ", "BUY", qty, 100]
    add("empty", [], [])
    add("single_active", [event(1,"A",8,8)], [out("A",10)])
    add("visible_withdrawal", [event(1,"A",8,8),event(2,"A",9,9,99,"DELETE")], [])
    add("unknown_withdrawal", [event(1,"A",8,8),event(2,"A",9,13,99,"DELETE")], [out("A",10)])
    add("future_withdrawal", [event(1,"A",8,8),event(2,"A",11,9,99,"DELETE")], [out("A",10)])
    add("exact_boundary_withdrawal", [event(1,"A",8,8),event(2,"A",10,12,99,"DELETE")], [])
    add("reopen_after_delete", [event(9,"A",7,7),event(8,"A",8,8,99,"DELETE"),event(1,"A",9,9,3)], [out("A",3)])
    add("same_time_corrected_to_delete", [event(1,"A",9,9),event(2,"A",9,11,99,"DELETE")], [])
    add("same_time_delete_corrected_to_active", [event(1,"A",9,9,99,"DELETE"),event(2,"A",9,11,4)], [out("A",4)])
    add("old_state_late_delete", [event(1,"A",8,11,99,"DELETE"),event(2,"A",9,9,4)], [out("A",4)])
    add("zero_is_not_delete", [event(1,"A",8,8),event(2,"A",9,9,0)], [out("A",0)])
    add("mixed_orders", [event(1,"A",8,8),event(2,"A",9,9,99,"DELETE"),event(3,"B",8,8,6)], [out("B",6)])
    for seed in range(16):
        rng = random.Random(5200+seed)
        rows=[]
        for order in range(4):
            seen=set()
            for version in range(5):
                while True:
                    pair=(rng.randrange(7,14),rng.randrange(7,15))
                    if pair not in seen:
                        seen.add(pair); break
                rows.append(event(order*10+version+1,f"S{seed}-{order}",*pair,rng.randrange(0,20),rng.choice(["UPSERT","DELETE"])))
        rng.shuffle(rows)
        cases.append(dict(name=f"seed_{5200+seed}", parameters=dict(effective_cutoff=stamp(rng.choice([8,10,12])),recorded_cutoff=stamp(rng.choice([9,12,14]))),tables={"order_versions":rows}))
    directory=ROOT/"tasks/t02/fixtures"; directory.mkdir(exist_ok=True)
    (directory/"cases.json").write_text(json.dumps(cases,indent=2)+"\n")
    metadata=dict(id="t02",title="Withdrawal state and reopening",status="implemented_pending_human_review",output_columns=["order_id","symbol","side","open_qty","limit_price_cents"],output_types=["text","text","text","integer","integer"],fixture_files=["fixtures/cases.json"],failure_hypothesis="Dropping withdrawal versions before determining current state resurrects superseded orders.")
    (ROOT/"tasks/t02/metadata.json").write_text(json.dumps(metadata,indent=2)+"\n")


if __name__=="__main__":
    build()
