"""Behaviour of an OCED-set: directly-follows per object (Def. 3), the partial order ≤ (Def. 4),
the OCED-graph view (Def. 5), df-paths and start/end events (Def. 6), and Lemma 1.

≤ is never materialized and paths are never enumerated: everything is reachability on the
event-level DF graph (BFS), so it scales to larger logs (R3).
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from functools import cached_property
from itertools import groupby

from .oced import OCEDSet, natkey

TIES = ("strict", "break_by_id")
READINGS = ("intended", "literal")


@dataclass(frozen=True)
class DF:
    """The local directly-follows relation ⋖ ⊆ E × O × E of an OCED-set (Def. 3), with indexes."""
    triples: frozenset[tuple[str, str, str]]      # (e, o, e'): e' directly follows e from the perspective of o
    succ: dict[str, frozenset[str]]               # event-level graph: e -> {e' | ∃o: e ⋖_o e'}
    pred: dict[str, frozenset[str]]
    ties: str

    @cached_property
    def by_pair(self) -> dict[tuple[str, str], frozenset[str]]:
        """(e, e') -> {o | e ⋖_o e'}; built once per DF."""
        idx = defaultdict(set)
        for a, o, b in self.triples:
            idx[(a, b)].add(o)
        return {k: frozenset(v) for k, v in idx.items()}

    def edges(self, objs=None, excluded=None):
        """DF triples whose object is in `objs` (all if None) and not in `excluded`."""
        return {(e, o, f) for (e, o, f) in self.triples
                if (objs is None or o in objs) and (excluded is None or o not in excluded)}


def directly_follows(d: OCEDSet, ties: str = "strict") -> DF:
    """Def. 3: e ⋖_o e' iff (e, o), (e', o) ∈ corr, #time(e) < #time(e'), and no e'' correlated to o
    with #time(e) < #time(e'') < #time(e').

    Ambiguity A1 (equal timestamps):
      ties="strict"      (paper, default): literal Def. 3. Tied events of o are not ordered; each event is
                          followed by *all* events of o at the next larger timestamp (fan-out / fan-in).
      ties="break_by_id": order the events of o totally by (timestamp, natural order of the event id)
                          and link consecutive events.
    """
    if ties not in TIES:
        raise ValueError(f"ties must be one of {TIES}")
    triples = set()
    for o in d.objects:
        evs = sorted(d.o2e[o], key=lambda e: (d.time(e), natkey(e)))
        if ties == "break_by_id":
            triples.update((a, o, b) for a, b in zip(evs, evs[1:]))
        else:
            groups = [list(g) for _, g in groupby(evs, key=d.time)]
            for g1, g2 in zip(groups, groups[1:]):
                triples.update((a, o, b) for a in g1 for b in g2)
    succ, pred = defaultdict(set), defaultdict(set)
    for a, _, b in triples:
        succ[a].add(b)
        pred[b].add(a)
    return DF(frozenset(triples),
              {e: frozenset(succ[e]) for e in d.events},
              {e: frozenset(pred[e]) for e in d.events},
              ties)


# ------------------------------------------------------------------------------------------------
# Def. 4 / Lemma 1: ≤ as reachability
# ------------------------------------------------------------------------------------------------
def _reach(start, nxt) -> set[str]:
    seen, todo = {start}, deque([start])
    while todo:
        for n in nxt.get(todo.popleft(), ()):
            if n not in seen:
                seen.add(n)
                todo.append(n)
    return seen


def descendants(df: DF, e: str) -> set[str]:
    """{e' | e ≤ e'} (reflexive)."""
    return _reach(e, df.succ)


def ancestors(df: DF, e: str) -> set[str]:
    """{e' | e' ≤ e} (reflexive)."""
    return _reach(e, df.pred)


def leq(df: DF, e: str, e2: str) -> bool:
    """Def. 4: e ≤ e' in the reflexive-transitive closure of {(e, e') | ∃o: e ⋖_o e'}, computed by
    reachability (Lemma 1: e < e' iff there is a df-path from e to e')."""
    return e == e2 or e2 in descendants(df, e)


# ------------------------------------------------------------------------------------------------
# Def. 6: df-paths, start and end events
# ------------------------------------------------------------------------------------------------
def is_df_path(df: DF, seq, objs=None) -> bool:
    """Def. 6: ⟨e1, ..., ek⟩ ∈ df(D, O') iff for 1 ≤ i < k there is o_i ∈ O' with e_i ⋖_{o_i} e_{i+1}.
    objs=None means O' = O (all objects)."""
    seq = list(seq)
    if not seq or any(e not in df.succ for e in seq):      # empty or unknown events: not a df-path
        return False
    objs = None if objs is None else set(objs)
    for a, b in zip(seq, seq[1:]):
        os = df.by_pair.get((a, b), frozenset())
        if not os or (objs is not None and not os & objs):
            return False
    return True


def start_events(d: OCEDSet, df: DF, objs=None, reading: str = "intended") -> set[str]:
    """Def. 6: e ∈ start(O') iff there is no o ∈ O' and no e' with e' ⋖_o e. objs=None means O' = O.

    Ambiguity A2:
      reading="intended" (default): e must also be correlated to some o ∈ O'.
      reading="literal": no such condition; every event without an O'-predecessor qualifies, including
                         events that have nothing to do with O'.
    """
    return _boundary(d, df, objs, reading, incoming=True)


def end_events(d: OCEDSet, df: DF, objs=None, reading: str = "intended") -> set[str]:
    """Def. 6 (end events, "defined correspondingly"): no o ∈ O' and no e' with e ⋖_o e'."""
    return _boundary(d, df, objs, reading, incoming=False)


def _boundary(d, df, objs, reading, incoming):
    if reading not in READINGS:
        raise ValueError(f"reading must be one of {READINGS}")
    objs = d.objects if objs is None else set(objs)
    blocked = {b if incoming else a for (a, o, b) in df.triples if o in objs}
    candidates = d.events if reading == "literal" else {e for o in objs for e in d.o2e[o]}
    return set(candidates) - blocked


def global_start_events(d: OCEDSet, df: DF) -> set[str]:
    """start(O): events with no DF predecessor at all (Sect. 5.2/5.3: "global" start events)."""
    return start_events(d, df)


def global_end_events(d: OCEDSet, df: DF) -> set[str]:
    """end(O): events with no DF successor at all."""
    return end_events(d, df)


def is_maximal_df_path(d: OCEDSet, df: DF, seq, objs=None) -> bool:
    """Def. 6: a df-path wrt. O' is maximal iff e1 ∈ start(O') and ek ∈ end(O')."""
    seq = list(seq)
    return (is_df_path(df, seq, objs) and seq[0] in start_events(d, df, objs)
            and seq[-1] in end_events(d, df, objs))


# ------------------------------------------------------------------------------------------------
# Def. 5: OCED-graph
# ------------------------------------------------------------------------------------------------
def oced_graph(d: OCEDSet, df: DF):
    """Def. 5: G = (N, R, type, #) with N = E ∪ O and R = corr ∪ rel ∪ ⋖ (a hyper-graph: ⋖ may hold
    (e, o1, e') and (e, o2, e') for the same pair). Edges are returned as tagged tuples."""
    nodes = set(d.events) | set(d.objects)
    edges = ({("corr", e, o) for (e, o) in d.corr}
             | {("rel", a, b) for (a, b) in d.rel}
             | {("df", e, o, f) for (e, o, f) in df.triples})
    return nodes, edges


def without_objects(df: DF, excluded) -> DF:
    """The DF relation restricted to df-edges of objects not in `excluded`, i.e. df(D, O \\ X) of Def. 6/11:
    df-paths in the result are exactly the df-paths of D that use no edge (e, x, e') with x ∈ X."""
    excluded = set(excluded)
    triples = frozenset(t for t in df.triples if t[1] not in excluded)
    succ, pred = defaultdict(set), defaultdict(set)
    for a, _, b in triples:
        succ[a].add(b)
        pred[b].add(a)
    return DF(triples, {e: frozenset(succ[e]) for e in df.succ},
              {e: frozenset(pred[e]) for e in df.pred}, df.ties)
