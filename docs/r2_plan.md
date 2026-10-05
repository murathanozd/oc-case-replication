# R2 plan – Independent implementation of the paper's definitions

## Context

Repo: `~/TUe/GitHub/oc-case-replication`. R1 is finished on branch `murathan-r1`: the authors' Cypher queries were run in Neo4j on the running example, and every claim of Sect. 4–5 was checked (`results/r1/claims_table.md`, `docs/r1_log.md`).

**Goal of R2:** implement the paper's formal definitions (Def. 1–11, Lemma 1, and the case-notion choices of Sect. 5.2) **directly from the paper text**, in plain Python, without Neo4j and without the authors' code. Then compare the result with R1, event by event.

- If R2 = R1, the paper's definitions and the authors' implementation agree, which is stronger evidence than rerunning their code.
- Every difference is a finding: either the definitions and the code disagree, or the definition is ambiguous. R2 must make each ambiguity explicit and compute **every reasonable reading**.
- R2 is also the basis for R3 (larger OCEL 2.0 logs), so it must scale: no enumeration of paths.

## Rules for this work

- Work on a new branch `murathan-r2`, created from `murathan-r1` (R2 needs the R1 results). Commit and push only to `murathan-r2`, never to `main`.
- Write code in `r2_python/`, results in `results/r2/`, notes in `docs/r2_log.md`.
- **Independence:**
  - Implement from the paper (`Multi-dimensional_Process_Mining.pdf`, Sect. 3–5) only.
  - Do not read the authors' Cypher or the R1 scripts (`r1_neo4j/`) to decide how something works.
  - Read R1 *result files* (`results/r1/*.json`) only in the comparison step (Step 6), after R2's results are written.
  - If you read anything else, say so in `docs/r2_log.md`.
