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

## Summary after Step 5 (status 2026-10-06)

Steps 1–5 of `docs/r2_plan.md` are implemented in `r2_python/` (`oced.py`, `behaviour.py`, `executions.py`,
`case_notions.py`, `generalized.py`, `run_all.py`); 38 pytest tests pass; `python -m r2_python.run_all`
regenerates `results/r2/` byte-identically (also with a different `PYTHONHASHSEED`). R1 results have
not been compared yet (Step 6). Details and reasoning: dated entries below.

### Interpretation choices (not in the plan's A1–A5)

| id | where | choice | alternative | effect on the running example |
|---|---|---|---|---|
| I1 | Def. 2 / Sect. 3 | relate only *distinct* objects sharing an event; add both (o, o′) and (o′, o) | literal rule also adds self-loops (o, o) | none (`rel` is not used by Def. 3–11); 23 unordered related pairs |
| I2 | Def. 9, Def. 10 | a pair (o_st, o_end) is a case only if its execution is non-empty (start(o_st) ≤ end(o_end)) | Def. 9 literally also contains empty D[o_st → o_end] | case counts as in the paper; empty cases add nothing to the behaviour ⋃𝒟 |

### Ambiguities A1–A5

| id | where | default | alternative(s) | result on the running example |
|---|---|---|---|---|
| A1 | Def. 3, equal timestamps | `ties="strict"` (paper): tied events unordered; each event followed by *all* events of the object at the next larger timestamp (fan-out/fan-in) | `break_by_id`: total order by (time, natural event id) | no ties: both give the same 29 df-triples |
| A2 | Def. 6, start/end events | `intended`: e must be correlated to some o ∈ O′ | `literal`: any event without an O′-predecessor | literal start({O1}) = 18 of 21 events (incl. e3, e29), absurd; intended: start({O1}) = {e1} |
| A3 | Def. 9 vs. Sect. 5.2 | `self_pairs=True` (Def. 9 literally) | `self_pairs=False`; `distinct_types=True` ("pairs of distinct object types") | global executions: 16 / 13 / 12 (self-pairs add O1→O1, O2→O2, P1→P1; distinct types also drops O2→O1) |
| A4 | Sect. 5.2 "global" restriction | `by="object"` | `by="type"` (all objects of the type qualify) | same: start objects A, B, O1, O2, P1; end objects I1, I2, O1, O2, P1 (a mini test shows they can differ) |
| A5 | Def. 10/11, global events for filtered cases | `global_on="full"` (before removing X's edges) | `"filtered"` (on df(D, O \ X)) | start case (Fig. 11): no difference; end case (Fig. 12): full ∗→O1 = e1 e18 e27 e28, filtered ∗→O1 = e1 e6 e10 e11 e18 e19 e20 e27 e28 |

Def. 10 variant `any` (every object's end/start event instead of only global ones): same event sets as
`global` for the unfiltered start and end cases; for the filtered cases it equals the `filtered` reading.

### Findings so far

- **F1 – Fig. 2 vs. the relation rule.** The Sect. 3 rule yields 23 related pairs including same-type pairs
  (X1–X2, Y1–Y2, I1–I2, …) that Fig. 2 does not draw. No effect on results.
- **F2 – Sect. 5.2 absence statements depend on the global restriction.** Under plain Def. 9,
  D[Order → SupplierOrder] = {D[O2 → B]} = e2 e5 e7 e19 e20 e21 (via Update SO e7), and D[I1 → I2], D[I2 → I1]
  exist. They vanish only because B's end e21 is not a global end and invoices have no global start.
  D[SupplierOrder → Invoice / Payment] is empty in both cases.
- **F3 – D[O2 → O2] is not just O2's behaviour.** Sect. 5.3 says D[O1 → O1] and D[O2 → O2] "give the behavior
  of each order object"; D[O1 → O1] = O1's trace, but D[O2 → O2] = e2 e5 e7 e19 e20 e21 e33 e34 also contains
  B / Y1 / Y2 events.
- **F4 – Def. 9 vs. Sect. 5.2 count.** 13 global executions only without self-pairs; 16 under Def. 9 as
  written; 12 if "distinct object types" is taken literally (A3).
- **F5 – Def. 11 ambiguity (A5) matters only for the filtered end case** (Fig. 12), not for the filtered
  start case (Fig. 11).
- **F6 – Projection reintroduces excluded behaviour.** Filtered cases keep excluded objects that are
  correlated to included events (B via e7 in O2 → ∗ \ SO and, under `full`, in ∗ → O2 \ SO; A and B in both
  `filtered` end cases). After projection, ⋖ recomputed on the result contains df-edges of A and B again;
  e7 ⋖_B e19 is an edge the filter removed, and e6 ⋖_A e10, e19 ⋖_B e21 are not df-edges of D at all.
- **F7 – Strict ties (A1) create parallel df-edges**, not only missing ones (mini test).
- **F8 – Literal Def. 6 (A2) is unusable** (start({O1}) = 18 events).

### Review of Steps 1–3 (done before Step 4)

Def. 1–8 and Lemma 1 are implemented as written. Gaps found and handled: Sect. 4 subset/union were missing
(added); `is_df_path` accepted unknown events and rebuilt its index per call (fixed); events correlated to no
object are never start/end events under the intended A2 reading (not changed; none in the running example,
relevant for R3).

### Open before Step 6

- The detailed projection check announced for later (F6) has not been started. *(Done afterwards, see
  "Projection check" below.)*
- Step 6 (comparison with `results/r1/`) not started; `results/r1/` not opened by R2 code.
- Step 7 (timing, README, `environment.json`) not started.

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
9. **D[O2 → O2] is more than O2's behaviour.** Sect. 5.3: "While D[O1 → O1] and D[O2 → O2] give the behavior
   of each order object". D[O1 → O1] = e1 e18 e27 e28 is exactly O1's trace, but D[O2 → O2] =
   e2 e5 e7 e19 e20 e21 e33 e34 also contains e19, e20, e21 (B, Y1, Y2), reached via Update SO e7
   (e7 ⋖_B e19, e21 ⋖_Y2 e33). O2's own trace is e2 e5 e7 e33 e34.

## 2026-10-06 – `is_df_path` fixed

10. `is_df_path` now rejects empty sequences and sequences containing unknown events, and uses an
    (e, e′) → objects index built once per DF relation (`DF.by_pair`) instead of rebuilding it per call.
    A single known event is still a df-path (k = 1, Def. 6). Test `test_is_df_path_edge_cases`.

## 2026-10-06 – Step 5: start/end cases and filtering (`r2_python/generalized.py`)

11. **Def. 10.** O_end = {o | end(o) ⊆ end(O)} (objects whose end event is a global end), O_start
    correspondingly; D[o → ∗] = ⋃{D[o → o_end] | o_end ∈ O_end}, D[∗ → o] = ⋃{D[o_st → o] | o_st ∈ O_start};
    only non-empty parts (I2); o itself is not excluded from O_end / O_start. Lifted to types: one case per
    object of the type. Variant `any`: every object as end (start) object, i.e. every object's end (start)
    event, global or not.
12. **Def. 11.** E_i^o|X̄ = descendants ∩ ancestors in df(D, O \ X), i.e. on the DF graph without the
    df-edges (e, x, e′), x ∈ X (`behaviour.without_objects`), then projection onto the *original* D, so all
    objects correlated to included events stay, also those in X. X = all Supplier Order objects {A, B}.
    start(o) / end(o) of each object are always taken from the full DF graph.
13. **A5 – global_on.** `full`: global starts/ends = start(O) / end(O) on the full DF graph; `filtered`:
    start(O \ X) / end(O \ X) on df(D, O \ X). Under `filtered`, e6 (start of X1–X3) and e19 (start of Y1, Y2)
    become global starts (their only incoming edges e3 ⋖_A e6, e7 ⋖_B e19 are removed), so
    O_start = {O1, O2, P1, X1, X2, X3, Y1, Y2} instead of {A, B, O1, O2, P1}. O_end is {I1, I2, O1, O2, P1}
    in both readings. Taking the global events over all objects O instead of O \ X on the filtered graph
    would also admit e3, e4 (A, B, which have no edges left); this changes nothing here (their filtered
    executions to O1, O2 are empty).
14. **Results.**
    - Start cases D[Order → ∗] (Fig. 10): `global` and `any` give the same event sets
      (O1: e1 e18 e27 e28 e30; O2: e2 e5 e7 e9 e19 e20 e21 e27 e28 e30 e33 e34); `any` adds non-global end
      events (e27 for O1; e21, e27, e33 for O2) that lie inside the same event sets.
    - End cases D[∗ → Order] (unfiltered): `global` and `any` give the same event sets; `any` adds start events
      e5, e6, e18, e19.
    - **Filtered start case D[Order → ∗ \ {SupplierOrder}] (Fig. 11): A5 changes nothing** (same O_end):
      O1: e1 e18 e27 e28 e30; O2: e2 e5 e7 e9 e30 e33 e34. `any` gives the same event sets.
    - **Filtered end case D[∗ → Order \ {SupplierOrder}] (Fig. 12): A5 matters.**
      `full`: ∗→O1 = e1 e18 e27 e28, ∗→O2 = e2 e5 e7 e33 e34.
      `filtered`: ∗→O1 = e1 e6 e10 e11 e18 e19 e20 e27 e28, ∗→O2 = e2 e5 e6 e7 e8 e19 e21 e33 e34.
      `any` gives the same event sets as `filtered`.
15. **Excluded objects in the projection.** Start cases (both readings): B in O2→∗ via e7 (Update SO).
    End case `full`: B in ∗→O2 via e7. End case `filtered`: A and B in both cases
    (∗→O1: A via e6 e10 e11, B via e19 e20; ∗→O2: A via e6 e8, B via e7 e19 e21).
16. **Projection reintroduces excluded behaviour.** Def. 11 projects onto D, and ⋖ of the projection is
    recomputed (Sect. 4: "projection may alter ⋖"). In the `filtered` end cases the projected sets again
    contain df-edges of A and B: ∗→O1 has e6 ⋖_A e10, e10 ⋖_A e11, e19 ⋖_B e20; ∗→O2 has e6 ⋖_A e8,
    e7 ⋖_B e19, e19 ⋖_B e21. Two of them are not df-edges of D at all (e6 ⋖_A e10, because e8 is not in the
    projection; e19 ⋖_B e21, because e20 is not), and e7 ⋖_B e19 is exactly an edge the filter removed
    (both endpoints are included through other paths). So a filtered case "without behaviour of X" still
    carries X's events and, after projection, some of X's df-edges. Recorded per case in the result files
    (`excluded_objects_in_projection`, `projection_df_edges_of_excluded_objects`, `projection_df_edges_not_in_D`).
17. **Outputs:** `start_case_Order__global|any`, `end_case_Order__global|any`,
    `start_case_Order_noSO__global_full|global_filtered|any`, `end_case_Order_noSO__…` (same variants),
    `generalized_summary.json` (boundary objects per reading, event sets, and which variants coincide).

## 2026-10-06 – Projection check (F6, before Step 6)

`r2_python/projection_check.py`, output `results/r2/projection_check.md` (written by `run_all`),
test `r2_python/tests/test_projection_check.py`. X = {A, B} (all Supplier Orders), ties `strict`.

1. **Def. 7 is convex, so projection keeps ⋖.** E_i^o = {e | i ≤ e ≤ o} is convex wrt. ≤ of D: if
   e ≤ e' ≤ e'' with e, e'' ∈ E_i^o then i ≤ e' ≤ o, so e' ∈ E_i^o. Hence for any object, no event of it lies
   between two included events without being included, and ⋖ recomputed on Proj_{E_i^o} D equals ⋖ of D
   restricted to E_i^o. Checked for all 107 event pairs i ≤ o and all 95 non-empty Def. 8 cases
   (self-pairs included): all convex, no extra and no missing df-edge.
2. **Def. 11 is not convex in D.** E_i^o|X̄ is convex only wrt. ≤ of df(D, O \ X) (all 68 filtered event-pair
   executions are). Wrt. ≤ of D, 15 of 68 are not: events reachable between two included events only through
   A's or B's df-edges are dropped (e8, e10 of A; e19–e21 / e20 of B). The projection keeps every object
   correlated to an included event, including A and B, and ⋖ recomputed on it then
   - links events across the dropped ones: **spurious** edges, not df-edges of D
     (e6 ⋖_A e11 dropping e8 e10; e6 ⋖_A e10 dropping e8; e19 ⋖_B e21 dropping e20);
   - brings back df-edges of D on excluded objects: **reintroduced** edges (e6 ⋖_A e8, e10 ⋖_A e11,
     e19 ⋖_B e20).
   Of the 69 non-empty filtered Def. 8 cases, 23 have spurious and 29 reintroduced edges. Non-convexity is
   necessary but not sufficient for a spurious edge (D[O2 → O2 \ X] drops e19–e21 but has none: no included
   object has events on both sides). No df-edge of the filtered graph is ever lost by the projection.
3. **Unions (Def. 10 + 11).** The Step 5 filtered start cases (Fig. 11) are clean in all variants. The filtered
   end cases (Fig. 12) under `global_on="filtered"` and `any` have spurious e6 ⋖_A e10 (∗→O1), e19 ⋖_B e21
   (∗→O2), and reintroduced e10 ⋖_A e11, e19 ⋖_B e20 (∗→O1), e6 ⋖_A e8, e7 ⋖_B e19 (∗→O2). e7 ⋖_B e19 occurs in
   no single filtered Def. 8 case: it comes from the union of two parts. Under `global_on="full"` the end
   cases are clean (B is in ∗→O2 via e7, but has only that one event there). This confirms F6.
4. **Conclusion for the report:** convexity holds for Def. 7 but not for Def. 11, which is why the spurious
   edges appear. A filtered case, taken as an OCED-set (Proj onto D), does not have the behaviour that
   defined it; to keep the filter's meaning, one would have to keep the filtered ⋖ with the result instead of
   recomputing it, or drop X's objects from the projection. Not changed in R2 (paper's definition kept).
5. No behaviour of existing code changed; other result files are byte-identical; 41 tests pass.

## 2026-10-06 – Step 6: comparison with R1

`r2_python/compare_r1.py` → `results/r2/comparison.md` (run after `run_all`). **This is the first time R2
reads `results/r1/`.** Read: all top-level files of `results/r1/` (JSON, CSV, `claims_table.md`) and the three
`raw/*_view.json` files. Still not opened: `r1_neo4j/` code and queries, `docs/r1_log.md`, `external/`.

1. **Mapping.** Each R1 execution file is matched to the R2 variant with the R1 query's semantics
   (no self-pairs, global restriction per object, Def. 10 "any", Def. 11 filtered paths) and to the
   paper's alternatives. Executions are matched by `execution_id` (start/end object). R1's
   `n_paths` / `n_distinct_paths` are not compared (R2 enumerates no paths).
2. **Result: 37 comparisons, 0 unexplained differences.** For every R1 file, the R2 variant with the R1
   query's semantics is equal in executions, events, objects and start/end events.
   - `exec_A_O1`, all five case notions, `all_global_executions` (13), start/end cases, filtered start/end cases.
   - DF edges (29), start/end event per object (12), EKG counts, and the DF edges / case nodes returned by
     the three view queries.
3. **Differences, all explained:**
   - `notion_SO_Order_paths` (0 executions): typo `"Order "` in the published query, not an ambiguity.
   - A3: self-pairs add O1_O1, O2_O2, P1_P1 (13 → 16); "distinct types" drops O2_O1 (13 → 12).
   - Def. 10 global vs. any: only the recorded other-side start/end events differ, never the event or
     object sets.
   - A5: `end_case_Order_noSO__global_full` ("before") is smaller (∗→O1 = e1 e18 e27 e28,
     ∗→O2 = e2 e5 e7 e33 e34); R1 equals the "after" reading.
   - `rel`: R1 has 15 pairs, R2 23. R1 ⊆ R2; the 8 extra pairs are all same-type (I1–I2, X1–X2, …),
     which the tutorial's :REL query does not create (F1). `rel` is not used by Def. 3–11.
   - A1 and A4 cause no difference here: there are no timestamp ties, and by-object = by-type.
4. **R1 open points answered with R2 numbers** (section in `comparison.md`):
   - (1) Def. 10 global = any in event sets for all 8 start/end cases on this log (a property of the data).
   - (2) A5 matters only for Fig. 12. "After" is the reading of the tutorial and of the paper's text
     (Receive SO e6/e19 are only in the "after" cases).
   - (3) 13 / 16 / 12 executions; Order→Order 1 / 3 / 0.
