"""OCED-sets (Def. 1, Def. 2) and the operations of Sect. 4 (E[O'], O[E'], restriction, selection,
projection), implemented from Fahland & Montali, "What is an Object-Centric Case?" (2026).

Def. 1: D = (O, E, type, corr, rel, #) with O ∩ E = ∅, type: O -> OType ∪ E -> EType,
corr ⊆ E × O, rel ⊆ O × O, and attributes # where every event carries a timestamp.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from dataclasses import dataclass, field
from functools import cached_property
from datetime import datetime
from itertools import permutations
from pathlib import Path

# The 5 object types of the running example (Sect. 2: "Orders, Supplier Orders, Items, Invoices,
# Payments"), as CSV column -> object type. Actor, Order Details and Tray are not objects.
OBJECT_COLUMNS = {
    "Order": "Order",
    "Supplier Order": "Supplier Order",
    "Item": "Item",
    "Invoice": "Invoice",
    "Payment": "Payment",
}
TIME_FORMAT = "%d.%m.%Y %H:%M:%S"


def natkey(s: str):
    """Natural sort key: e2 < e10, X1 < X2."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


@dataclass(frozen=True)
class OCEDSet:
    objects: frozenset[str]
    events: frozenset[str]
    type: dict[str, str]                      # object -> object type, event -> activity (event type)
    corr: frozenset[tuple[str, str]]          # (event, object)
    rel: frozenset[tuple[str, str]]           # (object, object)
    attrs: dict[str, dict] = field(default_factory=dict)  # #: node -> {attribute: value}; events have "time"

    def __post_init__(self):
        assert not (self.objects & self.events), "Def. 1: O ∩ E must be empty"
        assert all(e in self.events and o in self.objects for e, o in self.corr), "corr ⊆ E × O"
        assert all(a in self.objects and b in self.objects for a, b in self.rel), "rel ⊆ O × O"
        assert all("time" in self.attrs.get(e, {}) for e in self.events), "every event has a timestamp"

    def time(self, e: str) -> datetime:
        return self.attrs[e]["time"]

    @cached_property
    def e2o(self) -> dict[str, frozenset[str]]:
        """Index of corr: event -> correlated objects."""
        idx = defaultdict(set)
        for e, o in self.corr:
            idx[e].add(o)
        return {e: frozenset(idx[e]) for e in self.events}

    @cached_property
    def o2e(self) -> dict[str, frozenset[str]]:
        """Index of corr: object -> correlated events."""
        idx = defaultdict(set)
        for e, o in self.corr:
            idx[o].add(e)
        return {o: frozenset(idx[o]) for o in self.objects}

    def objects_of_event(self, e: str) -> frozenset[str]:
        return self.e2o[e]

    def sorted_events(self, events=None) -> list[str]:
        return sorted(self.events if events is None else events, key=natkey)

    def sorted_objects(self, objects=None) -> list[str]:
        return sorted(self.objects if objects is None else objects, key=natkey)


