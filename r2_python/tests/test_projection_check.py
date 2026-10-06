"""Projection check (F6): Def. 7 executions are convex, so projection keeps DF; Def. 11 ones are not."""

from r2_python.behaviour import directly_follows, without_objects
from r2_python.executions import between
from r2_python.generalized import end_case, excluded_objects
from r2_python.projection_check import (check_filtered, check_unfiltered, convexity_witnesses,
                                        union_check)

from .conftest import mini


def test_unfiltered_convex_and_df_preserved(running, running_df):
    for i in running.events:
        for o in running.events:
            if between(running_df, i, o):
                r = check_unfiltered(running, running_df, i, o)
                assert r["convex"] and r["df_equal"], (i, o, r)


def test_filtered_running_example(running, running_df):
    X = excluded_objects(running, types=["Supplier Order"])
    # D[e6 -> e11 \ X]: A's edges e6-e8-e10-e11 are excluded, the remaining path is e6 ⋖_X1 e11
    r = check_filtered(running, running_df, "e6", "e11", X)
    assert r["convex_in_filtered"] and not r["convex_in_D"]
    assert r["convexity_witnesses_in_D"] == ["e8", "e10"]
    assert r["spurious"] == [{"edge": ["e6", "A", "e11"], "dropped": ["e8", "e10"]}]
    # every filtered execution is convex in the filtered DF graph and loses no filtered-DF edge
    fdf = without_objects(running_df, X)
    for i in running.events:
        for o in running.events:
            if between(fdf, i, o):
                r = check_filtered(running, running_df, i, o, X)
                assert r["convex_in_filtered"] and not r["missing"]
    # Fig. 12, global_on="filtered": *->O2 \ X reintroduces e7 ⋖_B e19 via the union
    u = union_check(running, running_df, end_case(running, running_df, "O2", "global", X, "filtered")[0], X)
    assert ("e7", "B", "e19") in u["reintroduced"] and u["spurious"] == [("e19", "B", "e21")]


def test_filtered_mini():
    """x: e1@1 -> e2@2 -> e3@3 ; y: e1@1 -> e3@3 ; X = {x}.
    df(D, O\\X) = {e1 ⋖_y e3}, so D[e1 -> e3 \\ X] = {e1, e3} (e2 dropped; e1 ≤ e2 ≤ e3 in D: not convex).
    The projection keeps x (via e1, e3) and recomputes e1 ⋖_x e3: spurious, dropped e2."""
    d = mini({"e1": ("a", 1), "e2": ("b", 2), "e3": ("c", 3)},
             {"e1": ["x", "y"], "e2": ["x"], "e3": ["x", "y"]}, {"x": "T", "y": "U"})
    df = directly_follows(d)
    assert convexity_witnesses(df, {"e1", "e3"}) == ["e2"]
    r = check_filtered(d, df, "e1", "e3", {"x"})
    assert r["spurious"] == [{"edge": ["e1", "x", "e3"], "dropped": ["e2"]}] and r["reintroduced"] == []
    assert check_unfiltered(d, df, "e1", "e3")["df_equal"]
