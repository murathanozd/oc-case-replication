"""Object-centric start-to-end executions and cases: Def. 7 and Def. 8 (Sect. 4, 5.1)."""

from __future__ import annotations

from .behaviour import DF, ancestors, descendants, directly_follows, end_events, start_events
from .oced import OCEDSet, natkey, project


class Def8AssumptionError(ValueError):
    """Def. 8 assumes that every object has exactly one start and one end event."""


def between(df: DF, i: str, o: str) -> set[str]:
    """E_i^o = {e ∈ E | i ≤ e ≤ o} = descendants(i) ∩ ancestors(o) (empty unless i ≤ o)."""
    return descendants(df, i) & ancestors(df, o)


def execution(d: OCEDSet, df: DF, i: str, o: str) -> OCEDSet:
    """Def. 7: D[i -> o] = Proj_{E_i^o} D."""
    return project(d, between(df, i, o))


def object_start_end(d: OCEDSet, df: DF) -> dict[str, tuple[set[str], set[str]]]:
    """start(o) = start({o}) and end(o) = end({o}) for every object (Def. 6, Sect. 5.1)."""
    return {o: (start_events(d, df, {o}), end_events(d, df, {o})) for o in d.objects}


def def8_violations(d: OCEDSet, df: DF) -> dict[str, tuple[list[str], list[str]]]:
    """Objects with != 1 start or != 1 end event (violating Def. 8's assumption)."""
    out = {}
    for o, (s, t) in object_start_end(d, df).items():
        if len(s) != 1 or len(t) != 1:
            out[o] = (sorted(s, key=natkey), sorted(t, key=natkey))
    return dict(sorted(out.items(), key=lambda kv: natkey(kv[0])))


def start_of(d: OCEDSet, df: DF, o: str) -> str:
    return _single(d, df, o, start_events(d, df, {o}), "start")


def end_of(d: OCEDSet, df: DF, o: str) -> str:
    return _single(d, df, o, end_events(d, df, {o}), "end")


def _single(d, df, o, evs, kind):
    if len(evs) != 1:
        raise Def8AssumptionError(
            f"Def. 8 assumes a single {kind} event, but {o} has {sorted(evs, key=natkey)}. "
            f"All objects violating the assumption: {def8_violations(d, df)}")
    return next(iter(evs))


def case(d: OCEDSet, df: DF, o_st: str, o_end: str) -> OCEDSet:
    """Def. 8: D[o_st -> o_end] = D[start(o_st) -> end(o_end)]."""
    return execution(d, df, start_of(d, df, o_st), end_of(d, df, o_end))


def common_format(execution_id: str, start_object, end_object, start_event, end_event,
                  ex: OCEDSet) -> dict:
    """R1's common result format, with sorted lists."""
    return {"execution_id": execution_id, "start_object": start_object, "end_object": end_object,
            "start_event": start_event, "end_event": end_event,
            "events": ex.sorted_events(), "objects": ex.sorted_objects()}


def case_record(d: OCEDSet, df: DF, o_st: str, o_end: str) -> dict:
    i, o = start_of(d, df, o_st), end_of(d, df, o_end)
    return common_format(f"{o_st}_{o_end}", o_st, o_end, i, o, execution(d, df, i, o))


__all__ = ["Def8AssumptionError", "between", "execution", "object_start_end", "def8_violations",
           "start_of", "end_of", "case", "case_record", "common_format", "directly_follows"]
