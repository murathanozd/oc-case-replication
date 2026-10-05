# R1 plan – Direct reproduction of the running example with the authors' Cypher queries

## Context

Repo: `~/TUe/GitHub/oc-case-replication` (remote `github.com/murathanozd/oc-case-replication`).
We replicate the running example of Fahland & Montali, *What is an Object-Centric Case? An Exploration* (LNCS 16480, 2026).
The authors' implementation is the submodule `external/eventgraph_tutorial` (pinned at `31d19b8`), tutorials:

- `order_process/tutorial-your-first-event-knowledge-graph.md` (+ scripts `0_prepare_log_for_import.py`, `1_import_events.py`, `2_build_event_knowledge_graph.py`)
- `order_process/tutorial-ocpm-relations.md` (OCPM 1)
- `order_process/tutorial-ocpm-object-traces.md` (OCPM 2)
- `order_process/tutorial-ocpm-object-centric-process-executions.md` (OCPM 3.1)
- `order_process/tutorial-ocpm-object-centric-process-executions-summarizing.md` (OCPM 3.2)
- `order_process/tutorial-ocpm-object-centric-process-executions-generalized.md` (OCPM 3.3)

Input data: `data/running_example/order_process_event_table_orderhandling.csv` (21 events = Table 1 of the paper).
Object types used in the paper: Order, Supplier Order, Item, Invoice, Payment (NOT Actor, Order Details, Tray).

**Goal of R1:** run the authors' queries as published, record every result, and check each claim the paper makes about the running example (Sect. 4–5, Fig. 5–12). Do not "fix" the authors' queries silently: if something has to change to make it run, keep the original, make a copy with the fix, and log the change.

## Rules for this work

- Work only in `r1_neo4j/`, `results/r1/` and `docs/`. Never edit files inside `external/`.
- Scripts in Python 3 with the `neo4j` driver; Cypher queries in separate `.cypher` files so they can be cited in the report.
- Connection settings from environment variables `NEO4J_URI` (default `bolt://localhost:7687`), `NEO4J_USER` (default `neo4j`), `NEO4J_PASSWORD`. Never hard-code the password.
- Every script must be re-runnable from scratch (start by wiping the database).
- Small commits with plain descriptive messages. Do not add `Co-Authored-By` or any other trailers to commit messages.
- Ask me before installing anything system-wide.

## Step 0 – Manual setup (I do this, you guide me)

1. Install Neo4j Desktop, create a local DBMS (Neo4j 5.x), set a password (≥ 8 characters), install the **APOC** plugin, start it.
2. Write down the Neo4j and APOC versions (needed for the report).
3. Create `.env.example` in the repo root with the three variables (no real password) and make sure `.env` is in `.gitignore`.

## Step 1 – Known pitfalls to handle (log each in `docs/r1_log.md`)

- **Passwords differ across the authors' scripts** (`1234` in the tutorial text, `password` in `2_build_event_knowledge_graph.py`, `12341234` in `1_import_events.py`). We use the env variable everywhere.
- **The tutorial says the file path must not contain a dash** for `LOAD CSV`. Our repo path contains dashes (`oc-case-replication`). Instead of changing `neo4j.conf`, copy the prepared CSV into the DBMS's own `import/` folder (Neo4j Desktop → DBMS → "…" → Open folder → Import) and load it with `file:///<filename>`. Make the script print where it expects the file.
- **Typo in OCPM 3.1, Sect. 3.1:** `"Order " AS endType` has a trailing space, so it returns nothing. Run it as published once, record the empty result, then run the corrected version.
- Neo4j 5 may warn about deprecated `ID(e)` (used for tie-breaking in the DF query). Keep it, but note the warning.

## Step 2 – Build the event knowledge graph (`r1_neo4j/01_build_ekg.py`)

Port (do not rewrite the logic of) `0_prepare_log_for_import.py`, `1_import_events.py`, `2_build_event_knowledge_graph.py`:

1. Prepare the CSV (rename columns, ISO timestamps with `+0100`, sort by time) → `r1_neo4j/prepared/order_process_event_table_orderhandling_prepared.csv`.
2. Wipe DB, import `:Event` nodes, split comma-separated values into lists.
3. Create `:Entity` nodes and `:CORR` for the 5 types only (Order, Supplier Order, Item, Invoice, Payment).
4. Create generic `:DF` relationships with properties `EntityType` and `ID` (the `option_df_typed = False` variant).
5. Sanity checks, printed and saved to `results/r1/ekg_stats.json`:
   - 21 `:Event` nodes
   - 12 `:Entity` nodes: O1, O2, A, B, X1, X2, X3, Y1, Y2, I1, I2, P1
   - number of `:CORR` and `:DF` relationships, and the DF edge list `(e1, e2, objectID)` → `results/r1/df_edges.csv`
   - number of events per timestamp (flag any ties)

## Step 3 – Materialize relations, start/end events (`r1_neo4j/02_materialize.py`)

