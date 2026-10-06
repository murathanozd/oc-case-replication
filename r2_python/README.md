# R2 - Independent implementation (Python)

Def. 1–11 of Fahland & Montali, "What is an Object-Centric Case? An Exploration", implemented from the paper
only, and compared afterwards with R1 (the authors' Cypher in Neo4j).
Plan: [`docs/r2_plan.md`](../docs/r2_plan.md). Log of every interpretation decision and finding:
[`docs/r2_log.md`](../docs/r2_log.md). Comparison with R1: [`results/r2/comparison.md`](../results/r2/comparison.md).

## Run

From the repo root, with the project venv (Python 3.11, `pip install -r requirements.txt`):

```bash
python -m r2_python.run_all      # all of results/r2/ (incl. comparison.md, environment.json), < 1 s
python -m r2_python.timing       # results/r2/runtimes.csv (1 warm-up + 5 timed runs per computation)
python -m pytest r2_python       # 45 tests
```

Input: the raw CSV `data/running_example/order_process_event_table_orderhandling.csv`, read by our own loader.
No database is needed. The implementation uses the Python standard library only; networkx is used only in
the tests, as an independent cross-check of Lemma 1. `comparison.md` reads `results/r1/` (committed R1 results).

Reruns are byte-identical (sorted output, no timestamps in files, independent of `PYTHONHASHSEED`), except
`runtimes.csv`. `environment.json` is identical on the same machine.

## Modules

| module | paper | contents |
|---|---|---|
| `oced.py` | Def. 1, 2, Sect. 3, 4 | `OCEDSet`, CSV loader, relation-consistency, E[O′], O[E′], `restrict`, `select`, `project`, subset, union |
| `behaviour.py` | Def. 3–6, Lemma 1 | `directly_follows` (⋖), `leq` / `descendants` / `ancestors` (≤ by BFS reachability), `start_events` / `end_events`, `is_df_path`, OCED-graph, `without_objects` (df(D, O \ X)) |
| `executions.py` | Def. 7, 8 | `between` (E_i^o), `execution`, `case`, start/end event per object, Def. 8 assumption check |
| `case_notions.py` | Def. 9, Sect. 5.2 | case notions per type pair, global start/end objects, all global executions |
| `generalized.py` | Def. 10, 11 | start/end cases, filtered executions |
| `projection_check.py` | Sect. 4 (Proj) | convexity / DF-after-projection check for Def. 7 and Def. 11 |
| `run_all.py` | – | writes `results/r2/` |
| `compare_r1.py` | – | Step 6: `results/r2/comparison.md` |
| `timing.py`, `environment.py` | – | Step 7: `runtimes.csv`, `environment.json` |
| `tests/` | – | pytest: sanity numbers, partial-order properties, Lemma 1 vs. networkx, properties after Def. 7, hand-made mini sets (tie, two start events, …), Def. 10 property test on random sets, projection check |

Nothing enumerates paths. ≤ is reachability on the event-level DF graph, so the code scales to larger logs (R3).

## Interpretation choices and ambiguities

| | question | default (used for the main results) | alternative(s) | effect on the running example |
|---|---|---|---|---|
| I1 | Def. 2 / Sect. 3: which pairs go into `rel`? | every two *distinct* objects of an event, both directions | – | 23 pairs (R1's tutorial: 15, no same-type pairs); `rel` is not used by Def. 3–11 |
| I2 | is an empty execution a case? | no (Def. 9 keeps only pairs with start(o_st) ≤ end(o_end)) | – | – |
| A1 | Def. 3 with equal timestamps | `ties="strict"`: no edge between tied events; each event links to all events of the next timestamp | `"break_by_id"`: total order by (time, event id) | none (no ties) |
| A2 | Def. 6 start/end events | `reading="intended"`: e must be correlated to O′ | `"literal"`: any event without O′-predecessor | literal is unusable (start({O1}) = 18 events) |
| A3 | Def. 9 self-pairs | `self_pairs=True` = Def. 9 as written | `False` (R1 query); `distinct_types=True` (Sect. 5.2 "distinct object types") | 16 / 13 / 12 global executions |
| A4 | Sect. 5.2 global restriction | `by="object"` (R1 query) | `"type"`: all objects of the type must qualify | none |
| A5 | Def. 11: global start/end events before or after removing X's df-edges | `global_on="full"` (before) | `"filtered"` (after; equals R1 / the tutorial and the paper's text on Fig. 12) | Fig. 12 end case differs; Fig. 11 start case does not |
| Def. 10 | other end: global or any start/end event | `variant="global"` (Def. 10) | `"any"` (R1 query) | equal event sets; provably equal for every unfiltered OCED-set |
