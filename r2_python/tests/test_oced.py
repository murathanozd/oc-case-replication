"""Step 1: data model (Def. 1, Def. 2) and Sect. 4 operations."""

from r2_python.oced import E_of, O_of, is_relation_consistent, project, select

from .conftest import mini


def test_sanity_numbers(running):
    assert len(running.events) == 21
    assert len(running.objects) == 12
    assert len(running.corr) == 41


def test_object_types(running):
    types = {o: running.type[o] for o in running.objects}
    assert types == {"O1": "Order", "O2": "Order", "A": "Supplier Order", "B": "Supplier Order",
                     "X1": "Item", "X2": "Item", "X3": "Item", "Y1": "Item", "Y2": "Item",
                     "I1": "Invoice", "I2": "Invoice", "P1": "Payment"}


def test_not_objects(running):
    # Actor (R1..R5), Order Details and Tray (T1..T4) are not objects
    assert not ({"R1", "R2", "T1", "T2", "X", "Y"} & running.objects)


def test_relation_consistent(running):
    assert is_relation_consistent(running)
    assert not any(a == b for a, b in running.rel)        # I1: no self-loops
    assert ("O2", "B") in running.rel and ("B", "O2") in running.rel   # via e7
    assert ("A", "O1") not in running.rel                 # A and O1 share no event


def test_not_relation_consistent_without_rel():
    d = mini({"e1": ("a", 1)}, {"e1": ["x", "y"]}, {"x": "T", "y": "U"})
    stripped = type(d)(d.objects, d.events, d.type, d.corr, frozenset(), d.attrs)
    assert is_relation_consistent(d) and not is_relation_consistent(stripped)


def test_operations(running):
    assert E_of(running, {"P1"}) == {"e29", "e30"}
    assert O_of(running, {"e30"}) == {"I1", "I2", "P1"}
    sel = select(running, {"P1"})
    assert sel.events == {"e29", "e30"} and sel.objects == {"P1"}
    assert sel.corr == {("e29", "P1"), ("e30", "P1")}
    proj = project(running, {"e30"})
    assert proj.objects == {"I1", "I2", "P1"} and proj.events == {"e30"}
    assert {frozenset(p) for p in proj.rel} == {frozenset(p) for p in [("I1", "I2"), ("I1", "P1"), ("I2", "P1")]}


def test_union_subset(running):
    from r2_python.oced import is_subset, union
    a, b = select(running, {"P1"}), select(running, {"I1"})
    u = union([a, b])
    assert is_subset(a, u) and is_subset(b, u) and is_subset(u, running)
    assert u.events == {"e18", "e29", "e30"} and u.objects == {"P1", "I1"}
    assert not is_subset(running, u)
    assert union([]).events == set()
