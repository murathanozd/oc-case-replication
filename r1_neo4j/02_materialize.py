"""R1 Step 3: materialize object relations (:REL) and start/end events (:START, :END).

Queries as published in
  tutorial-ocpm-relations.md, Sect. 2 and 4.1      -> queries/materialize/01_related_objects, 02_rel
  tutorial-ocpm-object-traces.md, Sect. 2.2        -> queries/materialize/03_start, 04_end
Requires the EKG built by 01_build_ekg.py. Re-runnable: first removes the relationships
this step creates (it does not wipe the EKG itself, see docs/r1_log.md).
"""

import csv
import json
import sys

from common import RESULTS_DIR, Runner, get_driver, load_cypher

# Directed relations listed in tutorial-ocpm-relations.md, Sect. 3 (n1.ID, n2.ID)
TUTORIAL_REL = {
    ("O2", "B"), ("O1", "X1"), ("A", "X1"), ("O1", "X2"), ("A", "X2"), ("O2", "X3"), ("A", "X3"),
    ("O1", "Y1"), ("B", "Y1"), ("O2", "Y2"), ("B", "Y2"), ("O2", "I2"), ("O1", "I1"),
    ("I2", "P1"), ("I1", "P1"),
}


def main():
    driver = get_driver()
    try:
        runner = Runner(driver)
        if runner.run("MATCH (e:Event) RETURN count(e) AS n")[0]["n"] == 0:
            raise SystemExit("No :Event nodes - run r1_neo4j/01_build_ekg.py first.")

        for q in load_cypher("materialize/00_reset"):
            runner.run(q)
        [q_related] = load_cypher("materialize/01_related_objects")
        related = runner.run(q_related)
        for name in ["02_rel", "03_start", "04_end"]:
            for q in load_cypher(f"materialize/{name}"):
                runner.run(q)

        q_rel, q_start_end = load_cypher("materialize/checks")
        quiet = Runner(driver, verbose=False)
        rel = quiet.run(q_rel)
        start_end = quiet.run(q_start_end)
    finally:
        driver.close()

    undirected = {frozenset((r["n1.ID"], r["n2.ID"])) for r in related}
    rel_pairs = {(r["n1"], r["n2"]) for r in rel}
    no_direction = sorted(sorted(p) for p in undirected if not any(set(p) == {a, b} for a, b in rel_pairs))
    multi = [r for r in start_end if len(r["starts"]) != 1 or len(r["ends"]) != 1]

    stats = {
        "related_rows_sect2": len(related),
        "related_pairs_undirected": len(undirected),
        "rel_edges": len(rel),
        "rel_equals_tutorial_table": rel_pairs == TUTORIAL_REL,
        "rel_missing_vs_tutorial": sorted(TUTORIAL_REL - rel_pairs),
        "rel_extra_vs_tutorial": sorted(rel_pairs - TUTORIAL_REL),
        "related_pairs_without_direction": no_direction,
        "start_relationships": sum(len(r["starts"]) for r in start_end),
        "end_relationships": sum(len(r["ends"]) for r in start_end),
        "objects_not_exactly_one_start_and_end": multi,
        "server_notifications": runner.notifications,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / "rel_edges.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["n1", "type1", "t1", "n2", "type2", "t2"])
        for r in rel:
            w.writerow([r["n1"], r["type1"], r["t1"], r["n2"], r["type2"], r["t2"]])
    with open(RESULTS_DIR / "start_end.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["object", "type", "start_event", "end_event", "n_start", "n_end"])
        for r in start_end:
            w.writerow([r["object"], r["type"], ";".join(r["starts"]), ";".join(r["ends"]),
                        len(r["starts"]), len(r["ends"])])
    with open(RESULTS_DIR / "materialize_stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    print("\n=== Step 3 results ===")
    print(f"Related object pairs (Sect. 2): {len(related)} rows = {len(undirected)} undirected pairs")
    print(f":REL edges: {len(rel)}; equal to tutorial table (Sect. 3): {stats['rel_equals_tutorial_table']}")
    print(f"Related pairs that got no :REL (equal first timestamps): {no_direction or 'none'}")
    for r in rel:
        print(f"  {r['n1']:>3} -> {r['n2']:<3} ({r['type1']} -> {r['type2']})")
    print(f"\n:START {stats['start_relationships']}, :END {stats['end_relationships']}")
    print(f"{'object':7s} {'type':15s} {'start':6s} {'end':6s}")
    for r in start_end:
        print(f"{r['object']:7s} {r['type']:15s} {';'.join(r['starts']):6s} {';'.join(r['ends']):6s}")
    print("Objects with != 1 start or end event: "
          + (", ".join(f"{r['object']} (starts {r['starts']}, ends {r['ends']})" for r in multi) if multi else "none"))
    print(f"\nWrote rel_edges.csv, start_end.csv, materialize_stats.json to {RESULTS_DIR}")
    return 0 if stats["rel_equals_tutorial_table"] else 1


if __name__ == "__main__":
    sys.exit(main())
