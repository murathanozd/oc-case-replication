# Replication: "What is an Object-Centric Case? An Exploration"

Replication study for the 2IMI00 Seminar Process Analytics (TU/e, 2026-GS1).

**Original paper:** D. Fahland, M. Montali. _What is an Object-Centric Case? An Exploration._
In: Wil van der Aalst Festschrift, LNCS 16480, pp. 398-425, Springer, 2026.
https://doi.org/10.1007/978-3-032-17618-9_28

**Authors of this replication:** Murathan Ozdemir, Kallista Komdeur

## Goal

The paper defines object-centric start-to-end executions and case notions over
object-centric event data (OCED) and illustrates them on a small order-handling
example, implemented as Cypher queries over an event knowledge graph in Neo4j.
We replicate this in three steps:

| Part | What                                                                        | Where              |
| ---- | --------------------------------------------------------------------------- | ------------------ |
| R1   | Direct reproduction with the authors' Cypher queries on the running example | `replication/`     |
| R2   | Applying to public OCEL 2.0 log                                             | `replication/`     |
| R3   | Recording running times                                                     | `03_executions.py` |

## Repository layout

```
data/running_example/                 running example event table (Table 1 of the paper)
data/ocel_scientific_publications/    OCEL 2.0 log
external/                             authors' tutorial repo (git submodule, pinned)
replication/                          Neo4j/Cypher reproduction
results/                tables and figures produced by the scripts
```

## Setup

Requires **Python 3.11 or newer** (`pandas==3.0.6` does not install on 3.10 or older).

```bash
git clone --recurse-submodules https://github.com/murathanozd/oc-case-replication.git
cd oc-case-replication
python3 --version          # must be 3.11+
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

If you cloned without `--recurse-submodules`, run `git submodule update --init` (R1 needs
`external/eventgraph_tutorial`).

R1 additionally needs a local Neo4j 5.x DBMS with the APOC plugin and a `.env` file with its
password and import folder. **Step-by-step instructions: [`replication/README.md`](replication/README.md#rerun-from-a-clean-machine).**

`04_check_claims.py` and `05_render_figures.py` read only the committed result files, so they run
without Neo4j (useful to check the setup first).

## Data and code sources

- Running example and Cypher queries: https://github.com/multi-dimensional-process-mining/eventgraph_tutorial
  (LGPL-2.1), pinned at commit `31d19b8`.
- OCEL 2.0 logs: https://www.ocel-standard.org/
