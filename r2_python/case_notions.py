"""Object-centric start-to-end case notions: Def. 9 and the "global" restriction of Sect. 5.2."""

from __future__ import annotations

from .behaviour import DF, global_end_events, global_start_events
from .executions import between, case, common_format, end_of, execution, start_of
from .oced import OCEDSet, natkey, union

SELF_PAIRS = (True, False)
GLOBAL_BY = ("object", "type")


def _objects_of_type(d: OCEDSet, t: str) -> list[str]:
    return sorted((o for o in d.objects if d.type[o] == t), key=natkey)


def case_pairs(d: OCEDSet, df: DF, starts, ends, self_pairs: bool = True,
               distinct_types: bool = False) -> list[tuple[str, str]]:
    """Pairs (o_st, o_end) with a non-empty case D[o_st -> o_end], i.e. start(o_st) ≤ end(o_end).

    Ambiguity A3 (Def. 9 vs. Sect. 5.2):
      self_pairs=True  (Def. 9 literally): o_st = o_end is allowed, e.g. D[O1 -> O1].
      self_pairs=False: o_st ≠ o_end.
      distinct_types=True: additionally type(o_st) ≠ type(o_end) (Sect. 5.2, read literally:
                           "pairs of distinct object types"); this removes D[Order -> Order] entirely.
    Interpretation I2: pairs with an empty execution (not start(o_st) ≤ end(o_end)) are not cases.
    """
    out = []
    for s in sorted(starts, key=natkey):
        for t in sorted(ends, key=natkey):
            if s == t and not self_pairs:
                continue
            if distinct_types and d.type[s] == d.type[t]:
                continue
            if between(df, start_of(d, df, s), end_of(d, df, t)):
                out.append((s, t))
    return out


def case_notion(d: OCEDSet, df: DF, t_st: str, t_end: str, self_pairs: bool = True) -> list[dict]:
    """Def. 9: D[T_st -> T_end] = {D[o_st -> o_end] | type(o_st) = T_st, type(o_end) = T_end}
    (non-empty cases only, I2), in the common result format."""
    pairs = case_pairs(d, df, _objects_of_type(d, t_st), _objects_of_type(d, t_end), self_pairs)
    return [record(d, df, s, t) for s, t in pairs]


def behaviour(d: OCEDSet, df: DF, pairs) -> OCEDSet:
    """Def. 9: the behaviour ⋃𝒟[T_st -> T_end] defined by a case notion (union of its cases)."""
    return union(case(d, df, s, t) for s, t in pairs)


def record(d: OCEDSet, df: DF, s: str, t: str) -> dict:
    i, o = start_of(d, df, s), end_of(d, df, t)
    return common_format(f"{s}_{t}", s, t, i, o, execution(d, df, i, o))


# ------------------------------------------------------------------------------------------------
# Sect. 5.2: restriction to objects with a global start / end event
# ------------------------------------------------------------------------------------------------
def global_objects(d: OCEDSet, df: DF, by: str = "object") -> tuple[list[str], list[str]]:
    """Start objects and end objects admitted by the Sect. 5.2 restriction ("we restrict start object
    types to those where objects have a global start event ... correspondingly for end object types").

    Ambiguity A4:
      by="object": every object whose start (end) event is a global start (end) event, start(O) / end(O).
      by="type":   every object of a type all of whose objects have a global start (end) event.
    """
    if by not in GLOBAL_BY:
        raise ValueError(f"by must be one of {GLOBAL_BY}")
    gs, ge = global_start_events(d, df), global_end_events(d, df)
    st = {o for o in d.objects if start_of(d, df, o) in gs}
    en = {o for o in d.objects if end_of(d, df, o) in ge}
    if by == "type":
        types = {d.type[o] for o in d.objects}
        st_types = {t for t in types if all(o in st for o in _objects_of_type(d, t))}
        en_types = {t for t in types if all(o in en for o in _objects_of_type(d, t))}
        st = {o for o in d.objects if d.type[o] in st_types}
        en = {o for o in d.objects if d.type[o] in en_types}
    return sorted(st, key=natkey), sorted(en, key=natkey)


def global_executions(d: OCEDSet, df: DF, by: str = "object", self_pairs: bool = True,
                      distinct_types: bool = False) -> list[dict]:
    """All non-empty cases D[o_st -> o_end] between objects with a global start / end event (Sect. 5.2)."""
    st, en = global_objects(d, df, by)
    return [record(d, df, s, t) for s, t in case_pairs(d, df, st, en, self_pairs, distinct_types)]


def type_matrix(d: OCEDSet, records: list[dict]) -> dict[str, int]:
    """Number of cases per (start type, end type)."""
    counts = {}
    for r in records:
        k = f"{d.type[r['start_object']]} -> {d.type[r['end_object']]}"
        counts[k] = counts.get(k, 0) + 1
    return dict(sorted(counts.items()))
