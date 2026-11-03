"""Render the paper's figures (Fig. 4-12) from the R1 query results.

The figures are drawn from the files that the Neo4j queries produced
(results/r1/*.json, results/r1/df_edges.csv), not from a separate
computation. This avoids two problems with screenshots of Neo4j Browser /
Query: (1) the tool automatically draws every stored relationship between
returned nodes, which brings back DF edges that a filtered case excludes,
and (2) screenshots are raster images.

Layout ("object lanes"):
  * one horizontal lane per object of the execution (its object layer, O[E]),
    grouped by object type;
  * events on the x-axis in timestamp order;
  * a dot where an event is correlated to an object; a thin vertical line
    joins the dots of one event (= the event synchronizes these objects);
  * DF edges as arrows inside the lane of the object they belong to.
    Only DF edges between events of the execution are drawn, and for
    filtered cases (Def. 11) edges of excluded object types are omitted.
    This equals the set of DF edges on start-to-end paths (every event of
    an execution lies on such a path).
  * start / end events of the execution are drawn with a black ring.

Run from the repository root:  python replication/05_render_figures.py
Writes PDF (for LaTeX) and PNG (for quick viewing) to results/r1/figures/.
"""

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.transforms import offset_copy  # noqa: E402

from common import DATASET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "running_example" / "order_process_event_table_orderhandling.csv"
RES = ROOT / "results" / "running_example"
OUT = RES / "figures"

TYPES = ["Order", "Supplier Order", "Item", "Invoice", "Payment"]
COLUMN = {"Order": "Order", "Supplier Order": "Supplier Order", "Item": "Item",
          "Invoice": "Invoice", "Payment": "Payment"}
# Categorical palette in fixed order (validated: CVD + normal-vision checks pass).
# Contrast < 3:1 for some hues is compensated by direct labels (every edge and
# lane carries its object id) and a per-type line style for grayscale print.
COLOR = {"Order": "#2a78d6", "Supplier Order": "#eb6834", "Item": "#1baf7a",
         "Invoice": "#eda100", "Payment": "#e87ba4"}
STYLE = {"Order": "-", "Supplier Order": (0, (5, 2)), "Item": (0, (1, 1.5)),
         "Invoice": (0, (6, 2, 1, 2)), "Payment": (0, (3, 1, 1, 1, 1, 1))}
INK, MUTED, FAINT = "#222222", "#6b6b6b", "#c9c9c9"


