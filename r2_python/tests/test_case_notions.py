"""Step 4: Def. 9 case notions, A3 (self-pairs / distinct types), A4 (global restriction per object / type).

Hand derivation on the running example (from the DF edges):
  global start events e1 (O1), e2 (O2), e3 (A), e4 (B), e29 (P1); global end events e28 (O1), e34 (O2),
  e30 (I1, I2, P1).  Events reachable from each global start:
    e3 (A):  e6 e8 e10 e11 e27 e28 e33 e34                    -> ends O1, O2
    e4 (B):  e7 e19 e20 e21 e27 e28 e33 e34                   -> ends O1, O2
    e1 (O1): e18 e27 e28 e30                                  -> ends O1, I1, I2, P1
    e2 (O2): e5 e7 e9 e19 e20 e21 e27 e28 e30 e33 e34         -> ends O1, O2, I1, I2, P1
    e29 (P1): e30                                             -> ends I1, I2, P1
  without self-pairs: 2 + 2 + 3 + 4 + 2 = 13;  with self-pairs (O1, O2, P1): 16;
  distinct types (also drop O2 -> O1): 12.
"""

from r2_python.case_notions import behaviour, case_notion, case_pairs, global_executions, global_objects

from .conftest import mini
from r2_python.behaviour import directly_follows


def ids(recs):
    return [r["execution_id"] for r in recs]


def test_SO_Order(running, running_df):
    # Sect. 5.1: D[SupplierOrder -> Order] = {A->O1, A->O2, B->O1, B->O2}
    assert ids(case_notion(running, running_df, "Supplier Order", "Order")) == ["A_O1", "A_O2", "B_O1", "B_O2"]


def test_order_order_self_pairs(running, running_df):
    assert ids(case_notion(running, running_df, "Order", "Order", self_pairs=False)) == ["O2_O1"]
    assert ids(case_notion(running, running_df, "Order", "Order", self_pairs=True)) == ["O1_O1", "O2_O1", "O2_O2"]


def test_global_objects(running, running_df):
    for by in ("object", "type"):
        assert global_objects(running, running_df, by) == (["A", "B", "O1", "O2", "P1"],
                                                           ["I1", "I2", "O1", "O2", "P1"])


def test_global_counts(running, running_df):
    assert len(global_executions(running, running_df, "object", self_pairs=False)) == 13
    assert len(global_executions(running, running_df, "object", self_pairs=True)) == 16
    assert len(global_executions(running, running_df, "object", self_pairs=False, distinct_types=True)) == 12
    no_self = ids(global_executions(running, running_df, "object", self_pairs=False))
    assert no_self == ["A_O1", "A_O2", "B_O1", "B_O2", "O1_I1", "O1_I2", "O1_P1", "O2_I1", "O2_I2",
                       "O2_O1", "O2_P1", "P1_I1", "P1_I2"]


def test_order_invoice_equals_order_payment(running, running_df):
    """Sect. 5.2: D[Order -> Invoice] and D[Order -> Payment] yield the same executions (shared end e30)."""
    inv = case_notion(running, running_df, "Order", "Invoice")
    pay = case_notion(running, running_df, "Order", "Payment")
    assert {tuple(r["events"]) for r in inv} == {tuple(r["events"]) for r in pay}
    assert ids(inv) == ["O1_I1", "O1_I2", "O2_I1", "O2_I2"]


def test_behaviour_union(running, running_df):
    pairs = [("A", "O1"), ("A", "O2")]
    assert behaviour(running, running_df, pairs).events == {"e3", "e6", "e8", "e10", "e11", "e27", "e28", "e33", "e34"}


def test_a4_differs_on_mini():
    """A4 on a mini set where the two readings differ: type T has objects a (global start e1) and
    b (start e3, preceded by e2 of c). by object: a, c start globally; by type: only type U (c) qualifies,
    since b of type T does not start globally.
       c: e2@2 -> e3@3 ; a: e1@1 -> e4@4 ; b: e3@3 -> e4@4"""
    d = mini({"e1": ("x", 1), "e2": ("y", 2), "e3": ("z", 3), "e4": ("w", 4)},
             {"e1": ["a"], "e2": ["c"], "e3": ["c", "b"], "e4": ["a", "b"]},
             {"a": "T", "b": "T", "c": "U"})
    df = directly_follows(d)
    assert global_objects(d, df, "object")[0] == ["a", "c"]
    assert global_objects(d, df, "type")[0] == ["c"]


def test_empty_pairs_dropped(running, running_df):
    # I2: pairs without an execution are not cases: no Supplier Order -> Invoice / Payment cases
    assert case_notion(running, running_df, "Supplier Order", "Invoice") == []
    assert case_notion(running, running_df, "Supplier Order", "Payment") == []
    assert case_pairs(running, running_df, ["A"], ["P1"]) == []


def test_order_to_supplier_order_needs_global_restriction(running, running_df):
    """Plain Def. 9 (no Sect. 5.2 restriction) has one Order -> Supplier Order case: e2 (start of O2)
    ⋖_O2 e5 ⋖_O2 e7 ⋖_B e19 ⋖_B e20 ⋖_B e21 (end of B). It is excluded only because e21 is not a
    global end (e21 ⋖_Y2 e33), so B is not an end object in Sect. 5.2."""
    recs = case_notion(running, running_df, "Order", "Supplier Order")
    assert [(r["execution_id"], r["events"]) for r in recs] == [("O2_B", ["e2", "e5", "e7", "e19", "e20", "e21"])]
    assert not any(r["end_object"] in ("A", "B") for r in global_executions(running, running_df))
    # likewise same-type cases between distinct invoices exist under plain Def. 9
    assert [r["execution_id"] for r in case_notion(running, running_df, "Invoice", "Invoice", self_pairs=False)] == ["I1_I2", "I2_I1"]
