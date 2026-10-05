"""R1 Step 4: object-centric executions and case notions (OCPM 3.1 and 3.3).

Every query in queries/executions/<name>.cypher is run as published (or, for `_fixed` files,
with the one documented fix). For each query we save
  results/r1/raw/<name>.json  - the query's own output (paths / rows / write counters) + notifications
  results/r1/<name>.json      - the common format
      [{execution_id, start_object, end_object, start_event, end_event, events, objects}]
and time it 5 times (results/r1/runtimes.csv).

One untimed warm-up run precedes the 5 timed runs. Notifications come from EXPLAIN (see common.py).
Materializing queries start from a graph without :Execution nodes (wiped before each run, not timed),
so each result reflects that query alone. Requires 01_build_ekg.py and 02_materialize.py.
"""

import csv
import json
import statistics
import sys
import time
from collections import defaultdict

from neo4j.graph import Node, Path, Relationship

from common import RESULTS_DIR, Runner, get_driver, load_cypher, notifications_of

RUNS = 5
RAW_DIR = RESULTS_DIR / "raw"


def ev_key(eid):
    return int(eid[1:])


# ---------------------------------------------------------------- serialization of raw results
def node_id(n):
    return n.get("EventID") or n.get("ID")


def ser(v):
    if isinstance(v, Path):
        return {"path": [node_id(n) for n in v.nodes],
                "df": [dict(r) for r in v.relationships]}
    if isinstance(v, Node):
        return {"labels": sorted(v.labels), "id": node_id(v)}
    if isinstance(v, Relationship):
        return {"type": v.type, "from": node_id(v.start_node), "to": node_id(v.end_node), **dict(v)}
    if isinstance(v, list):
        return [ser(x) for x in v]
    return v


# ---------------------------------------------------------------- running and timing
class Step4:
    def __init__(self, driver):
        self.driver = driver
        self.runtimes = []
        self.log = Runner(driver, verbose=False)
        lookup_events, lookup_objects = load_cypher("executions/ekg_lookup")
        self.event_objects = {r["event"]: r["objects"] for r in self.log.run(lookup_events)}
        self.objects = {r["object"]: r for r in self.log.run(lookup_objects)}

    def wipe(self):
        for q in load_cypher("executions/00_wipe_executions"):
            self.log.run(q)

    def run_once(self, query):
        t0 = time.perf_counter()
        with self.driver.session() as session:
            result = session.run(query)
            records = [r.values() for r in result]
            keys = result.keys()
            summary = result.consume()
        elapsed = (time.perf_counter() - t0) * 1000
        counters = {k: v for k, v in vars(summary.counters).items() if v and not k.startswith("_")}
        return records, keys, counters, elapsed

    def explain_notifications(self, query):
        # EXPLAIN always plans the query, so notifications are reported even if the plan is cached
        with self.driver.session() as session:
            return notifications_of(session.run("EXPLAIN " + query).consume())

    def run_timed(self, name, source, materializing=False):
        """Run queries/executions/<name>.cypher once untimed (warm-up: planning, caches), then RUNS
        timed runs; return the records of the last run."""
        [query] = load_cypher(f"executions/{name}")
        notes = self.explain_notifications(query)
        times = []
        for i in range(RUNS + 1):
            if materializing:
                self.wipe()
            records, keys, counters, elapsed = self.run_once(query)
            if i == 0:
                warmup = elapsed
            else:
                times.append(elapsed)
        self.runtimes.append({
            "name": name, "source": source, "rows": len(records), "warmup_ms": round(warmup, 2),
            "mean_ms": round(statistics.mean(times), 2), "std_ms": round(statistics.stdev(times), 2),
            "runs_ms": ";".join(f"{t:.2f}" for t in times),
        })
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        raw = {"query_file": f"r1_neo4j/queries/executions/{name}.cypher", "source": source,
               "columns": keys, "rows": [dict(zip(keys, map(ser, r))) for r in records],
               "write_counters": counters, "notifications": notes}
        with open(RAW_DIR / f"{name}.json", "w") as f:
            json.dump(raw, f, indent=2)
        flag = f" [{len(notes)} notification(s)]" if notes else ""
        print(f"{name:32s} rows={len(records):3d}  {statistics.mean(times):8.2f} ms "
              f"(sd {statistics.stdev(times):.2f}){flag}")
        return records

    # ------------------------------------------------------------ conversion to the common format
    def objects_of(self, events):
        return sorted({o for e in events for o in self.event_objects[e]})

    def common(self, execution_id, start_object, end_object, start_event, end_event, events):
        events = sorted(set(events), key=ev_key)
        return {"execution_id": execution_id, "start_object": start_object, "end_object": end_object,
                "start_event": start_event, "end_event": end_event,
                "events": events, "objects": self.objects_of(events)}

    def extract(self, start_type=None, end_type=None, xid=None):
        [q] = load_cypher("executions/extract_executions")
        rows = self.log.run(q, startType=start_type, endType=end_type, id=xid)
        out = [self.common(r["execution_id"], r["start_object"], r["end_object"],
                           r["start_event"], r["end_event"], r["events"]) for r in rows]
        return sorted(out, key=lambda x: x["execution_id"])

    def objects_with(self, kind, event, etype=None):
        return sorted(o for o, r in self.objects.items()
                      if r[kind] == event and (etype is None or r["type"] == etype))

    def from_paths(self, records, start_type, end_type):
        """Sect. 3.1 returns one path per row: group by (first, last) event = (start, end) of an execution."""
        groups = defaultdict(set)
        for [p] in records:
            ids = [node_id(n) for n in p.nodes]
            groups[(ids[0], ids[-1])].update(ids)
        out = []
        for (s, t), events in groups.items():
            so = ",".join(self.objects_with("start", s, start_type))
            eo = ",".join(self.objects_with("end", t, end_type))
            out.append(self.common(f"{so}_{eo}", so, eo, s, t, events))
        return sorted(out, key=lambda x: x["execution_id"])

    def from_path_groups(self, records, group_by, leading_type):
        """OCPM 3.3 returns one row per group (start or end event) with a list of paths.
        The leading object is the Order whose START (or END) is the grouping event; the other side is '*'."""
        out = []
        for [paths] in records:
            ids = [[node_id(n) for n in p.nodes] for p in paths]
            events = {e for path in ids for e in path}
            starts = sorted({path[0] for path in ids}, key=ev_key)
            ends = sorted({path[-1] for path in ids}, key=ev_key)
            if group_by == "start":
                [s] = starts
                lead = ",".join(self.objects_with("start", s, leading_type))
                x = self.common(f"{lead}_*", lead, "*", s, ends, events)
            else:
                [t] = ends
                lead = ",".join(self.objects_with("end", t, leading_type))
                x = self.common(f"*_{lead}", "*", lead, starts, t, events)
            x["n_paths"] = len(ids)
            x["n_distinct_paths"] = len({tuple(p) for p in ids})
            out.append(x)
        return sorted(out, key=lambda x: x["execution_id"])


