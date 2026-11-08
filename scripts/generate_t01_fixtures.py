"""Regenerate synthetic t01 fixtures; no oracle is used for manual goldens.

Do not regenerate or modify fixtures during a formal run. Their hashes are logged.
"""

from datetime import datetime, timedelta
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]


def ts(clock):
    return f"2026-10-30T{clock}:00Z"


def row(version_id, order_id, effective, recorded, qty, price=12345, symbol="XYZ", side="BUY"):
    return dict(version_id=version_id, order_id=order_id, effective_at=ts(effective),
                recorded_at=ts(recorded), symbol=symbol, side=side,
                open_qty=qty, limit_price_cents=price)


def case(name, rationale, rows, expected, effective="10:00", recorded="12:00"):
    return dict(name=name, rationale=rationale,
                parameters=dict(effective_cutoff=ts(effective), recorded_cutoff=ts(recorded)),
                rows=rows, expected=expected)


def manual_cases():
    # Expected arrays are deliberately supplied independently, not copied from
    # either the SQL solution or Python oracle. Participant audit remains pending.
    return [
        case("empty", "Empty history returns an empty relation with the required columns.", [], []),
        case("single_state", "Straightforward baseline.",
             [row(4, "A", "08:00", "08:05", 10)], [["A", "XYZ", "BUY", 10, 12345]]),
        case("inclusive_both_boundaries", "Both exact boundaries must be included.",
             [row(1, "A", "10:00", "12:00", 17)], [["A", "XYZ", "BUY", 17, 12345]]),
        case("exclude_future_effective", "A recorded scheduled amendment is not yet effective.",
             [row(1, "A", "08:00", "08:00", 10), row(2, "A", "10:01", "09:00", 99)],
             [["A", "XYZ", "BUY", 10, 12345]]),
        case("exclude_future_recorded", "An effective amendment not yet known cannot affect this report.",
             [row(1, "A", "08:00", "08:00", 10), row(2, "A", "09:00", "12:01", 99)],
             [["A", "XYZ", "BUY", 10, 12345]]),
        case("late_correction_same_effective", "Exclude an invisible correction without losing the visible same-time version.",
             [row(3, "A", "09:00", "12:01", 900), row(2, "A", "09:00", "11:00", 12),
              row(1, "A", "08:00", "08:00", 10)], [["A", "XYZ", "BUY", 12, 12345]]),
        case("effective_precedes_recorded", "A later arrival correcting an older state cannot overwrite a later effective state.",
             [row(7, "A", "08:00", "11:30", 88), row(3, "A", "09:00", "09:15", 20),
              row(9, "A", "08:00", "08:10", 10)], [["A", "XYZ", "BUY", 20, 12345]]),
        case("same_effective_latest_correction", "Recorded time breaks a tie on effective time.",
             [row(8, "A", "09:00", "09:10", 20), row(2, "A", "09:00", "11:00", 25)],
             [["A", "XYZ", "BUY", 25, 12345]]),
        case("eligibility_before_ranking", "Ranking the complete history then filtering can omit an order incorrectly.",
             [row(1, "A", "08:00", "08:00", 10), row(2, "A", "11:00", "11:00", 99)],
             [["A", "XYZ", "BUY", 10, 12345]]),
        case("keep_zero_quantity", "A zero quantity is a retained state, not a deletion.",
             [row(1, "A", "08:00", "08:00", 10), row(2, "A", "09:00", "09:00", 0, 0)],
             [["A", "XYZ", "BUY", 0, 0]]),
        case("orders_without_eligible_state", "Omit only ineligible orders; do not add fabricated zero rows.",
             [row(1, "A", "08:00", "08:00", 10), row(2, "B", "11:00", "09:00", 22),
              row(3, "C", "08:00", "13:00", 33), row(4, "D", "07:00", "08:00", 5, 9800, "ABC", "SELL")],
             [["A", "XYZ", "BUY", 10, 12345], ["D", "ABC", "SELL", 5, 9800]]),
        case("storage_id_is_not_precedence", "Storage IDs and row insertion order are unrelated to state chronology.",
             [row(1, "A", "09:00", "10:00", 25), row(900, "A", "08:00", "11:00", 100),
              row(700, "A", "09:00", "09:00", 20)], [["A", "XYZ", "BUY", 25, 12345]]),
        case("preserve_whole_winning_row", "Independent MAX operations cannot synthesize a winning state.",
             [row(1, "A", "08:00", "11:00", 90, 99999, "OLD", "SELL"),
              row(2, "A", "09:00", "09:00", 12, 12000, "NEW", "SELL"),
              row(3, "A", "09:00", "10:00", 4, 11000, "NEW", "BUY")],
             [["A", "NEW", "BUY", 4, 11000]]),
        case("knowledge_cutoff_before_effective_cutoff", "The two cutoffs have different roles even when K < T.",
             [row(1, "A", "08:00", "08:00", 10), row(2, "A", "09:30", "08:30", 15),
              row(3, "A", "09:00", "09:30", 20)],
             [["A", "XYZ", "BUY", 15, 12345]], recorded="09:00"),
        case("no_eligible_versions", "Nonempty input can have an empty snapshot.",
             [row(1, "A", "11:00", "09:00", 10), row(2, "B", "08:00", "13:00", 20)], []),
        case("case_sensitive_entity_ids", "Distinct case-sensitive identifiers remain distinct orders.",
             [row(1, "ord-a", "08:00", "08:00", 4), row(2, "ORD-A", "09:00", "09:00", 7)],
             [["ORD-A", "XYZ", "BUY", 7, 12345], ["ord-a", "XYZ", "BUY", 4, 12345]]),
    ]


def generated_cases():
    result = []
    origin = datetime(2026, 10, 30, 8)
    stamp = lambda seconds: (origin + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for seed in range(24):
        rng = random.Random(4300 + seed)
        rows = []
        ids = rng.sample(range(1, 10000), 30)
        for entity in range(6):
            seen = set()
            for version in range(5):
                while True:
                    effective = rng.choice([0, 1800, 3600, 5400, 7200, 9000])
                    recorded = rng.randrange(0, 18001)
                    if (effective, recorded) not in seen:
                        seen.add((effective, recorded))
                        break
                rows.append(dict(version_id=ids[entity * 5 + version],
                                 order_id=f"order-{seed}-{entity}", effective_at=stamp(effective),
                                 recorded_at=stamp(recorded), symbol=f"SYM{entity}",
                                 side=rng.choice(["BUY", "SELL"]), open_qty=rng.randrange(0, 101),
                                 limit_price_cents=rng.randrange(1, 50001)))
        rng.shuffle(rows)
        result.append(dict(name=f"seed_{4300 + seed}", generator_seed=4300 + seed,
                           rationale="Reproducible mixed histories and independent cutoff pairs; oracle-computed outcome.",
                           parameters=dict(effective_cutoff=stamp(rng.choice([0, 3600, 7200, 10800])),
                                           recorded_cutoff=stamp(rng.choice([0, 3600, 10800, 18000]))),
                           rows=rows))
    return result


if __name__ == "__main__":
    directory = ROOT / "tasks/t01/fixtures"
    directory.mkdir(parents=True, exist_ok=True)
    for name, cases in [("hand_cases", manual_cases()), ("generated_cases", generated_cases())]:
        (directory / f"{name}.json").write_text(json.dumps(cases, indent=2) + "\n")
    print("Wrote 16 explicit golden fixtures and 24 seeded histories.")
