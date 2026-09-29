# Replication: "What is an Object-Centric Case? An Exploration"

Replication study for the 2IMI00 Seminar Process Analytics (TU/e, 2026-GS1).

**Original paper:** D. Fahland, M. Montali. *What is an Object-Centric Case? An Exploration.*
In: Wil van der Aalst Festschrift, LNCS 16480, pp. 398-425, Springer, 2026.
https://doi.org/10.1007/978-3-032-17618-9_28

**Authors of this replication:** Murathan Ozdemir, Kallista Komdeur

## Goal

The paper defines object-centric start-to-end executions and case notions over
object-centric event data (OCED) and illustrates them on a small order-handling
example, implemented as Cypher queries over an event knowledge graph in Neo4j.
We replicate this in three steps:

| Part | What | Where |
|------|------|-------|
| R1 | Direct reproduction with the authors' Cypher queries on the running example | `r1_neo4j/` |
| R2 | Independent Python implementation of Def. 1-11, compared against R1 | `r2_python/` |
| R3 | Applying both to public OCEL 2.0 logs (case notions, overlap, runtime) | `r3_ocel/` |

## Repository layout

```
data/running_example/   running example event table (Table 1 of the paper)
data/ocel/              OCEL 2.0 logs (downloaded, not committed)
external/               authors' tutorial repo (git submodule, pinned)
r1_neo4j/               Neo4j/Cypher reproduction
r2_python/              independent implementation
r3_ocel/                experiments on OCEL 2.0 logs
results/                tables and figures produced by the scripts
docs/                   plan and notes
report/                 LNCS report sources
```

## Setup

```bash
git clone --recurse-submodules <this repo>
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

R1 additionally needs a local Neo4j 5.x instance with the APOC plugin.

## Data and code sources

- Running example and Cypher queries: https://github.com/multi-dimensional-process-mining/eventgraph_tutorial
  (LGPL-2.1), pinned at commit `31d19b8`.
- OCEL 2.0 logs: https://www.ocel-standard.org/
