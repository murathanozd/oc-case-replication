"""R3: why the published global-executions query (OCPM 3.1 Sect. 4) does not scale, and the fix.

all_global_executions.cypher matches every path (eStart)-[:DF*]->(eEnd) between a global start and
a global end event; the number of such paths grows exponentially with the DF graph.
all_global_executions_reach.cypher gets the same executions from reachability (polynomial).

For the configured dataset this script
  1. reads the DF graph and START/END from Neo4j and computes in Python (no path search):
     #DF paths the published query enumerates, and the expected executions (events between
     eStart and eEnd = descendants(eStart) & ancestors(eEnd));
  2. runs the reachability query (warm-up + timed runs) and the published query with a time limit
     (SCALING_TIMEOUT_S, default 600 s); each run starts without :Execution nodes;
  3. checks that every query that finished materialized exactly the expected executions.
Writes results/<dataset>/scaling.json and one row per dataset in results/scaling.csv.
Requires 01_build_ekg.py and 02_materialize.py for the dataset.
"""

import csv
import importlib
import json
import math
import os
import sys
import time
from collections import defaultdict

from neo4j.exceptions import Neo4jError

from common import DATASET, REPO_ROOT, RESULTS_DIR, load_cypher

step4 = importlib.import_module("03_executions")

TIMEOUT_S = float(os.environ.get("SCALING_TIMEOUT_S", 600))
SUMMARY = REPO_ROOT / "results" / "scaling.csv"


def expected_executions(s4):
    """Python version of the query semantics on the DF graph; also counts the DF paths."""
    df = s4.log.run("MATCH (a:Event)-[:DF]->(b:Event) RETURN a.EventID AS a, b.EventID AS b")
    out, inc = defaultdict(list), defaultdict(list)
    for r in df:
        out[r["a"]].append(r["b"])
        inc[r["b"]].append(r["a"])
    events = list(s4.event_objects)
    indeg = {e: len(inc[e]) for e in events}
    order, todo = [], [e for e in events if indeg[e] == 0]
    while todo:
        e = todo.pop()
        order.append(e)
        for f in out[e]:
            indeg[f] -= 1
            if indeg[f] == 0:
                todo.append(f)
    if len(order) != len(events):
        raise SystemExit("DF graph has a cycle; the reachability query is only equivalent on acyclic DF.")

    starts = defaultdict(list)  # global start event -> objects it starts
    ends = defaultdict(list)
    for o, r in s4.objects.items():
        if not inc[r["start"]]:
            starts[r["start"]].append(o)
        if not out[r["end"]]:
            ends[r["end"]].append(o)

    bit = {e: 1 << i for i, e in enumerate(order)}
    desc, anc, n_paths = {}, {}, {}
    for e in reversed(order):
        desc[e] = bit[e]
        n_paths[e] = int(e in ends)  # DF paths (counted per relationship, as [:DF*]) from e to a global end
        for f in out[e]:
            desc[e] |= desc[f]
            n_paths[e] += n_paths[f]
    for e in order:
        anc[e] = bit[e]
        for f in inc[e]:
            anc[e] |= anc[f]

    executions, paths = {}, 0
    for s, s_objs in starts.items():
        for t, t_objs in ends.items():
            if s == t or not desc[s] & bit[t]:
                continue
            between = desc[s] & anc[t]
            evs = sorted((e for e in order if between & bit[e]), key=step4.ev_key)
            for a in s_objs:
                for b in t_objs:
                    if a != b:
                        executions[f"{a}_{b}"] = (s, t, evs)
        paths += n_paths[s] - int(s in ends)  # paths of length >= 1, as [:DF*]
    stats = {"events": len(events), "df_edges": len(df), "global_start_events": len(starts),
             "global_end_events": len(ends), "df_paths_log10": round(math.log10(paths), 1) if paths else None,
             "executions": len(executions), "corr_edges": sum(len(v[2]) for v in executions.values())}
    return executions, stats


def same_as_expected(s4, expected):
    got = {x["execution_id"]: (x["start_event"], x["end_event"], x["events"]) for x in s4.extract()}
    return got == expected


def run(s4, name, expected, runs, warmup, timeout):
    """Run queries/executions/<name>.cypher (materializing) up to warmup+runs times; stop at a timeout."""
    [query] = load_cypher(f"executions/{name}")
    times, status, correct, error, failed_after = [], "ok", None, None, None
    for i in range(warmup + runs):
        s4.wipe()
        t0 = time.perf_counter()
        try:
            _, _, counters, elapsed, _ = s4.run_once(query, timeout=timeout)
        except Neo4jError as e:
            code = e.code or ""
            if "TimedOut" in code or "Timeout" in code:
                status = "timeout"
            elif "MemoryPoolOutOfMemoryError" in code:  # dbms.memory.transaction.total.max reached
                status = "out of memory"
            else:
                raise
            error, failed_after = e.message, round(time.perf_counter() - t0, 1)
            break
        if correct is None:
            correct = same_as_expected(s4, expected)
        if i >= warmup:
            times.append(elapsed)
    s4.wipe()
    res = {"query": name, "status": status, "same_executions_as_python": correct,
           "runs": len(times), "warmup_runs": warmup}
    if error:
        res.update({"failed_after_s": failed_after, "error": error})
    if times:
        res.update({"median_ms": round(sorted(times)[len(times) // 2], 1),
                    "min_ms": round(min(times), 1), "runs_ms": [round(t, 1) for t in times]})
    if error:
        status += f" after {failed_after} s"
    print(f"{name:32s} {status:22s} correct={correct}  "
          f"median {res.get('median_ms', '-')} ms over {len(times)} run(s)")
    return res


def main():
    driver = step4.get_driver()
    try:
        s4 = step4.Step4(driver)
        expected, stats = expected_executions(s4)
        print(f"{DATASET}: {json.dumps(stats)}")
        reach = run(s4, "all_global_executions_reach", expected, step4.RUNS, step4.WARMUP, None)
        # the published query: same number of runs if it finishes in time, none after a timeout
        published = run(s4, "all_global_executions", expected, step4.RUNS, step4.WARMUP, TIMEOUT_S)
    finally:
        driver.close()

    out = {"dataset": DATASET, "graph": stats, "timeout_s": TIMEOUT_S,
           "queries": [published, reach]}
    with open(RESULTS_DIR / "scaling.json", "w") as f:
        json.dump(out, f, indent=2)

    row = {"dataset": DATASET, **stats,
           "published_status": published["status"], "published_median_ms": published.get("median_ms"),
           "published_correct": published["same_executions_as_python"],
           "published_failed_after_s": published.get("failed_after_s"),
           "reach_status": reach["status"], "reach_median_ms": reach.get("median_ms"),
           "reach_correct": reach["same_executions_as_python"]}
    rows = []
    if SUMMARY.exists():
        with open(SUMMARY, newline="") as f:
            rows = [r for r in csv.DictReader(f) if r["dataset"] != DATASET]
    rows.append(row)
    with open(SUMMARY, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {RESULTS_DIR / 'scaling.json'} and {SUMMARY}")
    return 0 if reach["same_executions_as_python"] and published["same_executions_as_python"] is not False else 1


if __name__ == "__main__":
    sys.exit(main())
