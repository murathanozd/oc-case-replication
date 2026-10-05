"""Step 3: Def. 7 (executions), Def. 8 (cases), and the properties stated after Def. 7."""

import pytest

from r2_python.behaviour import directly_follows, end_events, is_df_path, leq, start_events
from r2_python.executions import (Def8AssumptionError, between, case, case_record, def8_violations,
                                  execution, object_start_end)

from .conftest import mini


def test_A_O1(running, running_df):
    """Fig. 5 / Sect. 4: D[e3 -> e28] = D[A -> O1]. Worked out from the DF edges by hand:
    descendants of e3 ∩ ancestors of e28 = {e3, e6, e8, e10, e11, e27, e28};
    objects: A, X1, X2, X3 (e6, e8, e10, e11), O1 (e27, e28), Y1 (e27)."""
    r = case_record(running, running_df, "A", "O1")
    assert r["start_event"] == "e3" and r["end_event"] == "e28"
    assert r["events"] == ["e3", "e6", "e8", "e10", "e11", "e27", "e28"]
    assert r["objects"] == ["A", "O1", "X1", "X2", "X3", "Y1"]


def test_empty_execution(running, running_df):
    # no execution from O1 to O2: e1 is not ≤ e34
    assert between(running_df, "e1", "e34") == set()
    assert execution(running, running_df, "e1", "e34").events == set()


def test_properties_after_def7(running, running_df):
    """For every pair i ≤ o: D[i -> o] has the single start event i and the single end event o
    (computed on D[i -> o] itself), and every event e lies on a df-path i...e...o in D[i -> o] and in D."""
    for i in running.events:
        for o in running.events:
            if not leq(running_df, i, o):
                continue
            ex = execution(running, running_df, i, o)
            exdf = directly_follows(ex)
            assert start_events(ex, exdf) == {i}
            assert end_events(ex, exdf) == {o}
            for e in ex.events:
                assert leq(exdf, i, e) and leq(exdf, e, o)
                assert leq(running_df, i, e) and leq(running_df, e, o)
            # the projection does not change DF between included events (E_i^o is convex)
            assert exdf.triples == {t for t in running_df.triples if t[0] in ex.events and t[2] in ex.events}


def test_def8_running_has_single_start_end(running, running_df):
    assert def8_violations(running, running_df) == {}
    se = object_start_end(running, running_df)
    assert se["X1"] == ({"e6"}, {"e27"}) and se["P1"] == ({"e29"}, {"e30"})


def test_def8_two_start_events():
    """Object c has two events at the same, earliest time (e1@0, e2@0) and one later event e3@5.
    strict: start({c}) = {e1, e2} -> Def. 8 assumption violated, case() must raise and name c.
    break_by_id: e1 ⋖ e2 ⋖ e3, start({c}) = {e1}, D[c -> c] = {e1, e2, e3}."""
    d = mini({"e1": ("a", 0), "e2": ("b", 0), "e3": ("c", 5)},
             {"e1": ["c"], "e2": ["c"], "e3": ["c"]}, {"c": "T"})
    s = directly_follows(d, "strict")
    assert def8_violations(d, s) == {"c": (["e1", "e2"], ["e3"])}
    with pytest.raises(Def8AssumptionError, match="c"):
        case(d, s, "c", "c")
    b = directly_follows(d, "break_by_id")
    assert case(d, b, "c", "c").events == {"e1", "e2", "e3"}


def test_mini_converging():
    """x: e1@1 -> e3@3; y: e2@2 -> e3@3 (e3 synchronizes x and y); z: e3@3 -> e4@4.
    D[x -> z] = {e1, e3, e4}, objects {x, y, z} (y via e3); D[y -> x] = {e2, e3} (end(x) = e3);
    D[x -> y] = {e1, e3}; there is no execution from e2 to e1."""
    d = mini({"e1": ("a", 1), "e2": ("b", 2), "e3": ("c", 3), "e4": ("d", 4)},
             {"e1": ["x"], "e2": ["y"], "e3": ["x", "y", "z"], "e4": ["z"]},
             {"x": "X", "y": "Y", "z": "Z"})
    df = directly_follows(d)
    xz = case(d, df, "x", "z")
    assert xz.events == {"e1", "e3", "e4"} and xz.objects == {"x", "y", "z"}
    assert case(d, df, "y", "x").events == {"e2", "e3"}
    assert case(d, df, "x", "y").events == {"e1", "e3"}
    assert execution(d, df, "e2", "e1").events == set()
    assert is_df_path(df, ["e1", "e3", "e4"])