def natkey(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", str(s))]


# ---------------------------------------------------------------- input data
def load_events():
    events, corr, otype = {}, defaultdict(set), {}
    with open(DATA, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            eid = row["EventID"]
            d, t = row["time"].split(" ")
            dd, mm, yyyy = d.split(".")
            events[eid] = {"activity": row["event"], "time": f"{yyyy}-{mm}-{dd}T{t}"}
            for ty in TYPES:
                val = (row.get(COLUMN[ty]) or "").strip()
                for oid in [v.strip() for v in val.split(",") if v.strip()]:
                    corr[eid].add(oid)
                    otype[oid] = ty
    return events, corr, otype


def load_df():
    with open(RES / "df_edges.csv", newline="") as f:
        return [(r["e1"], r["e2"], r["object_id"], r["entity_type"]) for r in csv.DictReader(f)]


def load(name):
    with open(RES / f"{name}.json") as f:
        return json.load(f)


def as_list(x):
    return x if isinstance(x, list) else [x]


# ------------------------------------------------------------------- drawing
def lanes_draw(ax, events, corr, otype, df, ev_set, *, objects=None,
               excluded_types=(), starts=(), ends=(), title="", subtitle=""):
    ev = sorted(ev_set, key=lambda e: (events[e]["time"], natkey(e)))
    x = {e: i for i, e in enumerate(ev)}
    if objects is None:
        objects = set().union(*(corr[e] for e in ev))
    objs = sorted(objects, key=lambda o: (TYPES.index(otype[o]), natkey(o)))
    y = {o: -i for i, o in enumerate(objs)}

    # lanes
    for o in objs:
        excl = otype[o] in excluded_types
        ax.axhline(y[o], color=FAINT, lw=0.6, zorder=0)
        ax.text(-0.7, y[o], f"{o}", ha="right", va="center", fontsize=8.5,
                color=MUTED if excl else INK, fontweight="bold")
        ax.text(-0.7, y[o] - 0.33, otype[o] + (" (excluded)" if excl else ""),
                ha="right", va="center", fontsize=6, color=MUTED)

    # DF edges inside lanes
    for e1, e2, oid, ty in df:
        if e1 in x and e2 in x and oid in y and ty not in excluded_types:
            ax.annotate("", xy=(x[e2] - 0.13, y[oid]), xytext=(x[e1] + 0.13, y[oid]),
                        arrowprops=dict(arrowstyle="-|>", color=COLOR[ty], lw=2,
                                        linestyle=STYLE[ty], shrinkA=0, shrinkB=0,
                                        mutation_scale=9),
                        zorder=2)

    # events: synchronization line + dots
    for e in ev:
        ys = [y[o] for o in corr[e] if o in y]
        if len(ys) > 1:
            ax.plot([x[e], x[e]], [min(ys), max(ys)], color=MUTED, lw=1, zorder=1)
        for o in sorted(corr[e], key=natkey):  # sorted: set order varies per run (hash seed)
            if o in y:
                ring = e in starts or e in ends
                ax.scatter([x[e]], [y[o]], s=60, zorder=3,
                           color=MUTED if otype[o] in excluded_types else COLOR[otype[o]],
                           edgecolors=INK if ring else "white", linewidths=1.6 if ring else 1.2)

    ax.set_xticks(range(len(ev)))
    ax.set_xticklabels([f"{e}\n{events[e]['activity']}" for e in ev],
                       rotation=60, ha="right", fontsize=7, color=INK)
    ax.set_yticks([])
    ax.set_xlim(-0.6, len(ev) - 0.4)
    ax.set_ylim(-len(objs) + 0.4, 0.6)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(axis="x", length=0)
    if title:
        ax.set_title(title, fontsize=10, loc="left", color=INK, pad=14)
    if subtitle:
        ax.text(0, 1, subtitle, fontsize=7, color=MUTED, va="bottom",
                transform=offset_copy(ax.transAxes, fig=ax.figure, y=4, units="points"))


def legend(ax, types, excluded=(), ring=True, ncol=None):
    h = []
    for t in types:
        if t in excluded:
            h.append(Line2D([0], [0], color="none", marker="o", markerfacecolor=MUTED,
                            markeredgecolor="white", markersize=6, label=f"{t} (excluded)"))
        else:
            h.append(Line2D([0], [0], color=COLOR[t], lw=2, linestyle=STYLE[t], marker="o",
                            markersize=5, label=t))
    if ring:
        h.append(Line2D([0], [0], color="none", marker="o", markerfacecolor="white",
                        markeredgecolor=INK, markeredgewidth=1.6, markersize=6,
                        label="start/end event"))
    ax.legend(handles=h, loc="lower left", bbox_to_anchor=(0, 1), ncol=ncol or len(h),
              bbox_transform=offset_copy(ax.transAxes, fig=ax.figure, y=16, units="points"),
              frameon=False, fontsize=7, handlelength=2.6, borderaxespad=0, columnspacing=1.2)


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        # no CreationDate in the PDF, so reruns give byte-identical files
        meta = {"CreationDate": None} if ext == "pdf" else None
        fig.savefig(OUT / f"{name}.{ext}", dpi=200, bbox_inches="tight", metadata=meta)
    plt.close(fig)
    print("wrote", OUT / f"{name}.pdf")


def union(execs):
    s = set()
    for ex in execs:
        s |= set(ex["events"])
    return s


def union_objects(execs):
    s = set()
    for ex in execs:
        s |= set(ex["objects"])
    return s


def ends_of(execs, key):
    s = set()
    for ex in execs:
        s |= set(as_list(ex[key]))
    return s


def lane_fig(name, execs, title, src, excluded=(), w=None):
    events, corr, otype = EV, CORR, OTYPE
    ev = union(execs)
    objs = union_objects(execs)
    h = 1.0 + 0.45 * len(objs)
    w = w or max(5.5, 0.55 * len(ev) + 2.2)
    fig, ax = plt.subplots(figsize=(w, h + 0.6))
    lanes_draw(ax, events, corr, otype, DF, ev, objects=objs, excluded_types=excluded,
               starts=ends_of(execs, "start_event"), ends=ends_of(execs, "end_event"),
               title="", subtitle=f"source: {src}")
    ncol = None if w >= 7 else 2
    ring = any(ex["start_event"] for ex in execs)
    types = [t for t in TYPES if any(OTYPE[o] == t for o in objs)]
    legend(ax, types, excluded, ring=ring, ncol=ncol)
    rows = 1 if ncol is None else -(-(len(types) + ring) // ncol)
    ax.set_title(title, fontsize=10, loc="left", color=INK, pad=22 + 12 * rows)
    save(fig, name)


# --------------------------------------------------------------------- Fig. 7
def fig7(execs):
    starts = sorted({e["start_object"] for e in execs}, key=lambda o: (TYPES.index(OTYPE[o]), natkey(o)))
    ends = sorted({e["end_object"] for e in execs}, key=lambda o: (TYPES.index(OTYPE[o]), natkey(o)))
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    ys = {o: -i for i, o in enumerate(starts)}
    ye = {o: -i * (len(starts) - 1) / max(1, len(ends) - 1) for i, o in enumerate(ends)}
    for ex in execs:
        s, t = ex["start_object"], ex["end_object"]
        ax.annotate("", xy=(1, ye[t]), xytext=(0, ys[s]),
                    arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1, shrinkA=7, shrinkB=7))
    for o, yy in ys.items():
        ax.scatter([0], [yy], s=110, color=COLOR[OTYPE[o]], edgecolors="white", zorder=3)
        ax.text(-0.06, yy, f"{o} ({OTYPE[o]})", ha="right", va="center", fontsize=8)
    for o, yy in ye.items():
        ax.scatter([1], [yy], s=110, color=COLOR[OTYPE[o]], edgecolors="white", zorder=3)
        ax.text(1.06, yy, f"{o} ({OTYPE[o]})", ha="left", va="center", fontsize=8)
    ax.text(0, 0.7, "start object", ha="center", fontsize=8, color=MUTED)
    ax.text(1, 0.7, "end object", ha="center", fontsize=8, color=MUTED)
    ax.set_xlim(-0.9, 1.7)
    ax.set_ylim(-len(starts) + 0.5, 1.0)
    ax.axis("off")
    ax.set_title(f"Fig. 7 - all {len(execs)} start-to-end executions between objects "
                 "with global start/end events", fontsize=9, loc="left")
    ax.text(0, -0.02, "source: results/r1/all_global_executions.json (one arrow = one execution)",
            transform=ax.transAxes, fontsize=7, color=MUTED)
    save(fig, "fig7")


# ---------------------------------------------------------------------- main
if __name__ == "__main__":
    if DATASET != "running_example":
        print("Skipping paper figures: they are defined only for the running_example dataset.")
        raise SystemExit(0)

    EV, CORR, OTYPE = load_events()
    DF = load_df()

    # Fig. 4: whole EKG
    allex = [{"events": list(EV), "objects": list(OTYPE), "start_event": [], "end_event": []}]
    lane_fig("fig4", allex, "Fig. 4 - OCED graph of the running example (21 events, 29 DF edges)",
             "results/r1/df_edges.csv")

    lane_fig("fig5", load("exec_A_O1"), "Fig. 5 - start-to-end execution D[e3 -> e28] = D[A -> O1]",
             "results/r1/exec_A_O1.json")
    lane_fig("fig6", load("notion_SO_Order"),
             "Fig. 6 - case notion D[SupplierOrder -> Order]: A->O1, A->O2, B->O1, B->O2",
             "results/r1/notion_SO_Order.json")
    fig7(load("all_global_executions"))
    lane_fig("fig8_left", load("notion_Order_Payment"),
             "Fig. 8 (left) - D[Order -> Payment] (= D[Order -> Invoice] events)",
             "results/r1/notion_Order_Payment.json")
    lane_fig("fig8_right", load("notion_Payment_Invoice"), "Fig. 8 (right) - D[Payment -> Invoice]",
             "results/r1/notion_Payment_Invoice.json", w=4.5)
    lane_fig("fig9", load("notion_Order_Order"), "Fig. 9 - D[Order -> Order] = D[O2 -> O1]",
             "results/r1/notion_Order_Order.json")
    lane_fig("fig10", load("start_case_Order"), "Fig. 10 - start cases D[Order -> *]",
             "results/r1/start_case_Order.json")
    lane_fig("fig11", load("start_case_Order_noSO"),
             "Fig. 11 - filtered start cases D[Order -> * \\ {SupplierOrder}]",
             "results/r1/start_case_Order_noSO.json", excluded=("Supplier Order",))
    lane_fig("fig12", load("end_case_Order_noSO"),
             "Fig. 12 - filtered end cases D[* -> Order \\ {SupplierOrder}]",
             "results/r1/end_case_Order_noSO.json", excluded=("Supplier Order",))