- Input is the raw CSV `data/running_example/order_process_event_table_orderhandling.csv`, read with your own loader (not R1's prepared CSV).
- Plain Python 3.11 with the packages already in `requirements.txt`. networkx may only be used in tests as an independent cross-check, not in the implementation.
- Every result file must be deterministic (sorted output, no timestamps inside files). Reruns must be byte-identical.
- Small commits with plain descriptive messages. No `Co-Authored-By` or other trailers.
- Stop after each step marked **STOP** and report.

## Step 1 – Data model (Def. 1, Def. 2) → `r2_python/oced.py`

- `OCEDSet` with objects O, events E, `type`, `corr ⊆ E×O`, `rel ⊆ O×O`, attributes (activity, timestamp).
- Loader: one event per row; activity from `event`, timestamp from `time` (format `dd.mm.yyyy HH:MM:SS`). Objects come from the columns **Order, Supplier Order, Item, Invoice, Payment** only (comma-separated values). Actor, Order Details and Tray are not objects (the paper lists 5 object types).
- Def. 2: make the set relation-consistent by adding (o, o') to `rel` for every pair correlated to the same event (Sect. 3, "to make the OCED-set relation-consistent…"). Implement `is_relation_consistent()`.
- Sanity numbers (must match): 21 events, 12 objects, 41 corr pairs.

## Step 2 – Behaviour (Def. 3–6, Lemma 1)

- **Def. 3** `df[(e, o, e')]`: local directly-follows per object with **strict** `<` on timestamps.
  - Ambiguity A1: with equal timestamps, strict `<` gives no DF edge between tied events. Implement a parameter `ties = "strict" | "break_by_id"` (default `strict` = paper). The running example has no ties; R3 will need this.
- **Def. 4** partial order `≤` = reflexive-transitive closure of DF, ignoring the object. Implement `leq(e, e')` by reachability (BFS/DFS on the DF graph). Do **not** materialize all paths.
- **Def. 5/6**: DF graph; `start(O')`, `end(O')`; `is_df_path`.
  - Ambiguity A2: Def. 6 literally says e ∈ start(O') iff no o ∈ O' and no e' with e' ≻_o e. Taken literally, events not correlated to O' also qualify. Implement the intended reading (e must be correlated to some o ∈ O') as default, record the literal reading in the log, and show by a test that the literal one gives absurd results (e.g. start({O1}) would contain e3).
- **Lemma 1** check: for all pairs, e < e' (closure) ⟺ there is a df-path from e to e'. Verify it with an independent networkx implementation in a test.
- Partial-order properties (reflexive, antisymmetric, transitive) as tests.

## Step 3 – Operations and executions (Sect. 4, Def. 7, Def. 8) **STOP**

- `E_of(O')` (E[O']), `O_of(E')` (O[E']), `restrict`, `select(O')`, `project(E')`.
- **Def. 7** `execution(i, o)`: E_i^o = {e | i ≤ e ≤ o}, computed as descendants(i) ∩ ancestors(o) (by reachability), then `project`.
- Check the properties stated after Def. 7 as tests: single start event i, single end event o, every event lies on a df-path i…e…o.
- **Def. 8** `case(o_st, o_end)` = execution(start(o_st), end(o_end)). Raise an error if an object has ≠ 1 start or end event (Def. 8's assumption), and report which objects violate it.
- Output `results/r2/exec_A_O1.json` in R1's common format: `{execution_id, start_object, end_object, start_event, end_event, events (sorted), objects (sorted)}`.
- **STOP**: show me D[A→O1] (events + objects) and the start/end event of every object.

## Step 4 – Case notions (Def. 9, Sect. 5.2) **STOP**

- **Def. 9** `case_notion(T_st, T_end)`: one case per pair (o_st, o_end) of those types whose execution is non-empty, i.e. start(o_st) ≤ end(o_end).
  - Ambiguity A3: Def. 9 allows o_st = o_end, but Sect. 5.2 says "pairs of distinct object types" and then discusses D[Order→Order]. Implement a parameter `self_pairs = True | False` and compute both.
- **Sect. 5.2 "global" restriction**: start objects are those whose start event is a global start (no DF predecessor at all); end objects likewise for end events.
  - Ambiguity A4: the restriction can be applied per object (as R1's query does) or per type (all objects of the type must qualify). Implement both and record whether they differ here.
- Outputs in `results/r2/`, one file per case notion and variant: `notion_SO_Order`, `notion_Order_Payment`, `notion_Order_Invoice`, `notion_Payment_Invoice`, `notion_Order_Order`, `all_global_executions` (with `self_pairs` false and true).
- **STOP**: show the table of all global executions for both `self_pairs` settings.

## Step 5 – Start/end cases and filtering (Def. 10, Def. 11) **STOP**

- **Def. 10** `start_case(o)` = union over o_end ∈ O_end of D[o → o_end], where O_end = {o | end(o) ⊆ end(O)} (end event is a global end). `end_case(o)` correspondingly with O_start. Lift to types.
  - Variant "any end": take every object's end event instead of only global ones (this is what R1's tutorial query does). Compute both and compare their event sets and end events.
- **Def. 11** `filtered_execution(i, o, X)`: events on a df-path from i to o that uses **no df-edge (e, x, e') with x ∈ X**. Compute it as reachability in the DF graph with the X-edges removed, not by enumerating paths. X is given as object types (all objects of that type) or as an object set.
  - Then `project` onto those events. Note that the projection still contains excluded objects that are correlated to included events (e.g. B at e7). Keep them, and report them.
  - Ambiguity A5: for filtered start/end cases, O_start / O_end (global start/end) can be determined
    - **before**: on the full DF graph, or
    - **after**: on the DF graph without the X-edges.
    Implement a parameter `global_on = "full" | "filtered"` and compute both for D[Order→∗ \ {SupplierOrder}] and D[∗→Order \ {SupplierOrder}].
- Outputs: `start_case_Order`, `start_case_Order_noSO`, `end_case_Order`, `end_case_Order_noSO` (in each variant, with the variant in the file name).
- **STOP**: show both readings for the filtered end case. I expect "full" to give ∗→O1 = {e1, e18, e27, e28} and "filtered" to give R1's result; confirm or refute this from your own implementation.

## Step 6 – Comparison with R1 → `r2_python/compare_r1.py` **STOP**

Now (and only now) read `results/r1/*.json`. For every R1 result file, find the R2 variant(s) that correspond to it and write `results/r2/comparison.md`:

| R1 file | R2 variant | executions equal? | events equal? | objects equal? | start/end events equal? | difference |

- "equal" means the same set of executions (matched by start/end object or start/end event) with the same sorted event and object lists.
- For every difference, state which ambiguity (A1–A5) or which definition explains it, or mark it as "unexplained" (that would be a real finding: investigate it and log it).
- Add a short section "Answers to the R1 open points" that resolves the three open points at the bottom of `results/r1/claims_table.md` with numbers from R2:
  1. Def. 10, global vs. any start/end events;
  2. Def. 11, before vs. after filtering;
  3. Def. 9, self-pairs and "distinct types".
- **STOP**: show me `comparison.md`.

## Step 7 – Tests, timing, documentation

- `r2_python/tests/` with pytest:
  - the property tests from Steps 2–3;
  - Lemma 1 against networkx;
  - a few hand-made mini OCED sets (3–6 events) whose executions you work out by hand in the test comments, including one with a timestamp tie and one with an object that has two candidate start events;
  - the sanity numbers.
- Timing: for each computation, 1 warm-up run, then 5 timed runs; write mean/std to `results/r2/runtimes.csv`. These are tiny on 21 events; they are the baseline for R3.
- `r2_python/README.md`: how to run (`python -m r2_python.run_all`, `pytest`), the module layout, and the list of ambiguities A1–A5 with the chosen default and the alternative.
- `docs/r2_log.md`: dated log of every interpretation decision, everything that differed from R1 and why, and anything you read besides the paper.
- `results/r2/environment.json`: Python and package versions, OS.

## Definition of done

- `python -m r2_python.run_all` regenerates all of `results/r2/` from the raw CSV in a few seconds, byte-identical across two runs.
- `pytest r2_python` passes.
- `results/r2/comparison.md` covers every R1 result file, and every difference is explained or marked unexplained.
- The three R1 open points are answered with R2 numbers.
- Everything is committed and pushed to `murathan-r2`.
