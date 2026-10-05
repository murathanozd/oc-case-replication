"""Shared helpers for the R1 scripts: settings from .env / environment, Neo4j driver,
loading .cypher files, and collecting server notifications (e.g. deprecation warnings)."""

import os
from pathlib import Path

from neo4j import GraphDatabase

REPO_ROOT = Path(__file__).resolve().parent.parent
R1_DIR = REPO_ROOT / "r1_neo4j"
QUERY_DIR = R1_DIR / "queries"
RESULTS_DIR = REPO_ROOT / "results" / "r1"


def load_dotenv(path=REPO_ROOT / ".env"):
    """Minimal .env reader (KEY=VALUE lines). Real environment variables take precedence."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv()

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_IMPORT_DIR = os.environ.get("NEO4J_IMPORT_DIR")


def get_driver():
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise SystemExit("NEO4J_PASSWORD is not set (put it in .env, see .env.example).")
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, password))


def load_cypher(name, **placeholders):
    """Read queries/<name>.cypher, fill <<placeholder>> markers, and split into statements.

    Statements are separated by ';' at the end of a line; lines starting with '//' are comments.
    """
    text = (QUERY_DIR / f"{name}.cypher").read_text()
    for key, value in placeholders.items():
        text = text.replace(f"<<{key}>>", str(value))
    lines = [l for l in text.splitlines() if not l.strip().startswith("//")]
    statements = [s.strip() for s in "\n".join(lines).split(";\n")]
    return [s.rstrip(";").strip() for s in statements if s.strip()]


class Runner:
    """Runs auto-commit queries and records every server notification it gets back."""

    def __init__(self, driver, verbose=True):
        self.driver = driver
        self.verbose = verbose
        self.notifications = []

    def run(self, query, **params):
        if self.verbose:
            print("\n" + query)
        with self.driver.session() as session:
            result = session.run(query, **params)
            records = [r.data() for r in result]
            summary = result.consume()
        for entry in notifications_of(summary):
            entry["query"] = " ".join(query.split())[:200]
            self.notifications.append(entry)
            print(f"  [server notification] {entry['gql_status']}: {entry['description']}")
        return records


def notifications_of(summary):
    """Warnings/infos returned by the server (GQL status objects that are notifications).
    Note: the server only reports them when it plans a query, i.e. not for cached plans;
    run the query with EXPLAIN to get them reliably."""
    return [{"gql_status": g.gql_status, "classification": str(g.raw_classification),
             "severity": str(g.raw_severity), "description": g.status_description}
            for g in summary.gql_status_objects if g.is_notification]
