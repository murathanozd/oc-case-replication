"""R1 Step 5: check the paper's claims about the running example against the saved R1 results.

Reads results/r1/*.json / *.csv (produced by 01-03) and writes
  results/r1/claims_table.md  - one row per claim
  results/r1/claims.json      - same content, machine-readable
No database access. The only computation outside Neo4j is a reachability check on df_edges.csv
for claim 12 (Def. 10 start case vs. the tutorial query, unfiltered case only).
"""

import csv
import json
import sys
from collections import defaultdict

from common import RESULTS_DIR


def load(name):
    with open(RESULTS_DIR / f"{name}.json") as f:
        return json.load(f)


def by_id(executions):
    return {x["execution_id"]: x for x in executions}


def evs(x):
    return set(x["events"])


def fmt(events):
    return " ".join(sorted(events, key=lambda e: int(e[1:])))


def pairs(executions):
    return sorted((x["start_object"], x["end_object"]) for x in executions)


# ---------------------------------------------------------------- EKG facts from CSV exports
with open(RESULTS_DIR / "df_edges.csv") as f:
    DF = [r for r in csv.DictReader(f)]
with open(RESULTS_DIR / "start_end.csv") as f:
    OBJ = {r["object"]: r for r in csv.DictReader(f)}
EVENTS = {r["e1"] for r in DF} | {r["e2"] for r in DF}
SUCC, PRED = defaultdict(set), defaultdict(set)
for r in DF:
    SUCC[r["e1"]].add(r["e2"])
    PRED[r["e2"]].add(r["e1"])
GLOBAL_START = {e for e in EVENTS if not PRED[e]}
GLOBAL_END = {e for e in EVENTS if not SUCC[e]}


def reach(e, nxt):
    seen, todo = {e}, [e]
    while todo:
        for n in nxt[todo.pop()]:
            if n not in seen:
                seen.add(n)
                todo.append(n)
    return seen


def between(i, o):
    """E_io = {e | i <= e <= o} (Def. 7), via df-reachability (Lemma 1)."""
    return reach(i, SUCC) & reach(o, PRED) if o in reach(i, SUCC) else set()


def def10_start_case(o):
    """D[o -> *] = union of D[o -> oend] for oend in O_end (objects whose end event is a global end)."""
    o_end = [n for n, r in OBJ.items() if r["end_event"] in GLOBAL_END]
    out = set()
    for n in o_end:
        out |= between(OBJ[o]["start_event"], OBJ[n]["end_event"])
    return out


# ---------------------------------------------------------------- shared wording
PATHS_VS_CLOSURE = ("Def. 7 uses ≤ (transitive closure); the query enumerates `[:DF*]` paths. "
                    "Equivalent by Lemma 1.")
DEF10_GLOBAL = ("(a) Def. 10 restricts the other end to objects with a **global** start/end event "
                "(O_end / O_start); the OCPM 3.3 query accepts any `:START`/`:END` event.")
DEF11_ORDER = ("(c) Def. 11 (filtered) is ambiguous on whether global start/end events are determined "
               "**before** or **after** removing the excluded objects' df-edges.")


