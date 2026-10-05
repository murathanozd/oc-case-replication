"""Regenerate results/r2/ from the raw CSV:  python -m r2_python.run_all"""

from __future__ import annotations

import json
from pathlib import Path

from .behaviour import directly_follows, global_end_events, global_start_events
from .executions import case_record, def8_violations, object_start_end
from .oced import load_csv, natkey

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "running_example" / "order_process_event_table_orderhandling.csv"
OUT = ROOT / "results" / "r2"


def write_json(name: str, obj) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / f"{name}.json", "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def sorted_ev(evs):
    return sorted(evs, key=natkey)


def main() -> None:
    d = load_csv(DATA)
    df = directly_follows(d, ties="strict")

    # Step 1-2: basic facts of the OCED-set
    write_json("oced_stats", {
        "events": len(d.events), "objects": len(d.objects), "corr": len(d.corr),
        "rel_ordered_pairs": len(d.rel), "rel_unordered_pairs": len({frozenset(p) for p in d.rel}),
        "df_triples": len(df.triples),
        "global_start_events": sorted_ev(global_start_events(d, df)),
        "global_end_events": sorted_ev(global_end_events(d, df)),
        "def8_violations": def8_violations(d, df),
    })
    write_json("object_start_end", [
        {"object": o, "type": d.type[o], "start_events": sorted_ev(s), "end_events": sorted_ev(t)}
        for o, (s, t) in sorted(object_start_end(d, df).items(), key=lambda kv: (d.type[kv[0]], natkey(kv[0])))
    ])

    # Step 3: Def. 8 case D[A -> O1] (= D[e3 -> e28], Fig. 5)
    write_json("exec_A_O1", [case_record(d, df, "A", "O1")])
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
