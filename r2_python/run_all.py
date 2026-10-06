"""Regenerate results/r2/ from the raw CSV:  python -m r2_python.run_all"""

from __future__ import annotations

import json
from pathlib import Path

from .behaviour import directly_follows, global_end_events, global_start_events
from .case_notions import (GLOBAL_BY, behaviour, case_notion, global_executions,
                           global_objects, type_matrix)
from .executions import case_record, def8_violations, object_start_end
from .generalized import boundary_objects, excluded_objects, type_records
from .oced import load_csv, natkey
from .projection_check import report as projection_report

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

    # Step 4: Def. 9 case notions (A3: self_pairs) and the Sect. 5.2 global restriction (A4)
    sp_name = {True: "selfpairs", False: "noselfpairs"}
    notions = [("SO_Order", "Supplier Order", "Order"), ("Order_Payment", "Order", "Payment"),
               ("Order_Invoice", "Order", "Invoice"), ("Payment_Invoice", "Payment", "Invoice"),
               ("Order_Order", "Order", "Order")]
    summary = {"notions": {}, "global": {}}
    for name, t_st, t_end in notions:
        for sp in (True, False):
            recs = case_notion(d, df, t_st, t_end, self_pairs=sp)
            write_json(f"notion_{name}__{sp_name[sp]}", recs)
            pairs = [(r["start_object"], r["end_object"]) for r in recs]
            summary["notions"][f"{name}__{sp_name[sp]}"] = {
                "cases": len(recs), "case_ids": [r["execution_id"] for r in recs],
                "behaviour_events": sorted_ev(behaviour(d, df, pairs).events)}
    for by in GLOBAL_BY:
        st, en = global_objects(d, df, by)
        summary["global"][f"by_{by}"] = {"start_objects": st, "end_objects": en}
        for sp in (True, False):
            recs = global_executions(d, df, by, self_pairs=sp)
            write_json(f"all_global_executions__by_{by}__{sp_name[sp]}", recs)
            summary["global"][f"by_{by}"][sp_name[sp]] = {
                "executions": len(recs), "per_type_pair": type_matrix(d, recs)}
    recs = global_executions(d, df, "object", self_pairs=False, distinct_types=True)
    write_json("all_global_executions__by_object__distinct_types", recs)
    summary["global"]["by_object"]["distinct_types"] = {
        "executions": len(recs), "per_type_pair": type_matrix(d, recs)}
    summary["global"]["by_object_equals_by_type"] = all(
        global_executions(d, df, "object", sp) == global_executions(d, df, "type", sp) for sp in (True, False))
    # plain Def. 9 (no Sect. 5.2 restriction) for every pair of object types, without self-pairs
    all_types = sorted({d.type[o] for o in d.objects})
    summary["def9_all_type_pairs__noselfpairs"] = {
        f"{a} -> {b}": [r["execution_id"] for r in case_notion(d, df, a, b, self_pairs=False)]
        for a in all_types for b in all_types}
    write_json("case_notions_summary", summary)

    # Step 5: Def. 10 start/end cases of Orders ("global" = Def. 10, "any" = every object's end/start
    # event), unfiltered and filtered by X = Supplier Order objects (Def. 11, A5: global_on full/filtered)
    X = excluded_objects(d, types=["Supplier Order"])
    gsum = {"X": sorted(X, key=natkey), "boundary_objects": {}, "cases": {}}
    for side in ("start", "end"):
        other = "end" if side == "start" else "start"
        for variant in ("global", "any"):
            recs = type_records(d, df, side, "Order", variant=variant)
            write_json(f"{side}_case_Order__{variant}", recs)
            gsum["cases"][f"{side}_case_Order__{variant}"] = {r["execution_id"]: r["events"] for r in recs}
        for variant, go in (("global", "full"), ("global", "filtered"), ("any", "full")):
            name = f"{side}_case_Order_noSO__{variant}" + (f"_{go}" if variant == "global" else "")
            recs = type_records(d, df, side, "Order", variant=variant, X=X, global_on=go)
            write_json(name, recs)
            gsum["cases"][name] = {r["execution_id"]: r["events"] for r in recs}
        for go in ("full", "filtered"):
            gsum["boundary_objects"][f"O_{other}__global_{go}"] = boundary_objects(d, df, other, "global", X, go)
    c = gsum["cases"]
    gsum["comparisons"] = {
        "start_case_Order: global == any": c["start_case_Order__global"] == c["start_case_Order__any"],
        "end_case_Order: global == any": c["end_case_Order__global"] == c["end_case_Order__any"],
        "start_case_Order_noSO: global_full == global_filtered":
            c["start_case_Order_noSO__global_full"] == c["start_case_Order_noSO__global_filtered"],
        "start_case_Order_noSO: global_full == any":
            c["start_case_Order_noSO__global_full"] == c["start_case_Order_noSO__any"],
        "end_case_Order_noSO: global_full == global_filtered":
            c["end_case_Order_noSO__global_full"] == c["end_case_Order_noSO__global_filtered"],
        "end_case_Order_noSO: global_filtered == any":
            c["end_case_Order_noSO__global_filtered"] == c["end_case_Order_noSO__any"],
    }
    write_json("generalized_summary", gsum)

    # Projection check (F6): convexity of Def. 7 vs. Def. 11
    with open(OUT / "projection_check.md", "w", encoding="utf-8") as f:
        f.write(projection_report(d, df, X))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