- `:REL` between objects (OCPM 1, Sect. 4.1) → export `results/r1/rel_edges.csv`.
- `:START` / `:END` per object (OCPM 2, Sect. 2.2) → export `results/r1/start_end.csv` (object, start event, end event). Flag objects with more than one start or end event (the paper's Def. 8 assumes exactly one).

## Step 4 – Executions and case notions (`r1_neo4j/03_executions.py` + `queries/*.cypher`)

For every query below, save the raw result to `results/r1/<name>.json` in one common format:
`[{ "execution_id", "start_object", "end_object", "start_event", "end_event", "events": [sorted event ids], "objects": [sorted object ids of correlated events] }]`.

| name | source | paper reference |
|---|---|---|
| `exec_A_O1` | OCPM 3.1 §2.2/2.3 | Fig. 5, D[e3→e28] / D[A→O1] |
| `notion_SO_Order` | OCPM 3.1 §3.2 | Def. 9, Fig. 6 |
| `all_global_executions` | OCPM 3.1 §4 | Fig. 7 |
| `notion_Order_Payment`, `notion_Order_Invoice`, `notion_Payment_Invoice`, `notion_Order_Order` | OCPM 3.1 §4.1–4.5 | Fig. 8, Fig. 9 |
| `start_case_Order` | OCPM 3.3 §6.2 (first query) | Def. 10, Fig. 10 |
| `start_case_Order_noSO` | OCPM 3.3 §6.2 (filtered) | Def. 11, Fig. 11 |
| `end_case_Order` | OCPM 3.3 §6.3 (first query) | Def. 10 |
| `end_case_Order_noSO` | OCPM 3.3 §6.3 (filtered) | Fig. 12 |

Also time each query (5 runs, mean and std) → `results/r1/runtimes.csv`.

Optional (if time): OCPM 3.2 activity variants and object variants → `results/r1/variants.json`.

## Step 5 – Claim check (`r1_neo4j/04_check_claims.py`)

Encode the paper's claims as checks against the saved JSON and write `results/r1/claims_table.md` with columns: `#`, `claim`, `paper (section/figure)`, `expected`, `observed`, `match (yes/no/partial)`, `note`.

Claims from the paper:

1. D[e3→e28] (Fig. 5) contains the handling of items X1, X2, X3 of supplier order A, with X1, X2 packed and shipped for O1; object layer includes A, X1, X2, X3, O1 and Y1.
2. D[SupplierOrder→Order] has 4 cases: A→O1, A→O2, B→O1, B→O2 (Sect. 5.1).
3. D[A→O1] and D[A→O2] overlap exactly on e3, e6, e8.
4. D[A→O1] and D[B→O1] overlap exactly on e27, e28.
5. Considered start types: Order, Supplier Order, Payment; end types: Order, Invoice, Payment (Sect. 5.2).
6. D[Order→Payment]: 2 executions, both ending in P1.
7. D[Payment→Invoice]: 2 executions (P1→I1, P1→I2), behaviorally just the trace of P1.
8. D[Order→Invoice]: 4 executions, incl. "emergent" O1→I2 and O2→I1; same executions as Order→Payment because of shared end event e30.
9. D[Order→Order]: exactly 1 execution, O2→O1, passing through e7 (Update SO).
10. In total 13 executions between objects with global start/end events (tutorial §4; check against Fig. 7).
11. No executions for Order→Supplier Order, Supplier Order→Invoice, Supplier Order→Payment, and none between distinct objects of the same type except O2→O1.
12. D[Order→∗] (Fig. 10) includes behavior of B and items Y1, Y2 but not of A (the "incompleteness" the paper criticizes).
13. D[Order→∗ \ {SupplierOrder}] (Fig. 11): two cases starting in Create Order, invoices of both cleared by the same payment.
14. D[∗→Order \ {SupplierOrder}] (Fig. 12): contains no Invoice or Payment events; both cases depend on the Receive SO events.

For each claim also note whether the query matches the paper's *definition* or only its *figure* (e.g. Def. 10 restricts end objects to global ends, the tutorial query in OCPM 3.3 §6.2 accepts any `:END` event). Do not resolve these differences in R1 — only record them; R2 will test them.

## Step 6 – Figures

Write the Neo4j Browser queries that reproduce Fig. 4–12 into `r1_neo4j/queries/figures.cypher` (one block per figure, commented with the figure number). I will take the screenshots manually and save them as `results/r1/figures/fig<N>.png`.

## Step 7 – Documentation

- `r1_neo4j/README.md`: exact steps to rerun R1 from a clean machine (versions, env vars, import folder, script order, expected runtime).
- `docs/r1_log.md`: dated log of everything that did not work as described, what we changed, and why. This becomes the "Experiment execution" section of the report.
- `results/r1/environment.json`: Neo4j version, APOC version, Python version, neo4j driver version, OS.

## Definition of done

- `python r1_neo4j/01_build_ekg.py && python r1_neo4j/02_materialize.py && python r1_neo4j/03_executions.py && python r1_neo4j/04_check_claims.py` runs end-to-end on a fresh DB.
- `results/r1/claims_table.md` has a row for each of the 14 claims with an observed value.
- `docs/r1_log.md` lists all deviations.
- Everything committed and pushed.
