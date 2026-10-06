"""Step 7 timing:  python -m r2_python.timing  ->  results/r2/runtimes.csv

For each computation: 1 warm-up run, then 5 timed runs (time.perf_counter); mean and sample std in ms.
The OCED-set and its DF relation are built once outside the timed computations (except for the first two
rows, which time exactly that), so the indexes of OCEDSet (cached) are warm after the warm-up.
Runtimes are machine-dependent and are not part of the byte-identical results.
"""

from __future__ import annotations

import csv
import statistics
import time

from .behaviour import directly_follows
from .case_notions import case_notion, global_executions
from .executions import case_record
from .generalized import excluded_objects, type_records
from .oced import load_csv
from .projection_check import report as projection_report
from .run_all import DATA, OUT

RUNS = 5


def measure(fn) -> tuple[float, list[float]]:
    t = time.perf_counter()
    fn()
    warm = (time.perf_counter() - t) * 1000
    runs = []
    for _ in range(RUNS):
        t = time.perf_counter()
        fn()
        runs.append((time.perf_counter() - t) * 1000)
    return warm, runs


def computations():
    d = load_csv(DATA)
    df = directly_follows(d)
    X = excluded_objects(d, types=["Supplier Order"])
    yield "load_csv", "Def. 1-2: load raw CSV, make relation-consistent", lambda: load_csv(DATA)
    yield "directly_follows", "Def. 3: DF relation (ties=strict)", lambda: directly_follows(d)
    yield "exec_A_O1", "Def. 7/8: D[A -> O1]", lambda: case_record(d, df, "A", "O1")
    for name, a, b in (("SO_Order", "Supplier Order", "Order"), ("Order_Payment", "Order", "Payment"),
                       ("Order_Invoice", "Order", "Invoice"), ("Payment_Invoice", "Payment", "Invoice"),
                       ("Order_Order", "Order", "Order")):
        yield f"notion_{name}", f"Def. 9: {a} -> {b}, no self-pairs", \
            lambda a=a, b=b: case_notion(d, df, a, b, self_pairs=False)
    yield "all_global_executions", "Def. 9 + Sect. 5.2 (by object, no self-pairs)", \
        lambda: global_executions(d, df, "object", self_pairs=False)
    for side in ("start", "end"):
        yield f"{side}_case_Order", f"Def. 10: {side} cases of Orders (global)", \
            lambda side=side: type_records(d, df, side, "Order", variant="global")
        for go in ("full", "filtered"):
            yield f"{side}_case_Order_noSO__global_{go}", \
                f"Def. 10 + 11: {side} cases of Orders without Supplier Orders (global_on={go})", \
                lambda side=side, go=go: type_records(d, df, side, "Order", variant="global", X=X, global_on=go)
    yield "projection_check", "projection check report (all event pairs)", lambda: projection_report(d, df, X)


def main() -> None:
    rows = []
    for name, what, fn in computations():
        warm, runs = measure(fn)
        rows.append([name, what, f"{warm:.3f}", f"{statistics.mean(runs):.3f}", f"{statistics.stdev(runs):.3f}",
                     ";".join(f"{r:.3f}" for r in runs)])
    with open(OUT / "runtimes.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["name", "computation", "warmup_ms", "mean_ms", "std_ms", "runs_ms"])
        w.writerows(rows)
    print(f"wrote {OUT / 'runtimes.csv'}")


if __name__ == "__main__":
    main()