def main():
    a_o1 = load("exec_A_O1")
    so_o = by_id(load("notion_SO_Order"))
    allx = load("all_global_executions")
    allx_id = by_id(allx)
    o_p = load("notion_Order_Payment")
    o_i = load("notion_Order_Invoice")
    p_i = load("notion_Payment_Invoice")
    o_o = load("notion_Order_Order")
    sc = by_id(load("start_case_Order"))
    sc_f = by_id(load("start_case_Order_noSO"))
    ec_f = by_id(load("end_case_Order_noSO"))
    typo = load("notion_SO_Order_paths")
    fixed = by_id(load("notion_SO_Order_paths_fixed"))
    activity = {}  # activity names of events, from the prepared CSV
    with open(RESULTS_DIR.parent.parent / "r1_neo4j" / "prepared"
              / "order_process_event_table_orderhandling_prepared.csv") as f:
        for r in csv.DictReader(f):
            activity[r["EventID"]] = r["Activity"]
    types = {o: r["type"] for o, r in OBJ.items()}

    claims = []

    def claim(num, text, ref, expected, observed, match, note="", dvq=""):
        claims.append({"#": num, "claim": text, "paper": ref, "expected": expected,
                       "observed": observed, "match": match, "note": note, "definition vs. query": dvq})

    # 1 ----------------------------------------------------------------------------------------
    [x] = a_o1
    exp_obj = {"A", "X1", "X2", "X3", "O1", "Y1"}
    x1x2_shipped = {"e27", "e28"} <= evs(x) and all(e in evs(x) for e in ["e6", "e8", "e10", "e11"])
    claim(1, "D[e3→e28] handles items X1, X2, X3 of supplier order A; X1, X2 are packed and shipped "
             "for O1; object layer includes A, X1, X2, X3, O1 and Y1",
          "Sect. 4, Fig. 5", "objects A, O1, X1, X2, X3, Y1",
          f"events {fmt(evs(x))}; objects {', '.join(x['objects'])}",
          "yes" if set(x["objects"]) == exp_obj and x1x2_shipped and x["start_event"] == "e3"
          and x["end_event"] == "e28" else "no",
          "Same events from OCPM 3.1 §2.3 (`exec_A_O1`) and as A_O1 in §3.2 and §4. "
          "X3 appears via Receive SO (e6) and Unpack (e8) only.",
          PATHS_VS_CLOSURE)

    # 2 ----------------------------------------------------------------------------------------
    exp = [("A", "O1"), ("A", "O2"), ("B", "O1"), ("B", "O2")]
    claim(2, "D[SupplierOrder→Order] has 4 cases: A→O1, A→O2, B→O1, B→O2",
          "Sect. 5.1, Def. 9, Fig. 6", "4: A→O1, A→O2, B→O1, B→O2",
          f"{len(so_o)}: " + ", ".join(f"{s}→{e}" for s, e in pairs(so_o.values())),
          "yes" if pairs(so_o.values()) == exp else "no",
          f"OCPM 3.1 §3.1 as published (`\"Order \"` typo): {len(typo)} executions (0 paths, no error); "
          f"fixed copy: {len(fixed)} executions with the same event sets as §3.2: "
          f"{all(evs(fixed[k]) == evs(so_o[k]) for k in so_o) and set(fixed) == set(so_o)}.",
          PATHS_VS_CLOSURE)

    # 3, 4 --------------------------------------------------------------------------------------
    ov = evs(so_o["A_O1"]) & evs(so_o["A_O2"])
    claim(3, "D[A→O1] and D[A→O2] overlap exactly on e3, e6, e8", "Sect. 5.1", "e3 e6 e8", fmt(ov),
          "yes" if ov == {"e3", "e6", "e8"} else "no", "", PATHS_VS_CLOSURE)
    ov = evs(so_o["A_O1"]) & evs(so_o["B_O1"])
    claim(4, "D[A→O1] and D[B→O1] overlap exactly on e27, e28", "Sect. 5.1", "e27 e28", fmt(ov),
          "yes" if ov == {"e27", "e28"} else "no", "", PATHS_VS_CLOSURE)

    # 5 ----------------------------------------------------------------------------------------
    st = sorted({types[o] for o, r in OBJ.items() if r["start_event"] in GLOBAL_START})
    en = sorted({types[o] for o, r in OBJ.items() if r["end_event"] in GLOBAL_END})
    obs_st = sorted({types[x["start_object"]] for x in allx})
    obs_en = sorted({types[x["end_object"]] for x in allx})
    claim(5, "Considered start types: Order, Supplier Order, Payment; end types: Order, Invoice, Payment",
          "Sect. 5.2", "start {Order, Payment, Supplier Order}; end {Invoice, Order, Payment}",
          f"start {{{', '.join(st)}}}; end {{{', '.join(en)}}} (global start events "
          f"{fmt(GLOBAL_START)}, global end events {fmt(GLOBAL_END)})",
          "yes" if st == ["Order", "Payment", "Supplier Order"] and en == ["Invoice", "Order", "Payment"]
          and obs_st == st and obs_en == en else "no",
          "The types of the start/end objects in `all_global_executions` are the same sets.",
          "Paper restricts *types* (\"objects have a global start event\"); the §4 query restricts "
          "*objects* (`NOT ()-[:DF]->(eStart)`). Same result here: every Order, Supplier Order and Payment "
          "object has a global start event and every Order, Invoice and Payment object a global end event, "
          "while no Invoice or Item object starts globally (e5, e18, e6, e19 have df-predecessors) and no "
          "Supplier Order or Item object ends globally (e11, e21, e27, e33 have df-successors).")

    # 6 ----------------------------------------------------------------------------------------
    claim(6, "D[Order→Payment]: 2 executions, both ending in P1", "Sect. 5.2, Fig. 8 (left)",
          "2: O1→P1, O2→P1",
          f"{len(o_p)}: " + "; ".join(f"{x['start_object']}→{x['end_object']} ({fmt(evs(x))})" for x in o_p),
          "yes" if pairs(o_p) == [("O1", "P1"), ("O2", "P1")] else "no",
          "Paper text: \"each have their own invoice P1 and P2\" – should be I1 and I2 (typo in the paper; "
          "O1's execution contains I1's events, O2's contains I2's Update Invoice e9).",
          PATHS_VS_CLOSURE)

    # 7 ----------------------------------------------------------------------------------------
    p1_trace = {"e29", "e30"}
    claim(7, "D[Payment→Invoice]: 2 executions (P1→I1, P1→I2), behaviorally just the trace of P1",
          "Sect. 5.2, Fig. 8 (right)", "2: P1→I1, P1→I2; events = trace of P1 (e29 e30)",
          f"{len(p_i)}: " + "; ".join(f"{x['start_object']}→{x['end_object']} ({fmt(evs(x))})" for x in p_i),
          "yes" if pairs(p_i) == [("P1", "I1"), ("P1", "I2")] and all(evs(x) == p1_trace for x in p_i)
          else "no", "", PATHS_VS_CLOSURE)

    # 8 ----------------------------------------------------------------------------------------
    same = sorted(fmt(evs(x)) for x in o_p) == sorted({fmt(evs(x)) for x in o_i})
    claim(8, "D[Order→Invoice]: 4 executions incl. \"emergent\" O1→I2 and O2→I1; same executions as "
             "Order→Payment because of shared end event e30",
          "Sect. 5.2, Fig. 8 (left)", "4: O1→I1, O1→I2, O2→I1, O2→I2; event sets = Order→Payment",
          f"{len(o_i)}: " + "; ".join(f"{x['start_object']}→{x['end_object']} ({fmt(evs(x))})" for x in o_i),
          "yes" if pairs(o_i) == [("O1", "I1"), ("O1", "I2"), ("O2", "I1"), ("O2", "I2")] and same
          and all(x["end_event"] == "e30" for x in o_i + o_p) else "no",
          "Query for §4.3 is not printed in the tutorial; derived from §4.2 with the types named in the text.",
          PATHS_VS_CLOSURE)

    # 9 ----------------------------------------------------------------------------------------
    [x] = o_o if len(o_o) == 1 else [None]
    ok = x is not None and (x["start_object"], x["end_object"]) == ("O2", "O1") and "e7" in evs(x)
    split = x is not None and evs(x) == between("e2", "e7") | between("e7", "e28")
    claim(9, "D[Order→Order]: exactly 1 execution, O2→O1, passing through e7 (Update SO)",
          "Sect. 5.2, Fig. 9", "1: O2→O1 containing e7",
          f"{len(o_o)}: " + "; ".join(f"{y['start_object']}→{y['end_object']} ({fmt(evs(y))})" for y in o_o),
          "yes" if ok else "no",
          f"e7 = {activity['e7']}. Events equal D[e2→e7] ∪ D[e7→e28] as described in the paper: {split}.",
          "Def. 9 allows o_st = o_end, so by definition D[Order→Order] also contains D[O1→O1] and "
          "D[O2→O2] (the paper uses these in Sect. 5.3). The \"exactly 1\" holds only because the §4 query "
          "has `nEnd <> nStart`. " + PATHS_VS_CLOSURE)

    # 10 ---------------------------------------------------------------------------------------
    counts = defaultdict(int)
    for x in allx:
        counts[(types[x["start_object"]], types[x["end_object"]])] += 1
    claim(10, "In total 13 executions between objects with global start/end events (Fig. 7)",
          "OCPM 3.1 §4, Sect. 5.2, Fig. 7",
          "13 = SO→Order 4, Order→Payment 2, Payment→Invoice 2, Order→Invoice 4, Order→Order 1",
          f"{len(allx)} = " + ", ".join(f"{s}→{e} {n}" for (s, e), n in sorted(counts.items())),
          "yes" if len(allx) == 13 and counts == {("Supplier Order", "Order"): 4, ("Order", "Payment"): 2,
                                                   ("Payment", "Invoice"): 2, ("Order", "Invoice"): 4,
                                                   ("Order", "Order"): 1} else "no",
          "Execution IDs: " + ", ".join(sorted(allx_id)) + ".",
          "Count relies on `nEnd <> nStart` in the §4 query (see claim 9): with D[o→o] allowed (Def. 9), "
          "O1→O1, O2→O2 and P1→P1 would add 3 more.")

    # 11 ---------------------------------------------------------------------------------------
    present = set(counts)
    absent = [("Order", "Supplier Order"), ("Supplier Order", "Invoice"), ("Supplier Order", "Payment")]
    same_type = [(x["start_object"], x["end_object"]) for x in allx
                 if types[x["start_object"]] == types[x["end_object"]]]
    claim(11, "No executions Order→Supplier Order, Supplier Order→Invoice, Supplier Order→Payment; none "
              "between distinct objects of the same type except O2→O1",
          "Sect. 5.2", "none of the 3 type pairs; same-type only O2→O1",
          f"absent type pairs present: {[p for p in absent if p in present] or 'none'}; same-type "
          f"executions: {', '.join(f'{s}→{e}' for s, e in same_type)}",
          "yes" if not [p for p in absent if p in present] and same_type == [("O2", "O1")] else "no",
          "Checked on the 13 global executions only, as in the paper/tutorial.",
          "Same caveat as claim 9 (`nEnd <> nStart`).")

    # 12 ---------------------------------------------------------------------------------------
    o2 = sc["O2_*"]
    a_events = {e for e in EVENTS if "A" in OBJ and e in between(OBJ["A"]["start_event"], OBJ["A"]["end_event"])}
    has_b = bool(evs(o2) & between(OBJ["B"]["start_event"], OBJ["B"]["end_event"]))
    has_y = {"e19", "e20", "e21"} <= evs(o2)
    no_a = not (evs(o2) & a_events) and "A" not in o2["objects"]
    def10 = {o: def10_start_case(o) for o in ["O1", "O2"]}
    coincide = all(def10[o] == evs(sc[f"{o}_*"]) for o in ["O1", "O2"])
    claim(12, "D[Order→∗] includes behavior of B and items Y1, Y2 but not of A (the \"incompleteness\")",
          "Sect. 5.3, Def. 10, Fig. 10", "O2→∗ contains B and Y1, Y2 behavior, no A behavior",
          f"O1→∗: {fmt(evs(sc['O1_*']))}; O2→∗: {fmt(evs(o2))}",
          "yes" if has_b and has_y and no_a else "no",
          f"B events in O2→∗: {fmt(evs(o2) & between(OBJ['B']['start_event'], OBJ['B']['end_event']))}; "
          f"no A events (A's events: {fmt(a_events)}). The query also ends paths at non-global end events "
          f"(e21 = end of B; e27, e33 = ends of items).",
          DEF10_GLOBAL + " (b) For the unfiltered start case the event sets coincide anyway: every df-sink "
          "is a global end, so each non-global end lies on a path to a global end. Checked in Python on "
          f"df_edges.csv: Def. 10 reading equals the query result for O1 and O2: {coincide}.")

    # 13 ---------------------------------------------------------------------------------------
    starts = {x["start_event"] for x in sc_f.values()}
    claim(13, "D[Order→∗ \\ {SupplierOrder}]: two cases starting in Create Order; invoices of both cleared "
              "by the same payment",
          "Sect. 5.3, Def. 11, Fig. 11", "2 cases starting in Create Order, both containing the same "
                                         "Clear Invoice event of P1",
          "; ".join(f"{k}: {fmt(evs(x))}" for k, x in sorted(sc_f.items())),
          "yes" if len(sc_f) == 2 and {activity[e] for e in starts} == {"Create Order"}
          and all("e30" in evs(x) for x in sc_f.values()) else "no",
          f"Paper: \"two simple and clear cases starting in Place Order\" – the activity in the data is "
          f"\"{activity['e1']}\" (e1, e2); \"Place Order\" does not occur (only \"Place SO\"). Both cases "
          f"contain e30 ({activity['e30']}, P1). O2→∗ still contains e7 ({activity['e7']}), which is "
          "correlated to B: the filter removes B's df-edges, not events shared with B.",
          DEF10_GLOBAL + " " + DEF11_ORDER + " Open point for R2 (not computed in R1).")

    # 14 ---------------------------------------------------------------------------------------
    inv = {e for x in ec_f.values() for e in evs(x) if activity[e] in ("Create Invoice", "Update Invoice",
                                                                         "Clear Invoice")}
    pay = {e for x in ec_f.values() for e in evs(x) if activity[e] in ("Receive Payment", "Clear Invoice")}
    shared = evs(ec_f["*_O1"]) & evs(ec_f["*_O2"])
    claim(14, "D[∗→Order \\ {SupplierOrder}] contains no Invoice or Payment events; both cases depend on "
              "the Receive SO events",
          "Sect. 5.3, Def. 11, Fig. 12", "no Invoice/Payment events; shared Receive SO events",
          "; ".join(f"{k}: {fmt(evs(x))}" for k, x in sorted(ec_f.items()))
          + f". Invoice events: {fmt(inv)}; Payment events: {fmt(pay) or 'none'}; shared: {fmt(shared)}",
          "partial",
          "Paper: \"Notably, the executions do not contain any invoices or payments as these are not involved "
          "in completing an order.\" Observed: no Payment events, but e18 and e5 (Create Invoice, correlated "
          "to the Order and to I1 / I2) are in the cases, so invoices I1, I2 are in the object layer. The "
          f"cases share only {fmt(shared)} ({', '.join(sorted({activity[e] for e in shared}))}), which "
          "supports \"independent of each other … dependent on the same Receive SO events\".",
          DEF10_GLOBAL + " " + DEF11_ORDER + " The tutorial query starts paths at object start events "
          "(e1, e2, e5, e6, e18, e19); its event sets equal the **after** reading. The **before** reading "
          "would give only e1 e18 e27 e28 for ∗→O1. Open point for R2 (not computed in R1).")

    # ------------------------------------------------------------------------------------------
    with open(RESULTS_DIR / "claims.json", "w") as f:
        json.dump(claims, f, indent=2, ensure_ascii=False)

    cols = ["#", "claim", "paper", "expected", "observed", "match", "note", "definition vs. query"]
    head = ["#", "claim", "paper (section/figure)", "expected", "observed", "match", "note",
            "definition vs. query"]
    lines = ["# R1 claims table", "",
             "Generated by `r1_neo4j/04_check_claims.py` from the results in `results/r1/`. "
             "\"paper\" = Fahland & Montali, LNCS 16480 (2026); OCPM x = tutorials in "
             "`external/eventgraph_tutorial` (pinned `31d19b8`).", "",
             "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for c in claims:
        lines.append("| " + " | ".join(str(c[k]).replace("|", "\\|").replace("\n", " ") for k in cols) + " |")
    summary = defaultdict(int)
    for c in claims:
        summary[c["match"]] += 1
    lines += ["", f"Summary: {len(claims)} claims – " + ", ".join(f"{k}: {v}" for k, v in sorted(summary.items()))]
    with open(RESULTS_DIR / "claims_table.md", "w") as f:
        f.write("\n".join(lines) + "\n")

    for c in claims:
        print(f"{c['#']:2d} {c['match']:8s} {c['claim'][:90]}")
        print(f"   observed: {c['observed'][:160]}")
    print("\nSummary:", dict(summary))
    return 0 if len(claims) == 14 else 1


if __name__ == "__main__":
    sys.exit(main())