def save(name, executions):
    with open(RESULTS_DIR / f"{name}.json", "w") as f:
        json.dump(executions, f, indent=2)


def main():
    driver = get_driver()
    try:
        r = Runner(driver, verbose=False)
        if not r.run("MATCH (:Event)-[s:START]->(:Entity) RETURN count(s) AS n")[0]["n"]:
            raise SystemExit("No :START relationships - run 01_build_ekg.py and 02_materialize.py first.")
        s4 = Step4(driver)
        print(f"Each query run {RUNS}x; materializing queries start without :Execution nodes.\n")

        # OCPM 3.1 Sect. 2.3: execution A -> O1
        s4.run_timed("exec_A_O1", "OCPM 3.1 §2.3 (materialize)", materializing=True)
        s4.run_timed("exec_A_O1_view", "OCPM 3.1 §2.3 (view)")
        save("exec_A_O1", s4.extract(xid="A_O1"))

        # OCPM 3.1 Sect. 3.1: as published ("Order " typo) and fixed
        recs = s4.run_timed("notion_SO_Order_paths", "OCPM 3.1 §3.1 as published")
        save("notion_SO_Order_paths", s4.from_paths(recs, "Supplier Order", "Order "))
        recs = s4.run_timed("notion_SO_Order_paths_fixed", "OCPM 3.1 §3.1 fixed (\"Order \" -> \"Order\")")
        save("notion_SO_Order_paths_fixed", s4.from_paths(recs, "Supplier Order", "Order"))

        # OCPM 3.1 Sect. 3.2/3.3: Supplier Order -> Order
        s4.run_timed("notion_SO_Order", "OCPM 3.1 §3.2 (materialize)", materializing=True)
        s4.run_timed("notion_SO_Order_view", "OCPM 3.1 §3.3 (view)")
        save("notion_SO_Order", s4.extract("Supplier Order", "Order"))

        # OCPM 3.1 Sect. 4: all executions between global start/end events, then 4.1-4.5
        s4.run_timed("all_global_executions", "OCPM 3.1 §4 (materialize)", materializing=True)
        s4.run_timed("all_global_executions_view", "OCPM 3.1 §4 (view)")
        save("all_global_executions", s4.extract())
        for name, st, et, src in [
            ("notion_SO_Order_global", "Supplier Order", "Order", "OCPM 3.1 §4.1"),
            ("notion_Order_Payment", "Order", "Payment", "OCPM 3.1 §4.2"),
            ("notion_Order_Invoice", "Order", "Invoice", "OCPM 3.1 §4.3 (types from text)"),
            ("notion_Payment_Invoice", "Payment", "Invoice", "OCPM 3.1 §4.4"),
            ("notion_Order_Order", "Order", "Order", "OCPM 3.1 §4.5"),
        ]:
            s4.run_timed(name, src)
            save(name, s4.extract(st, et))

        # OCPM 3.3 Sect. 6.2/6.3: start/end cases of Orders (not materialized)
        for name, group_by, src in [
            ("start_case_Order", "start", "OCPM 3.3 §6.2 (first query)"),
            ("start_case_Order_noSO", "start", "OCPM 3.3 §6.2 (excl. Supplier Order)"),
            ("end_case_Order", "end", "OCPM 3.3 §6.3 (first query)"),
            ("end_case_Order_noSO", "end", "OCPM 3.3 §6.3 (excl. Supplier Order)"),
        ]:
            recs = s4.run_timed(name, src)
            save(name, s4.from_path_groups(recs, group_by, "Order"))
    finally:
        driver.close()

    with open(RESULTS_DIR / "runtimes.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "source", "rows", "warmup_ms", "mean_ms", "std_ms", "runs_ms"])
        w.writeheader()
        w.writerows(s4.runtimes)
    print(f"\nWrote results to {RESULTS_DIR} (raw query output in {RAW_DIR})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