# ------------------------------------------------------------------------------------------------
# Loading (Sect. 3: Table 1 -> OCED-set "by simple rules")
# ------------------------------------------------------------------------------------------------
def load_csv(path: str | Path) -> OCEDSet:
    """One event per row: event id from `EventID`, event type (activity) from `event`, timestamp from
    `time` (dd.mm.yyyy HH:MM:SS); every comma-separated id in an object column is an object of that
    column's type, and (event, object) ∈ corr. Returns the set made relation-consistent (Def. 2)."""
    events, objects, types, corr, attrs = set(), set(), {}, set(), {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            e = row["EventID"].strip()
            events.add(e)
            types[e] = row["event"].strip()
            attrs[e] = {"time": datetime.strptime(row["time"].strip(), TIME_FORMAT)}
            for column, otype in OBJECT_COLUMNS.items():
                for o in (v.strip() for v in (row.get(column) or "").split(",")):
                    if not o:
                        continue
                    if o in types and o in objects and types[o] != otype:
                        raise ValueError(f"object {o} has two types: {types[o]}, {otype}")
                    objects.add(o)
                    types[o] = otype
                    corr.add((e, o))
    for o in objects:
        attrs[o] = {}
    d = OCEDSet(frozenset(objects), frozenset(events), types, frozenset(corr), frozenset(), attrs)
    return make_relation_consistent(d)


# ------------------------------------------------------------------------------------------------
# Def. 2: relation-consistency
# ------------------------------------------------------------------------------------------------
def make_relation_consistent(d: OCEDSet) -> OCEDSet:
    """Sect. 3: "we add (o, o') ∈ rel whenever ∃e ∈ E : (e, o), (e, o') ∈ corr".
    Interpretation I1 (see docs/r2_log.md): only for o ≠ o' (no self-loops; Fig. 2 shows none).
    Both (o, o') and (o', o) are added, as the rule is symmetric in o and o'."""
    rel = set(d.rel)
    for e in d.events:
        rel.update(permutations(d.objects_of_event(e), 2))
    return OCEDSet(d.objects, d.events, d.type, d.corr, frozenset(rel), d.attrs)


def is_relation_consistent(d: OCEDSet) -> bool:
    """Def. 2: any two (distinct, I1) objects correlated to the same event are related in some direction."""
    for e in d.events:
        for o, o2 in permutations(d.objects_of_event(e), 2):
            if (o, o2) not in d.rel and (o2, o) not in d.rel:
                return False
    return True


# ------------------------------------------------------------------------------------------------
# Sect. 4: operations on OCED
# ------------------------------------------------------------------------------------------------
def E_of(d: OCEDSet, objs) -> set[str]:
    """E[O'] = {e ∈ E | ∃o ∈ O' : (e, o) ∈ corr}."""
    return set().union(*(d.o2e[o] for o in objs))


def O_of(d: OCEDSet, evs) -> set[str]:
    """O[E'] = {o ∈ O | ∃e ∈ E' : (e, o) ∈ corr}."""
    return set().union(*(d.e2o[e] for e in evs))


def restrict(d: OCEDSet, objs, evs) -> OCEDSet:
    """Res_{O',E'} D = (O', E', type|O'∪E', corr|E'×O', rel|O'×O', #|O'∪E')."""
    objs, evs = frozenset(objs), frozenset(evs)
    keep = objs | evs
    return OCEDSet(
        objs, evs,
        {k: v for k, v in d.type.items() if k in keep},
        frozenset((e, o) for (e, o) in d.corr if e in evs and o in objs),
        frozenset((a, b) for (a, b) in d.rel if a in objs and b in objs),
        {k: v for k, v in d.attrs.items() if k in keep},
    )


def select(d: OCEDSet, objs) -> OCEDSet:
    """Sel_{O'} D = Res_{O', E[O']} D."""
    return restrict(d, objs, E_of(d, objs))


def project(d: OCEDSet, evs) -> OCEDSet:
    """Proj_{E'} D = Res_{O[E'], E'} D. (The directly-follows relation of the result is recomputed from
    the result itself, Def. 3; the paper notes that projection may alter it.)"""
    return restrict(d, O_of(d, evs), evs)


def is_subset(d1: OCEDSet, d2: OCEDSet) -> bool:
    """Sect. 4: D' ⊆ D iff D' is an element-wise subset of D (objects, events, corr, rel, and
    type / attributes agree on the shared elements)."""
    return (d1.objects <= d2.objects and d1.events <= d2.events and d1.corr <= d2.corr
            and d1.rel <= d2.rel and all(d2.type.get(k) == v for k, v in d1.type.items())
            and all(d2.attrs.get(k) == v for k, v in d1.attrs.items()))


def union(sets) -> OCEDSet:
    """Sect. 4: element-wise union D ∪ D' (and ⋃𝒟 for a finite set 𝒟). Assumes the sets come from the
    same OCED-set, so type and attributes agree on shared elements. The union of nothing is empty."""
    sets = list(sets)
    objs, evs, corr, rel, types, attrs = set(), set(), set(), set(), {}, {}
    for s in sets:
        objs |= s.objects
        evs |= s.events
        corr |= s.corr
        rel |= s.rel
        types.update(s.type)
        attrs.update(s.attrs)
    return OCEDSet(frozenset(objs), frozenset(evs), types, frozenset(corr), frozenset(rel), attrs)
