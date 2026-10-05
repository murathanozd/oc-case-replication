# R2 log – interpretation decisions and deviations

Dated log for R2 (independent implementation of the paper's definitions in `r2_python/`).
Source: Fahland & Montali, "What is an Object-Centric Case? An Exploration", LNCS 16480 (2026),
local copy `docs/paper/paper.pdf` (not committed).

## What was read (independence)

- Implementation is based on the paper text (Sect. 3–5, Def. 1–11, Lemma 1) and the raw CSV
  `data/running_example/order_process_event_table_orderhandling.csv`.
- During R2 we did **not** open `r1_neo4j/`, the authors' tutorial code (`external/`), or `results/r1/*.json`
  (until the comparison step, Step 6).
- **Limitation:** R2 is implemented by the same assistant (Claude) that carried out R1 in the same working
  session. It has therefore seen the authors' Cypher queries and the R1 results before writing R2. This
  cannot be undone; we mitigate it by implementing strictly from the paper's definitions, deriving the
  expected values in the tests by hand from the DF edges (comments in `r2_python/tests/`), and comparing
  with R1 only in Step 6 by script. The ambiguities A1–A5 were listed in the R2 plan beforehand.
- Read besides the paper: `README.md`, `docs/replication_plan.md`, `docs/r2_plan.md` (context, as instructed).

## 2026-10-06 – Steps 1–3

### Step 1 – data model (`r2_python/oced.py`)

1. **Loader.** Own CSV reader (`csv` module, UTF-8 with BOM). One event per row: id `EventID`, event type
   (activity) `event`, timestamp `time` parsed with `%d.%m.%Y %H:%M:%S` (naive; all events in one time zone).
   Objects only from the columns Order, Supplier Order, Item, Invoice, Payment (comma-separated ids);
   Actor, Order Details and Tray are ignored (Sect. 2 lists 5 object types).
   Result: 21 events, 12 objects, 41 corr pairs (matches the plan's sanity numbers).
2. **I1 – Def. 2 and self-pairs (not in the plan's A1–A5).** Def. 2 says "any two objects o, o′ correlated to the
   same event" must be related, and Sect. 3 adds (o, o′) ∈ rel "whenever ∃e : (e, o), (e, o′) ∈ corr". Read
   literally this includes o = o′, i.e. self-loops (o, o) for every correlated object. We read "two objects"
   as two *distinct* objects (Fig. 2 shows no self-loops). The rule is symmetric in o and o′, so both (o, o′)
   and (o′, o) are added. Result: 23 unordered related pairs (46 ordered).
3. **Fig. 2 shows fewer relations than the rule produces.** The rule also relates objects of the same type
   that share an event (X1–X2, X1–X3, X2–X3 via e6; Y1–Y2 via e19; X1–Y1, X2–Y1 via e27; X3–Y2 via e33;
   I1–I2 via e30). Fig. 2 draws only relations between objects of different types. No definition uses
   `rel` later (Def. 3–11 only use corr and ⋖), so this has no effect on the results.
4. `select`, `project`, `restrict`, `E[O']`, `O[E']` as in Sect. 4. The directly-follows relation is not
   stored in an OCED-set; it is always recomputed from the (restricted) set, since the paper notes that
   projection may alter ⋖.

### Step 2 – behaviour (`r2_python/behaviour.py`)

5. **Def. 3, A1 (ties).** `ties="strict"` (default, the paper): e ⋖_o e′ iff e′ has the next larger timestamp
   among o's events; tied events are not ordered, and an event is followed by *all* events of o at the
   next larger timestamp (fan-out), so strict `<` does not just drop edges but also creates parallel ones
   (test `test_tie_mini`). `ties="break_by_id"`: total order per object by (timestamp, natural order of
   the event id), consecutive events linked. The running example has no ties: both give the same 29 DF
   triples.
6. **Def. 4 / Lemma 1.** ≤ is computed by BFS reachability on the event-level DF graph (successors /
   predecessors), never by materializing ≤ or enumerating paths. Lemma 1 is checked in a test against an
   independent networkx graph (`has_path` and `transitive_closure_dag`) for both tie modes.
7. **Def. 6, A2 (start/end events).** Default `reading="intended"`: e ∈ start(O′) requires e to be correlated
   to some o ∈ O′. The literal reading (no such condition) gives start({O1}) = 18 of the 21 events,
   including e3 (Place SO of A) and e29 (Receive Payment) – absurd, shown in `test_start_literal_is_absurd`.
   "Global" start/end events (Sect. 5.2/5.3) = start(O) / end(O): e1, e2, e3, e4, e29 and e28, e30, e34.
8. Def. 5 (OCED-graph) is provided as `oced_graph()`; nothing else depends on it.

### Step 3 – executions and cases (`r2_python/executions.py`)

9. **Def. 7.** E_i^o = descendants(i) ∩ ancestors(o) (empty unless i ≤ o); D[i → o] = Proj_{E_i^o} D.
   Tests check, for all 21 × 21 pairs with i ≤ o, the properties stated after Def. 7: single start event i
   and single end event o computed on D[i → o] itself, and every event on a df-path i…e…o in D[i → o] and
   in D. They also confirm that projection does not change ⋖ between included events here (E_i^o is
   convex, so no event of an included object lies between two included events).
10. **Def. 8.** start(o) = start({o}), end(o) = end({o}). `case()` raises `Def8AssumptionError` naming all
    violating objects if an object has ≠ 1 start or end event. On the running example no object violates it
    (`results/r2/object_start_end.json`); a hand-made test with a tie at an object's first timestamp
    violates it under `strict` and not under `break_by_id`.
11. **D[A → O1]** (`results/r2/exec_A_O1.json`): events e3 e6 e8 e10 e11 e27 e28, objects A O1 X1 X2 X3 Y1.
12. **Testing tool.** `pytest` was not installed; installed into `.venv` and pinned in `requirements.txt`
    (`pytest==9.1.1`), as the plan requires `pytest r2_python`.

## 2026-10-06 – Session note for Step 4 onward

Step 4 onward were **not** done in a fresh session: they continue the same assistant session that carried
out R1 and R2 Steps 1–3, so the limitation stated above ("What was read") still applies. In this part of
the session `r1_neo4j/`, `results/r1/`, `docs/r1_log.md` and `external/` were not opened; the R1 knowledge
from earlier in the session remains. For a fully independent check, Steps 4–6 can be redone in a fresh
session and compared with these results.

## 2026-10-06 – Review of Steps 1–3 against the paper

Checked every function of `oced.py`, `behaviour.py`, `executions.py` against Def. 1–8 and Lemma 1. They
implement the definitions; the following points were not (fully) covered by this log before:

1. **Sect. 4 subset and union were missing.** Sect. 4 defines D′ ⊆ D (element-wise) and D ∪ D′ / ⋃𝒟; Def. 9
   ("the behavior ⋃𝒟[T_st → T_end]") and Def. 10 need the union. Added `is_subset()` and `union()` to
   `oced.py` (additive, no existing behaviour changed).
2. **Events without any object (intended reading of Def. 6, A2).** An event correlated to no object is
   never in start(O′) or end(O′) under the intended reading, so it is neither a global start nor a global
   end (the literal reading includes it). The running example has no such events; relevant for R3.
   Not changed.
3. **`is_df_path` accepts single-event sequences without checking the event exists** (k = 1 is a df-path
   by Def. 6, vacuously; but `is_df_path(df, ["nope"])` is also True). It also rebuilds an index per call
   (slow on large logs). Only used in tests so far. Not changed; to fix before R3.

## 2026-10-06 – Step 4: case notions (`r2_python/case_notions.py`)

4. **Def. 9 and empty cases (I2, not in the plan's A1–A5).** Def. 9 collects D[o_st → o_end] for *all*
   pairs of objects of the two types, including pairs whose execution is empty (start(o_st) ≰ end(o_end)).
   We count as cases only pairs with a non-empty execution, as the paper does when it counts cases
   ("defines 4 cases"). Empty cases would add nothing to the behaviour ⋃𝒟.
5. **A3 – self-pairs / distinct types.** `self_pairs=True` (Def. 9 literally, o_st = o_end allowed) and
   `False`. Additionally `distinct_types=True` (Sect. 5.2 read literally: "pairs of distinct object types",
   which also removes D[O2 → O1]). Global executions: 16 (self-pairs: adds O1→O1, O2→O2, P1→P1),
   13 (no self-pairs), 12 (distinct types).
6. **A4 – global restriction per object or per type.** Per object: objects whose start (end) event is a
   global start (end). Per type: all objects of a type must qualify. Same result on the running example:
   start objects A, B, O1, O2, P1 (types Order, Supplier Order, Payment) and end objects I1, I2, O1, O2, P1
   (types Order, Invoice, Payment), as in Sect. 5.2. A hand-made test shows that the readings can differ.
7. **The Sect. 5.2 absence statements depend on the global restriction.** Under plain Def. 9 (all objects
   of the types, no restriction), D[Order → SupplierOrder] is *not* empty: D[O2 → B] = e2 e5 e7 e19 e20 e21
   (via Update SO e7). It disappears only because B's end event e21 is not a global end (e21 ⋖_Y2 e33).
   Likewise distinct invoices: D[I1 → I2] and D[I2 → I1] exist under plain Def. 9 (both end at e30), but
   invoices are not start objects in Sect. 5.2. D[SupplierOrder → Invoice / Payment] is empty in both
   cases. The full Def. 9 matrix is in `results/r2/case_notions_summary.json`
   (`def9_all_type_pairs__noselfpairs`).
8. **Outputs** (`results/r2/`): `notion_<St>_<End>__selfpairs|noselfpairs.json` for SO→Order,
   Order→Payment, Order→Invoice, Payment→Invoice, Order→Order (plain Def. 9);
   `all_global_executions__by_object|by_type__selfpairs|noselfpairs.json`,
   `all_global_executions__by_object__distinct_types.json`; `case_notions_summary.json`.
