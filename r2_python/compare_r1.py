"""Step 6: compare R2 with R1.  python -m r2_python.compare_r1  ->  results/r2/comparison.md

Reads results/r1/ (only here) and the R2 results written by run_all. Every R1 result file is mapped to the
R2 variant(s) that correspond to it. A difference without an entry in EXPLAIN is reported as "unexplained".
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .oced import natkey

ROOT = Path(__file__).resolve().parent.parent
R1 = ROOT / "results" / "r1"
R2 = ROOT / "results" / "r2"


def load(p: Path):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _ev(x):
    return sorted(x, key=natkey) if isinstance(x, list) else x


def compare_executions(r1: list[dict], r2: list[dict]) -> dict:
    """Match executions by execution_id (= start/end object) and compare events, objects, start/end events."""
    a = {r["execution_id"]: r for r in r1}
    b = {r["execution_id"]: r for r in r2}
    common = sorted(a.keys() & b.keys(), key=natkey)
    diff = lambda k: [i for i in common if _ev(a[i][k]) != _ev(b[i][k])]
    return {"only_r1": sorted(a.keys() - b.keys(), key=natkey), "only_r2": sorted(b.keys() - a.keys(), key=natkey),
            "events": diff("events"), "objects": diff("objects"),
            "start_end": sorted(set(diff("start_event")) | set(diff("end_event")), key=natkey),
            "a": a, "b": b}


def describe(c: dict) -> str:
    parts = []
    if c["only_r1"]:
        parts.append("only in R1: " + ", ".join(c["only_r1"]))
    if c["only_r2"]:
        parts.append("only in R2: " + ", ".join(c["only_r2"]))
    for i in c["events"]:
        x, y = set(c["a"][i]["events"]), set(c["b"][i]["events"])
        parts.append(f"{i} events: R1−R2 = {{{' '.join(sorted(x - y, key=natkey))}}}, "
                     f"R2−R1 = {{{' '.join(sorted(y - x, key=natkey))}}}")
    for i in c["objects"]:
        x, y = set(c["a"][i]["objects"]), set(c["b"][i]["objects"])
        parts.append(f"{i} objects: R1−R2 = {{{' '.join(sorted(x - y, key=natkey))}}}, "
                     f"R2−R1 = {{{' '.join(sorted(y - x, key=natkey))}}}")
    for i in c["start_end"]:
        for k in ("start_event", "end_event"):
            x, y = c["a"][i][k], c["b"][i][k]
            if _ev(x) != _ev(y):
                parts.append(f"{i} {k}: R1 {' '.join(_ev(x)) if isinstance(x, list) else x} / "
                             f"R2 {' '.join(_ev(y)) if isinstance(y, list) else y}")
    return "; ".join(parts)


# R1 file -> R2 variants (the first one is the variant that implements the same semantics as the R1 query)
EXEC_MAP = {
    "exec_A_O1.json": ["exec_A_O1"],
    "notion_SO_Order.json": ["notion_SO_Order__noselfpairs", "notion_SO_Order__selfpairs"],
    "notion_SO_Order_global.json": ["notion_SO_Order__noselfpairs"],
    "notion_SO_Order_paths.json": ["notion_SO_Order__noselfpairs"],
    "notion_SO_Order_paths_fixed.json": ["notion_SO_Order__noselfpairs"],
    "notion_Order_Payment.json": ["notion_Order_Payment__noselfpairs", "notion_Order_Payment__selfpairs"],
    "notion_Order_Invoice.json": ["notion_Order_Invoice__noselfpairs", "notion_Order_Invoice__selfpairs"],
    "notion_Payment_Invoice.json": ["notion_Payment_Invoice__noselfpairs", "notion_Payment_Invoice__selfpairs"],
    "notion_Order_Order.json": ["notion_Order_Order__noselfpairs", "notion_Order_Order__selfpairs"],
    "all_global_executions.json": ["all_global_executions__by_object__noselfpairs",
                                   "all_global_executions__by_type__noselfpairs",
                                   "all_global_executions__by_object__selfpairs",
                                   "all_global_executions__by_type__selfpairs",
                                   "all_global_executions__by_object__distinct_types"],
    "start_case_Order.json": ["start_case_Order__any", "start_case_Order__global"],
    "start_case_Order_noSO.json": ["start_case_Order_noSO__any", "start_case_Order_noSO__global_filtered",
                                   "start_case_Order_noSO__global_full"],
    "end_case_Order.json": ["end_case_Order__any", "end_case_Order__global"],
    "end_case_Order_noSO.json": ["end_case_Order_noSO__any", "end_case_Order_noSO__global_filtered",
                                "end_case_Order_noSO__global_full"],
}

A3 = ("A3 (self-pairs): Def. 9 allows o_st = o_end; the R1 query excludes it (`nEnd <> nStart`). "
      "R2 `selfpairs` = Def. 9 as written.")
A10 = ("Def. 10 \"global\" vs. \"any\" (R1 open point 1): Def. 10 takes the other end only from objects "
       "with a global {0} event; the R1 query accepts every :{1} event. Only the recorded {0} events differ; the "
       "event and object sets are the same, because every non-global {0} event used by R1 lies on a df-path "
       "{2} a global one inside the same case.")
EXPLAIN = {
    ("notion_SO_Order_paths.json", "notion_SO_Order__noselfpairs"):
        "Not an ambiguity: the published OCPM 3.1 §3.1 query has the typo `\"Order \"` (trailing space), "
        "so it matches no end object (R1 log). The fixed copy (`_paths_fixed`) is equal.",
    ("notion_Order_Order.json", "notion_Order_Order__selfpairs"): A3,
    ("all_global_executions.json", "all_global_executions__by_object__selfpairs"): A3,
    ("all_global_executions.json", "all_global_executions__by_type__selfpairs"): A3,
    ("all_global_executions.json", "all_global_executions__by_object__distinct_types"):
        "A3 (\"pairs of distinct object types\", Sect. 5.2, read literally): O2_O1 (Order→Order) is dropped. "
        "R1 keeps it.",
    ("start_case_Order.json", "start_case_Order__global"): A10.format("end", "END", "to"),
    ("end_case_Order.json", "end_case_Order__global"): A10.format("start", "START", "from"),
    ("end_case_Order_noSO.json", "end_case_Order_noSO__global_filtered"):
        A10.format("start", "START", "from") + " Under the A5 reading `global_on=filtered`.",
    ("end_case_Order_noSO.json", "end_case_Order_noSO__global_full"):
        "A5 (Def. 11, global start events before vs. after filtering): with `global_on=full` O_start = "
        "{A, B, O1, O2, P1}; A and B have no df-edges left after removing X, so only O1, O2 contribute and the "
        "cases shrink to the Orders' own filtered executions. R1's query (any :START event, filtered paths) "
        "corresponds to `any`, which equals `global_filtered` in events.",
    ("start_case_Order_noSO.json", "start_case_Order_noSO__global_filtered"):
        A10.format("end", "END", "to"),
    ("start_case_Order_noSO.json", "start_case_Order_noSO__global_full"):
        A10.format("end", "END", "to"),
}


def exec_rows(lines: list[str]) -> dict:
    stats = {"rows": 0, "unexplained": 0}
    for f1, variants in EXEC_MAP.items():
        r1 = load(R1 / f1)
        for v in variants:
            c = compare_executions(r1, load(R2 / f"{v}.json"))
            ex_eq = not c["only_r1"] and not c["only_r2"]
            yn = lambda b: "yes" if b else "**no**"
            d = describe(c)
            if d:
                exp = EXPLAIN.get((f1, v))
                if exp is None:
                    stats["unexplained"] += 1
                    exp = "**unexplained**"
                d = f"{d}. *Explained by:* {exp}"
            else:
                d = "–"
            n = f"{len(r1)} / {len(c['b'])}"
            lines.append(f"| `{f1}` | `{v}.json` | {yn(ex_eq)} ({n}) | {yn(not c['events'])} | "
                         f"{yn(not c['objects'])} | {yn(not c['start_end'])} | {d} |")
            stats["rows"] += 1
    return stats


def read_csv(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def structure_rows(lines: list[str]) -> dict:
    """R1 files that are not executions: EKG statistics, df-edges, rel-edges, start/end events, views."""
    stats = {"rows": 0, "unexplained": 0}
    r2s = load(R2 / "oced_stats.json")
    r2se = {r["object"]: r for r in load(R2 / "object_start_end.json")}

    def row(f1, v, eq, diff, exp=None):
        stats["rows"] += 1
        if not eq and exp is None:
            stats["unexplained"] += 1
            exp = "**unexplained**"
        text = "–" if eq else f"{diff}. *Explained by:* {exp}"
        lines.append(f"| `{f1}` | {v} | {'yes' if eq else '**no**'} | {text} |")

    e1 = load(R1 / "ekg_stats.json")
    got = (e1["events"], e1["entities"], e1["corr"], e1["df"])
    want = (r2s["events"], r2s["objects"], r2s["corr"], r2s["df_triples"])
    row("ekg_stats.json", "`oced_stats.json` (events, objects, corr, df)", got == want, f"R1 {got} / R2 {want}")

    # df edges
    r1df = {(r["e1"], r["object_id"], r["e2"]) for r in read_csv(R1 / "df_edges.csv")}
    from .behaviour import directly_follows
    from .oced import load_csv
    from .run_all import DATA
    d = load_csv(DATA)
    df = directly_follows(d)
    row("df_edges.csv", "DF triples (Def. 3, `ties=strict`), recomputed", r1df == set(df.triples),
        f"R1−R2 {sorted(r1df - df.triples)}, R2−R1 {sorted(df.triples - r1df)}")

    # rel edges
    r1rel = {frozenset((r["n1"], r["n2"])) for r in read_csv(R1 / "rel_edges.csv")}
    r2rel = {frozenset(p) for p in d.rel}
    extra = sorted((tuple(sorted(p, key=natkey)) for p in r2rel - r1rel), key=lambda t: (natkey(t[0]), natkey(t[1])))
    same_type = all(d.type[a] == d.type[b] for a, b in extra)
    row("rel_edges.csv", "`rel` (Def. 2, I1), as unordered pairs", r1rel == r2rel,
        f"R1 {len(r1rel)} pairs, R2 {len(r2rel)}; R1 ⊆ R2: {r1rel <= r2rel}; only in R2: "
        + ", ".join(f"{a}–{b}" for a, b in extra),
        "Sect. 3 rule / I1 vs. the tutorial's :REL query: R2 relates every two distinct objects of one event; "
        "the tutorial only relates objects of different types (all R2-only pairs are same-type: "
        f"{same_type}) and stores one direction. `rel` is not used by Def. 3–11, so no execution changes (F1)."
        if same_type and r1rel <= r2rel else None)
    m1 = load(R1 / "materialize_stats.json")
    row("materialize_stats.json", "`rel` pairs; objects with ≠ 1 start/end event",
        m1["rel_edges"] == len(r2rel) and not m1["objects_not_exactly_one_start_and_end"] and not r2s["def8_violations"],
        f"rel: R1 {m1['rel_edges']} / R2 {len(r2rel)}; ≠ 1 start/end: R1 {m1['objects_not_exactly_one_start_and_end']}"
        f" / R2 {list(r2s['def8_violations'])}",
        "rel as for `rel_edges.csv` (F1); start/end: equal (12 objects, none violating Def. 8)."
        if not m1["objects_not_exactly_one_start_and_end"] and not r2s["def8_violations"] else None)

    # start/end events per object
    se1 = {r["object"]: (r["type"], [r["start_event"]], [r["end_event"]]) for r in read_csv(R1 / "start_end.csv")}
    se2 = {o: (r["type"], r["start_events"], r["end_events"]) for o, r in r2se.items()}
    row("start_end.csv", "`object_start_end.json`", se1 == se2,
        "; ".join(f"{o}: R1 {se1.get(o)} / R2 {se2.get(o)}" for o in sorted(se1.keys() | se2.keys(), key=natkey)
                  if se1.get(o) != se2.get(o)))

    # view queries: DF edges of the returned subgraph vs. D's DF restricted to the R2 execution events
    from .executions import between
    for name, pairs in (("exec_A_O1_view", [("e3", "e28")]),
                        ("notion_SO_Order_view", [("e3", "e28"), ("e3", "e34"), ("e4", "e28"), ("e4", "e34")])):
        raw = load(R1 / "raw" / f"{name}.json")
        r1e = {(r["df"]["from"], r["df"]["ID"], r["df"]["to"]) for r in raw["rows"]}
        evs = set().union(*(between(df, i, o) for i, o in pairs))
        r2e = {t for t in df.triples if t[0] in evs and t[2] in evs}
        row(f"raw/{name}.json", "DF of D restricted to the R2 execution event sets " + ", ".join(
            f"D[{i}→{o}]" for i, o in pairs), r1e == r2e, f"R1−R2 {sorted(r1e - r2e)}, R2−R1 {sorted(r2e - r1e)}")
    raw = load(R1 / "raw" / "all_global_executions_view.json")
    r1x = {(r["yStart"]["id"], r["x"]["id"], r["yEnd"]["id"]) for r in raw["rows"]}
    r2x = {(r["start_object"], r["execution_id"], r["end_object"])
           for r in load(R2 / "all_global_executions__by_object__noselfpairs.json")}
    row("raw/all_global_executions_view.json", "(start object, case, end object) of "
        "`all_global_executions__by_object__noselfpairs.json`", r1x == r2x,
        f"R1−R2 {sorted(r1x - r2x)}, R2−R1 {sorted(r2x - r1x)}")
    return stats


def open_points() -> list[str]:
    s = load(R2 / "case_notions_summary.json")
    g = load(R2 / "generalized_summary.json")
    c, cmp_ = g["cases"], g["comparisons"]
    fmt = lambda case: "; ".join(f"{k}: {' '.join(v)}" for k, v in case.items())
    nsp = s["global"]["by_object"]
    tm = lambda key: ", ".join(f"{k} {v}" for k, v in nsp[key]["per_type_pair"].items())
    bo = g["boundary_objects"]
    return [
        "## Answers to the R1 open points", "",
        "**1. Def. 10 – global vs. any start/end events.** On the running example, \"global\" and \"any\" give "
        "the same event and object sets in every case except the filtered end case under `global_on=full`; "
        "otherwise only the recorded other-side events differ.",
        f"- Unfiltered start cases: global == any: {cmp_['start_case_Order: global == any']}. "
        f"({fmt(c['start_case_Order__global'])}.)",
        f"- Unfiltered end cases: global == any: {cmp_['end_case_Order: global == any']}. "
        f"({fmt(c['end_case_Order__global'])}.)",
        f"- Filtered start cases: global (full) == any: {cmp_['start_case_Order_noSO: global_full == any']}; "
        f"filtered end cases: global (filtered) == any: {cmp_['end_case_Order_noSO: global_filtered == any']}, "
        f"global (full) == any: False (A5, see point 2).",
        "- **Unfiltered, this holds for every OCED-set** (with Def. 8's single start/end events), not only here. "
        "Start case D[o → ∗]: \"global\" ⊆ \"any\" since O_end ⊆ O. Conversely, let i = start(o) ≤ e = end(t) "
        "for any object t. The DF graph is acyclic (timestamps strictly increase along df-edges), so e reaches a "
        "DF-sink g. g has no df-successor for any of its objects, so g = end(t') for every object t' of g (g is "
        "correlated to one: if g ≠ e it has an incoming df-edge, else take t' = t), and g is a global end, so "
        "t' ∈ O_end. From e ≤ g follows E_i^e ⊆ E_i^g, and projection is monotone, so D[i → e] ⊆ D[i → g]: every "
        "part of \"any\" lies inside a part of \"global\". The end case is symmetric: every event is reached from "
        "a DF-source, which is the start event of all its objects and a global start. Property test: "
        "`test_def10_global_any.py`, 300 random OCED-sets without ties.",
        "- **Filtered (Def. 11), it depends on the data and on A5.** With `global_on=full` the sink g' of the "
        "filtered graph need not be a global end of D (it may still have df-successors via X). On the running "
        "example this already happens: the Fig. 12 end case is smaller under `full` than under `any`. A minimal "
        "counterexample for a start case: o: e1 → e2, x: e2 → e3, X = {x}; the only global end of D is e3 = end(x), "
        "unreachable without x's edge, so D[o → ∗ \\ X] is ∅ under `global/full` but {e1, e2} under `any`. With "
        "`global_on=filtered` the argument goes through on df(D, O \\ X) as long as the case's own object is not "
        "in X (also property-tested). It fails only in the degenerate case o ∈ X (o: e1, x: e2, X = {x}: "
        "D[x → ∗ \\ X] is {e2} under `any`, ∅ under `global/filtered`).", "",
        "**2. Def. 11 – global start/end events before vs. after filtering (A5).**",
        f"- Start case D[Order → ∗ \\ SO] (Fig. 11): no difference "
        f"(full == filtered: {cmp_['start_case_Order_noSO: global_full == global_filtered']}); "
        f"O_end is {bo['O_end__global_full']} in both readings. {fmt(c['start_case_Order_noSO__global_full'])}.",
        f"- End case D[∗ → Order \\ SO] (Fig. 12): differs "
        f"(full == filtered: {cmp_['end_case_Order_noSO: global_full == global_filtered']}). "
        f"O_start before filtering (full) = {bo['O_start__global_full']}, after (filtered) = "
        f"{bo['O_start__global_filtered']}.",
        f"  - before (full): {fmt(c['end_case_Order_noSO__global_full'])};",
        f"  - after (filtered): {fmt(c['end_case_Order_noSO__global_filtered'])}.",
        "- R1 (the tutorial query) equals the **after** reading. The paper's text on Fig. 12 (both cases "
        "depend on the same Receive SO events) also fits only \"after\": e6 and e19 (Receive SO) are not in "
        "the \"before\" cases. \"Before\" gives e1 e18 e27 e28 for ∗→O1, as R1 predicted. In the \"after\" "
        "reading the projection brings back excluded behaviour (spurious and reintroduced df-edges, "
        "see `projection_check.md`).", "",
        "**3. Def. 9 – self-pairs and \"distinct types\" (A3).**",
        f"- Without self-pairs (R1 query): {nsp['noselfpairs']['executions']} executions "
        f"({tm('noselfpairs')}).",
        f"- Def. 9 as written (self-pairs): {nsp['selfpairs']['executions']} executions "
        f"({tm('selfpairs')}); the extra ones are O1_O1, O2_O2, P1_P1.",
        f"- \"Distinct object types\" literally: {nsp['distinct_types']['executions']} executions "
        f"({tm('distinct_types')}); O2_O1 is dropped.",
        f"- Order→Order: 1 (query) / 3 (Def. 9) / 0 (distinct types). The by-object and by-type global "
        f"restrictions (A4) give the same executions: {s['global']['by_object_equals_by_type']}.",
        "",
    ]


def main() -> None:
    lines = ["# Comparison R2 vs. R1", "",
             "Generated by `python -m r2_python.compare_r1` from `results/r1/` and `results/r2/` "
             "(run `python -m r2_python.run_all` first). This is the first step in which R2 reads R1 results.", "",
             "\"equal\" = the same set of executions (matched by `execution_id`, i.e. start/end object) with the "
             "same sorted event and object lists. The numbers in the second column are the execution counts "
             "R1 / R2. The first R2 variant per R1 file implements the semantics of the R1 query; the others are "
             "the paper's alternatives (A1–A5). R1's `n_paths` / `n_distinct_paths` fields are not compared "
             "(R2 does not enumerate paths). All comparisons use `ties=strict` (A1); the running example has no "
             "timestamp ties, so A1 cannot cause a difference here.", "",
             "## Executions", "",
             "| R1 file | R2 variant | executions equal? | events equal? | objects equal? | start/end events equal? | difference |",
             "|---|---|---|---|---|---|---|"]
    st = exec_rows(lines)
    lines += ["", "## Data model, behaviour and query views", "",
              "| R1 file | R2 counterpart | equal? | difference |", "|---|---|---|---|"]
    st2 = structure_rows(lines)
    lines += ["", "Not compared: `claims.json` / `claims_table.md` (answered below and in the R2 log), "
              "`environment.json` and `runtimes.csv` (Step 7), `figures/` (rendered from the R1 files above). "
              "`raw/<name>.json` holds the unprocessed rows of the queries whose common-format files are "
              "compared above (identical content); the three `*_view` files have no common-format counterpart "
              "and are compared separately.", "",
              f"**Total:** {st['rows'] + st2['rows']} comparisons, "
              f"{st['unexplained'] + st2['unexplained']} unexplained differences.", ""]
    lines += open_points()
    with open(R2 / "comparison.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"wrote {R2 / 'comparison.md'}: {st['unexplained'] + st2['unexplained']} unexplained")


if __name__ == "__main__":
    main()
