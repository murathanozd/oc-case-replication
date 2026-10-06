"""Step 2: Def. 3-6, Lemma 1, partial-order properties."""

import networkx as nx
import pytest

from r2_python.behaviour import (descendants, directly_follows, end_events, global_end_events,
                                 global_start_events, is_df_path, is_maximal_df_path, leq, start_events)

from .conftest import mini


def test_df_running(running, running_df):
    assert len(running_df.triples) == 29
    # examples from the paper (Sect. 3): e6 ⋖_A e8, e6 ⋖_X1 e10, but not e6 ⋖_o e7 for any o
    assert ("e6", "A", "e8") in running_df.triples
    assert ("e6", "X1", "e10") in running_df.triples
    assert not any(a == "e6" and b == "e7" for a, _, b in running_df.triples)
    # no ties in the running example: both tie modes give the same DF
    assert directly_follows(running, ties="break_by_id").triples == running_df.triples


def test_paper_examples_order(running_df):
    # Sect. 3: e3 ≤ e28 (via e3 ⋖_A e6 ⋖_X1 e10 ⋖_X1 e27 ⋖_O1 e28); e6 and e7 are concurrent
    assert leq(running_df, "e3", "e28")
    assert is_df_path(running_df, ["e3", "e6", "e10", "e27", "e28"])
    assert not leq(running_df, "e6", "e7") and not leq(running_df, "e7", "e6")


def test_partial_order(running, running_df):
    E = sorted(running.events)
    for a in E:
        assert leq(running_df, a, a)                                   # reflexive
        for b in E:
            if a != b and leq(running_df, a, b):
                assert not leq(running_df, b, a)                       # antisymmetric
                for c in descendants(running_df, b):
                    assert leq(running_df, a, c)                       # transitive


@pytest.mark.parametrize("ties", ["strict", "break_by_id"])
def test_lemma1_against_networkx(running, ties):
    """Lemma 1: e < e' iff there is a df-path from e to e'. Independent check: build the DF graph
    with networkx from the triples and compare its path reachability with our closure."""
    df = directly_follows(running, ties=ties)
    g = nx.DiGraph()
    g.add_nodes_from(running.events)
    g.add_edges_from((a, b) for a, _, b in df.triples)
    for a in running.events:
        for b in running.events:
            if a != b:
                assert leq(df, a, b) == nx.has_path(g, a, b), (a, b)
    # the transitive closure of networkx equals our strict order
    closure = nx.transitive_closure_dag(g)
    assert {(a, b) for a in running.events for b in descendants(df, a) if a != b} == set(closure.edges)


def test_start_end_intended(running, running_df):
    assert start_events(running, running_df, {"O1"}) == {"e1"}
    assert end_events(running, running_df, {"O1"}) == {"e28"}
    assert global_start_events(running, running_df) == {"e1", "e2", "e3", "e4", "e29"}
    assert global_end_events(running, running_df) == {"e28", "e30", "e34"}
    # e6 is the shared start event of X1, X2, X3 (Sect. 2 / Fig. 4)
    assert start_events(running, running_df, {"X1", "X2", "X3"}) == {"e6"}


def test_start_literal_is_absurd(running, running_df):
    """A2: read literally, Def. 6 puts every event without an O'-predecessor into start(O'), including
    events not correlated to O': start({O1}) would contain e3 (Place SO of A) and 17 other events."""
    lit = start_events(running, running_df, {"O1"}, reading="literal")
    assert "e3" in lit and "e29" in lit
    assert len(lit) == 18                     # 21 events minus O1's three non-first events e18, e27, e28
    assert start_events(running, running_df, {"O1"}) == {"e1"}


def test_maximal_df_path(running, running_df):
    assert is_maximal_df_path(running, running_df, ["e1", "e18", "e27", "e28"], {"O1"})
    assert not is_maximal_df_path(running, running_df, ["e18", "e27", "e28"], {"O1"})
    assert not is_df_path(running_df, ["e1", "e18", "e30"], {"O1"})   # e18 ⋖ e30 only for I1
    assert is_df_path(running_df, ["e1", "e18", "e30"], {"O1", "I1"})


def test_tie_mini():
    """A1. Object a: e1@1, e2@2, e3@2 (tie), e4@3.
    strict (Def. 3 literally): e2 and e3 are not ordered; e1 is followed by both, both by e4:
        e1 ⋖ e2, e1 ⋖ e3, e2 ⋖ e4, e3 ⋖ e4   -> e2, e3 concurrent
    break_by_id: e1 ⋖ e2 ⋖ e3 ⋖ e4         -> e2 < e3"""
    d = mini({"e1": ("a", 1), "e2": ("b", 2), "e3": ("c", 2), "e4": ("d", 3)},
             {"e1": ["a"], "e2": ["a"], "e3": ["a"], "e4": ["a"]}, {"a": "T"})
    s = directly_follows(d, "strict")
    assert {(x, y) for x, _, y in s.triples} == {("e1", "e2"), ("e1", "e3"), ("e2", "e4"), ("e3", "e4")}
    assert not leq(s, "e2", "e3") and not leq(s, "e3", "e2")
    b = directly_follows(d, "break_by_id")
    assert {(x, y) for x, _, y in b.triples} == {("e1", "e2"), ("e2", "e3"), ("e3", "e4")}
    assert leq(b, "e2", "e3")


def test_is_df_path_edge_cases(running_df):
    assert not is_df_path(running_df, [])
    assert not is_df_path(running_df, ["nope"])                 # unknown event
    assert not is_df_path(running_df, ["e1", "nope"])
    assert is_df_path(running_df, ["e1"])                       # k = 1: a df-path (Def. 6, vacuously)
    assert not is_df_path(running_df, ["e1", "e28"])            # not directly following
    assert is_df_path(running_df, ["e6", "e8"], {"X3"}) and not is_df_path(running_df, ["e6", "e8"], {"O1"})
