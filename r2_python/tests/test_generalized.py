"""Step 5: Def. 10 (start/end cases) and Def. 11 (filtered executions), A5 (global_on full/filtered).

Hand derivation, X = {A, B} (Supplier Orders); df-edges of A, B removed:
  remaining edges out of e2: e2 ⋖_O2 e5, e5 ⋖_O2 e7, e5 ⋖_I2 e9, e7 ⋖_O2 e33 (e7 ⋖_B e19 removed)
  global starts on the full graph: e1 e2 e3 e4 e29; on df(D, O\\X): e1 e2 e6 e19 e29
  (e6, e19 lose their only incoming edges e3 ⋖_A e6, e7 ⋖_B e19; e3, e4 are correlated only to X).
  End case of O1 (end e28), filtered:
    full:     from e1: e1 e18 e27 e28; from e2: e28 unreachable (e7 ⋖_B e19 removed); e3, e4: no
              remaining out-edges -> {e1, e18, e27, e28}
    filtered: plus from e6: e6 e10 e11 e27 e28 (X1, X2); from e19: e19 e20 e27 e28 (Y1)
              -> {e1, e6, e10, e11, e18, e19, e20, e27, e28}
"""

from r2_python.behaviour import without_objects
from r2_python.generalized import boundary_objects, case_record, excluded_objects, filtered_execution, type_records


def ev(recs):
    return {r["execution_id"]: r["events"] for r in recs}


def test_filtered_execution_keeps_excluded_objects(running, running_df):
    X = excluded_objects(running, types=["Supplier Order"])
    ex = filtered_execution(running, running_df, "e2", "e34", X)     # D[O2 -> O2 \ SO]
    assert sorted(ex.events) == sorted(["e2", "e5", "e7", "e33", "e34"])
    assert "B" in ex.objects                                           # B is correlated to e7


def test_without_objects_removes_only_X_edges(running_df):
    dx = without_objects(running_df, {"A", "B"})
    assert all(o not in ("A", "B") for _, o, _ in dx.triples)
    assert len(running_df.triples) - len(dx.triples) == 8              # A: 4 edges, B: 4 edges
    assert dx.succ["e7"] == {"e33"}                                     # e7 ⋖_B e19 removed


def test_start_case_unfiltered(running, running_df):
    g = ev(type_records(running, running_df, "start", "Order", variant="global"))
    assert g["O1_*"] == ["e1", "e18", "e27", "e28", "e30"]
    assert g == ev(type_records(running, running_df, "start", "Order", variant="any"))


def test_start_case_filtered_same_for_both_readings(running, running_df):
    X = excluded_objects(running, types=["Supplier Order"])
    full = type_records(running, running_df, "start", "Order", X=X, global_on="full")
    filt = type_records(running, running_df, "start", "Order", X=X, global_on="filtered")
    assert ev(full) == ev(filt)
    assert ev(full)["O2_*"] == ["e2", "e5", "e7", "e9", "e30", "e33", "e34"]
    assert boundary_objects(running, running_df, "end", "global", X, "full") == \
        boundary_objects(running, running_df, "end", "global", X, "filtered") == ["I1", "I2", "O1", "O2", "P1"]


def test_end_case_filtered_readings_differ(running, running_df):
    X = excluded_objects(running, types=["Supplier Order"])
    full = ev(type_records(running, running_df, "end", "Order", X=X, global_on="full"))
    filt = ev(type_records(running, running_df, "end", "Order", X=X, global_on="filtered"))
    assert full["*_O1"] == ["e1", "e18", "e27", "e28"]
    assert filt["*_O1"] == ["e1", "e6", "e10", "e11", "e18", "e19", "e20", "e27", "e28"]
    assert boundary_objects(running, running_df, "start", "global", X, "full") == ["A", "B", "O1", "O2", "P1"]
    assert boundary_objects(running, running_df, "start", "global", X, "filtered") == \
        ["O1", "O2", "P1", "X1", "X2", "X3", "Y1", "Y2"]


def test_projection_reintroduces_excluded_df_edges(running, running_df):
    """*_O1 (filtered reading) contains e6, e10, e11 but not e8; recomputing Def. 3 on the projection
    gives e6 ⋖_A e10, which is not a df-edge of D (there e6 ⋖_A e8 ⋖_A e10)."""
    X = excluded_objects(running, types=["Supplier Order"])
    r = case_record(running, running_df, "end", "O1", X=X, global_on="filtered")
    assert r["excluded_objects_in_projection"] == ["A", "B"]
    assert r["projection_df_edges_not_in_D"] == [["e6", "A", "e10"]]
