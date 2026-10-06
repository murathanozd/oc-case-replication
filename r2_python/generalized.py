"""Generalized OCED cases (Sect. 5.3): start cases / end cases (Def. 10) and filtered start-to-end
executions (Def. 11).

Def. 11 is computed as Def. 7 on the DF graph without the df-edges of excluded objects
(reachability, no path enumeration), followed by the projection onto the *original* OCED-set.
"""

from __future__ import annotations

from .behaviour import DF, directly_follows, end_events, start_events, without_objects
from .executions import between, end_of, start_of
from .oced import OCEDSet, natkey, project, union

ENDS = ("global", "any")
GLOBAL_ON = ("full", "filtered")


def excluded_objects(d: OCEDSet, types=(), objects=()) -> set[str]:
    """X given as object types (all objects of those types) and/or as an object set."""
    return {o for o in d.objects if d.type[o] in set(types)} | set(objects)


def filtered_execution(d: OCEDSet, df: DF, i: str, o: str, X=frozenset()) -> OCEDSet:
    """Def. 11: D[i -> o \\ X] = Proj_{E_i^o|X̄} D with E_i^o|X̄ = events on a df-path from i to o in
    df(D, O \\ X). The projection keeps every object correlated to an included event, also objects in X."""
    return project(d, between(without_objects(df, X), i, o))


def boundary_objects(d: OCEDSet, df: DF, side: str, ends: str = "global", X=frozenset(),
                     global_on: str = "full") -> list[str]:
    """O_end (side="end") or O_start (side="start") of Def. 10.

    ends="global" (Def. 10): objects whose end (start) event is a global end (start) event,
                             O_end = {o | end(o) ⊆ end(O)}.
    ends="any"   (variant):  every object; its end (start) event need not be global.
    Ambiguity A5 (filtered cases, X non-empty), where the global end (start) events are determined:
      global_on="full":     end(O) on the full DF graph (before removing X's edges);
      global_on="filtered": end(O \\ X) on df(D, O \\ X) (after removing X's edges).
    start(o) / end(o) of each object are always taken from the full DF graph.
    """
    if ends not in ENDS or global_on not in GLOBAL_ON:
        raise ValueError("bad variant")
    if ends == "any":
        return sorted(d.objects, key=natkey)
    if global_on == "full" or not X:
        g_df, g_objs = df, None
    else:
        g_df, g_objs = without_objects(df, X), d.objects - set(X)
    if side == "end":
        glob = end_events(d, g_df, g_objs)
        return sorted((o for o in d.objects if end_of(d, df, o) in glob), key=natkey)
    glob = start_events(d, g_df, g_objs)
    return sorted((o for o in d.objects if start_of(d, df, o) in glob), key=natkey)


def start_case(d: OCEDSet, df: DF, o: str, ends: str = "global", X=frozenset(), global_on: str = "full"):
    """Def. 10 (+ Def. 11): D[o -> * \\ X] = ⋃{D[o -> o_end \\ X] | o_end ∈ O_end}.
    Returns (projected OCED-set, contributing end objects, their end events)."""
    i = start_of(d, df, o)
    parts, objs, evs = [], [], set()
    for t in boundary_objects(d, df, "end", ends, X, global_on):
        ex = filtered_execution(d, df, i, end_of(d, df, t), X)
        if ex.events:
            parts.append(ex)
            objs.append(t)
            evs.add(end_of(d, df, t))
    return union(parts), objs, evs


def end_case(d: OCEDSet, df: DF, o: str, starts: str = "global", X=frozenset(), global_on: str = "full"):
    """Def. 10 (+ Def. 11): D[* -> o \\ X] = ⋃{D[o_st -> o \\ X] | o_st ∈ O_start}."""
    t = end_of(d, df, o)
    parts, objs, evs = [], [], set()
    for s in boundary_objects(d, df, "start", starts, X, global_on):
        ex = filtered_execution(d, df, start_of(d, df, s), t, X)
        if ex.events:
            parts.append(ex)
            objs.append(s)
            evs.add(start_of(d, df, s))
    return union(parts), objs, evs


def case_record(d: OCEDSet, df: DF, side: str, o: str, variant: str = "global", X=frozenset(),
                global_on: str = "full") -> dict:
    """Common result format for a start case ("o_*") or end case ("*_o"), plus details:
    the contributing other-side objects, excluded objects remaining in the projection, and df-edges of
    the projection (recomputed by Def. 3 on the projection) that are not df-edges of D."""
    if side == "start":
        ex, others, evs = start_case(d, df, o, variant, X, global_on)
        rec = {"execution_id": f"{o}_*", "start_object": o, "end_object": "*",
               "start_event": start_of(d, df, o), "end_event": sorted(evs, key=natkey)}
        key = "end_objects"
    else:
        ex, others, evs = end_case(d, df, o, variant, X, global_on)
        rec = {"execution_id": f"*_{o}", "start_object": "*", "end_object": o,
               "start_event": sorted(evs, key=natkey), "end_event": end_of(d, df, o)}
        key = "start_objects"
    rec |= {"events": ex.sorted_events(), "objects": ex.sorted_objects(), key: others}
    if X:
        proj_df = directly_follows(ex, df.ties)
        rec["excluded_objects_in_projection"] = sorted(set(ex.objects) & set(X), key=natkey)
        rec["projection_df_edges_of_excluded_objects"] = sorted(
            ([a, x, b] for a, x, b in proj_df.triples if x in X), key=lambda t: (natkey(t[0]), natkey(t[2]), t[1]))
        rec["projection_df_edges_not_in_D"] = sorted(
            ([a, x, b] for a, x, b in proj_df.triples - df.triples), key=lambda t: (natkey(t[0]), natkey(t[2]), t[1]))
    return rec


def type_records(d: OCEDSet, df: DF, side: str, otype: str, **kw) -> list[dict]:
    """Lift to object types: one start (end) case per object of the type."""
    return [case_record(d, df, side, o, **kw)
            for o in sorted((o for o in d.objects if d.type[o] == otype), key=natkey)]
