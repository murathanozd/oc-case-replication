# R1 - Direct reproduction (Neo4j)

Run the authors' Cypher queries (tutorials OCPM 1, 2, 3.1-3.3) on the running example and
check every claim of Sect. 4-5 / Fig. 5-12 of the paper.
Deviations from the tutorials and everything that did not work as described: [`docs/r1_log.md`](../docs/r1_log.md).
Claim-by-claim result: [`results/r1/claims_table.md`](../results/r1/claims_table.md).

## Versions used

| | |
|---|---|
| Neo4j | 5.26.19 Enterprise (Neo4j Desktop), APOC 5.26.19 |
| Python | 3.11.8 |
| Packages | pinned in [`requirements.txt`](../requirements.txt) (neo4j driver 6.4.0, pandas 3.0.6, ...) |
| OS | macOS 26.6.2 (arm64) |
| Authors' tutorial | `external/eventgraph_tutorial` @ `31d19b8` (git submodule) |

The exact record is written to `results/r1/environment.json` by `00_environment.py`.

## Rerun from a clean machine

1. **Clone with the submodule** and set up Python:
   ```bash
   git clone --recurse-submodules https://github.com/murathanozd/oc-case-replication.git
   cd oc-case-replication
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Neo4j:** install Neo4j Desktop, create a local DBMS with Neo4j 5.x (we used 5.26.19), set a password,
   install the **APOC** plugin, start the DBMS. No changes to `neo4j.conf` are needed.
3. **Find the DBMS import folder:** Neo4j Desktop → DBMS → "…" → Open folder → Import.
4. **Create `.env`** in the repo root (copy [`.env.example`](../.env.example)):
   ```
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=<your password>
   NEO4J_IMPORT_DIR=<path of the import folder from step 3>
   ```
   Real environment variables override `.env`. The password is never printed.
5. **Run the scripts in order** (from the repo root, venv active):
   ```bash
   python r1_neo4j/00_environment.py
   python r1_neo4j/01_build_ekg.py
   python r1_neo4j/02_materialize.py
   python r1_neo4j/03_executions.py
   python r1_neo4j/04_check_claims.py
   python r1_neo4j/05_render_figures.py
   ```
   Expected runtime: about 10 s in total (each Step 4 query takes 1–25 ms on the 21-event graph;
   rendering the figures takes a few seconds).

**Warning:** `01_build_ekg.py` **deletes everything** in the connected database. Before wiping, it checks
that the connected DBMS can read the prepared CSV from `NEO4J_IMPORT_DIR`, and aborts otherwise. Use a
DBMS that holds nothing else.

## Scripts

| script | plan step | does | writes (`results/r1/`) |
|---|---|---|---|
| `00_environment.py` | 7 | asks the server for Neo4j / APOC versions; Python, package and OS versions | `environment.json` |
| `01_build_ekg.py` | 2 | prepares the CSV (port of `0_prepare_log_for_import.py`), copies it to the import folder, wipes the DB, imports `:Event`s, creates `:Entity`, `:CORR`, generic `:DF` for Order, Supplier Order, Item, Invoice, Payment | `ekg_stats.json`, `df_edges.csv` |
| `02_materialize.py` | 3 | `:REL` (OCPM 1 §4.1), `:START` / `:END` (OCPM 2 §2.2); first removes these relationships | `rel_edges.csv`, `start_end.csv`, `materialize_stats.json` |
| `03_executions.py` | 4 | OCPM 3.1 / 3.3 execution and case queries, each 1 warm-up + 5 timed runs; materializing queries start without `:Execution` nodes | `<name>.json` (common format), `raw/<name>.json`, `runtimes.csv` |
| `04_check_claims.py` | 5 | checks the paper's 14 claims against the saved results (no DB access) | `claims_table.md`, `claims.json` |
| `05_render_figures.py` | 6 | renders Fig. 4–12 from the saved results and `df_edges.csv` with matplotlib (no DB access) | `figures/fig<N>.pdf`, `figures/fig<N>.png` |

Each script can be rerun on its own (02–05 need the output of the previous ones). Rerunning the chain
gives byte-identical result files, except `runtimes.csv` and `environment.json`. The figure PDFs are
byte-identical with the pinned matplotlib version (3.11.2); the PNGs are pixel-identical but their bytes can
differ across operating systems (checked on Linux against the committed macOS files). Other matplotlib
versions give slightly different font rendering and image sizes.

## Queries

All Cypher is in [`queries/`](queries/) and cites its source in a header comment:

- `ekg/` – EKG construction (from the authors' Python scripts; f-string parts as `<<placeholder>>`)
- `materialize/` – OCPM 1 and OCPM 2 queries, verbatim
- `executions/` – OCPM 3.1 / 3.3 queries, verbatim unless marked: `notion_SO_Order_paths_fixed.cypher`
  (fix of the `"Order "` typo) and `notion_Order_Invoice.cypher` (§4.3, built from the text);
  `00_wipe_executions`, `extract_executions`, `ekg_lookup` are ours
- `figures.cypher` – Neo4j Browser queries for Fig. 4–12 (see below)

## Figures

The figures in `results/r1/figures/` (`fig4` … `fig12`, `fig8_left`, `fig8_right`; PDF for LaTeX,
PNG for viewing) are **rendered by `05_render_figures.py` from the R1 result files**, not screenshotted.
Layout: one lane per object (grouped by type), events on the x-axis in time order, DF edges as arrows in
the lane of their object, a vertical line joining the objects of one event; for the filtered cases
(Fig. 11, 12) the Supplier Order lanes are grey and their DF edges are omitted.

Why not screenshots: Neo4j Query (and Neo4j Browser with "Connect result nodes" on) automatically draws
every stored relationship between returned nodes, so the DF edges that a filtered case excludes would
reappear in Fig. 11 / 12.

[`queries/figures.cypher`](queries/figures.cypher) remains available for exploring the figures
interactively in Neo4j Browser (untick "Connect result nodes" in its settings first; Fig. 6 and 7 need the
`:Execution` nodes left by `03_executions.py`).

The paper's figures label O2's Pack Shipment / Ship events as e31 / e32; in Table 1 and the data they
are e33 / e34.
