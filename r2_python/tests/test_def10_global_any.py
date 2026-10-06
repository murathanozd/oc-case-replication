"""Def. 10: "global" vs. "any" start/end events (R1 open point 1).

Claim (unfiltered, any OCED-set satisfying Def. 8's assumption): D[o -> *] and D[* -> o] are the same with
O_end / O_start restricted to objects with a global end / start event ("global") or with all objects ("any").
Proof (start case; the end case is symmetric with sources): "global" ⊆ "any" since O_end ⊆ O. Let t be any
object with i = start(o) ≤ e = end(t). The DF graph is acyclic (strict timestamps), so e reaches a DF-sink g.
g ≠ e only if g has an incoming df-edge, so g is correlated to some object t'; if g = e, take t' = t. g has no
df-successor at all, so g = end(t') and g ∈ end(O): t' ∈ O_end. e ≤ g gives E_i^e ⊆ E_i^g, hence
D[i -> e] ⊆ D[i -> g] (projection is monotone), so every part of "any" lies in a part of "global".

Filtered (Def. 11), the same argument on df(D, O \\ X):
  global_on="filtered": holds whenever the case's own object o ∉ X (the sink/source g' of the filtered graph is
    correlated to a non-excluded object, whose start/end it is). Fails in the degenerate case o ∈ X.
  global_on="full": data-dependent. The filtered sink need not be a global end of D (it may still have
    df-successors via X). Counterexamples: the running example's Fig. 12 end case, and test_counterexample_full.
"""

import random

from r2_python.behaviour import directly_follows
from r2_python.generalized import end_case, start_case

from .conftest import mini


def random_oced(rng: random.Random):
    """3-8 events with distinct timestamps (no ties), 2-4 objects, each event correlated to 1-2 objects."""
    n, k = rng.randint(3, 8), rng.randint(2, 4)
    objs = [f"o{j}" for j in range(k)]
    minutes = rng.sample(range(100), n)
    events = {f"e{j}": (f"a{j}", minutes[j]) for j in range(n)}
    corr = {e: rng.sample(objs, rng.randint(1, 2)) for e in events}
    used = sorted({o for os in corr.values() for o in os})
    return mini(events, corr, {o: rng.choice(["T", "U"]) for o in used})


def same(a, b):
    return a[0].events == b[0].events and a[0].objects == b[0].objects


SEEDS = range(300)


def test_unfiltered_global_equals_any_random():
    for seed in SEEDS:
        d = random_oced(random.Random(seed))
        df = directly_follows(d)
        for o in d.objects:
            assert same(start_case(d, df, o, "global"), start_case(d, df, o, "any")), (seed, o)
            assert same(end_case(d, df, o, "global"), end_case(d, df, o, "any")), (seed, o)


def test_filtered_global_on_filtered_equals_any_random():
    """global_on="filtered" equals "any" for o ∉ X; global_on="full" differs on some random sets."""
    full_differs = 0
    for seed in SEEDS:
        rng = random.Random(seed)
        d = random_oced(rng)
        df = directly_follows(d)
        objs = sorted(d.objects)
        X = set(rng.sample(objs, rng.randint(1, len(objs) - 1))) if len(objs) > 1 else set()
        for o in sorted(d.objects - X):
            for fn in (start_case, end_case):
                anyv = fn(d, df, o, "any", X, "full")
                assert same(fn(d, df, o, "global", X, "filtered"), anyv), (seed, o, fn.__name__)
                full_differs += not same(fn(d, df, o, "global", X, "full"), anyv)
    assert full_differs > 0


def test_counterexample_full():
    """o: e1@1 -> e2@2 ; x: e2@2 -> e3@3 ; X = {x}.
    Full DF: e1 ⋖_o e2 ⋖_x e3; the only global end is e3 = end(x), so O_end(full) = {x}.
    Filtered DF: e1 ⋖_o e2 only. Start case D[o -> * \\ X]:
      global_on="full":     D[e1 -> e3 \\ X] = ∅ (e3 unreachable without x's edge)       -> ∅
      "any":                adds D[e1 -> end(o) = e2 \\ X] = {e1, e2}                     -> {e1, e2}
      global_on="filtered": end(O \\ X) on the filtered graph = {e2}, O_end = {o}         -> {e1, e2}
    Unfiltered, D[o -> *] = D[e1 -> e3] = {e1, e2, e3} in both readings."""
    d = mini({"e1": ("a", 1), "e2": ("b", 2), "e3": ("c", 3)},
             {"e1": ["o"], "e2": ["o", "x"], "e3": ["x"]}, {"o": "Order", "x": "SO"})
    df = directly_follows(d)
    X = {"x"}
    assert start_case(d, df, "o", "global", X, "full")[0].events == set()
    assert start_case(d, df, "o", "any", X)[0].events == {"e1", "e2"}
    assert start_case(d, df, "o", "global", X, "filtered")[0].events == {"e1", "e2"}
    assert start_case(d, df, "o", "global")[0].events == start_case(d, df, "o", "any")[0].events == {"e1", "e2", "e3"}


def test_counterexample_filtered_excluded_own_object():
    """Degenerate case o ∈ X. o: e1@1 ; x: e2@2 (x has a single event); X = {x}.
    Start case D[x -> * \\ X]: "any" contains D[e2 -> end(x) = e2 \\ X] = {e2}; global_on="filtered":
    end(O \\ X) = {e1} (e2 is correlated only to x), D[e2 -> e1 \\ X] = ∅ -> ∅."""
    d = mini({"e1": ("a", 1), "e2": ("b", 2)}, {"e1": ["o"], "e2": ["x"]}, {"o": "Order", "x": "SO"})
    df = directly_follows(d)
    assert start_case(d, df, "x", "any", {"x"})[0].events == {"e2"}
    assert start_case(d, df, "x", "global", {"x"}, "filtered")[0].events == set()
