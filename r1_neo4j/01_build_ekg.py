"""R1 Step 2: build the event knowledge graph of the running example.

Port of the authors' scripts in external/eventgraph_tutorial/order_process/:
  0_prepare_log_for_import.py  -> prepare_log()
  1_import_events.py           -> import_events()
  2_build_event_knowledge_graph.py -> build_ekg()
The query logic is unchanged; queries live in r1_neo4j/queries/ekg/*.cypher.
Deviations (connection from env vars, CSV via the DBMS import/ folder, full wipe first)
are logged in docs/r1_log.md.

Re-runnable from scratch: the database is wiped at the start.
"""

import csv
import filecmp
import json
import os
import shutil
import sys
import time
from collections import Counter

import pandas as pd

from common import NEO4J_IMPORT_DIR, NEO4J_URI, R1_DIR, REPO_ROOT, RESULTS_DIR, Runner, get_driver, load_cypher

INPUT_FILE = REPO_ROOT / "data" / "running_example" / "order_process_event_table_orderhandling.csv"
PREPARED_DIR = R1_DIR / "prepared"
PREPARED_NAME = "order_process_event_table_orderhandling_prepared.csv"
AUTHORS_PREPARED = (REPO_ROOT / "external" / "eventgraph_tutorial" / "order_process"
                    / "prepared_logs" / PREPARED_NAME)

# Same config as model_entities_from_attributes in 2_build_event_knowledge_graph.py
MODEL_ENTITIES_FROM_ATTRIBUTES = [
    ["Order", "Order", ""],
    ["Supplier Order", "SupplierOrder", ""],
    ["Item", "Item", ""],
    ["Invoice", "Invoice", ""],
    ["Payment", "Payment", ""],
]

EXPECTED_EVENTS = 21
EXPECTED_ENTITIES = {"O1", "O2", "A", "B", "X1", "X2", "X3", "Y1", "Y2", "I1", "I2", "P1"}


# --------------------------------------------------------------------------------------
# 1. Prepare the CSV (port of PrepareOrderHandling in 0_prepare_log_for_import.py)
# --------------------------------------------------------------------------------------
def prepare_log(input_file, output_path, file_name):
    csvLog = pd.read_csv(os.path.realpath(input_file), keep_default_na=True)
    csvLog.drop_duplicates(keep='first', inplace=True)
    csvLog = csvLog.reset_index(drop=True)

    csvLog = csvLog.rename(columns={'event': 'Activity', 'time': 'timestamp', 'User': 'Actor',
                                    'Supplier Order': 'SupplierOrder', 'Order Details': 'Order_Details'})

    sampleList = []
    for index, row in csvLog.iterrows():
        rowList = list(row)
        sampleList.append(rowList)

    header = list(csvLog)
    logSamples = pd.DataFrame(sampleList, columns=header)

    logSamples['timestamp'] = pd.to_datetime(logSamples['timestamp'], format='%d.%m.%Y %H:%M:%S')

    logSamples.fillna(0)  # no-op in the original as well (result not assigned)
    logSamples['timestamp'] = logSamples['timestamp'].map(
        lambda x: x.strftime('%Y-%m-%dT%H:%M:%S.%f')[0:-3] + '+0100')
    logSamples.sort_values(['timestamp'], inplace=True)

    os.makedirs(output_path, exist_ok=True)
    logSamples.to_csv(os.path.join(output_path, file_name), index=False)


# --------------------------------------------------------------------------------------
# 2. Import events (port of 1_import_events.py)
# --------------------------------------------------------------------------------------
def get_log_header(file_name):
    with open(file_name) as f:
        reader = csv.reader(f)
        return list(next(reader))


def create_event_query(file_name, log_header):
    """Same output as CreateEventQuery(fileName, logHeader, 'order_process')."""
    props = []
    for col in log_header:
        col_value = f'datetime(line.{col})' if col in ['timestamp', 'start', 'end'] else 'line.' + col
        props.append(f'{col}: {col_value}')
    [query] = load_cypher("ekg/01_import_events", file=file_name, properties=", ".join(props))
    return query


def copy_to_import_dir(prepared_file):
    if not NEO4J_IMPORT_DIR:
        raise SystemExit("NEO4J_IMPORT_DIR is not set. Set it to the import/ folder of the oc-case DBMS "
                         "(Neo4j Desktop -> DBMS -> ... -> Open folder -> Import), see .env.example.")
    target = os.path.join(NEO4J_IMPORT_DIR, PREPARED_NAME)
    print(f"Copying prepared CSV to the DBMS import folder; LOAD CSV expects it at:\n  {target}\n"
          f"  (loaded as file:///{PREPARED_NAME})")
    shutil.copyfile(prepared_file, target)
    return target


def check_target_dbms(runner):
    """Make sure we are connected to the DBMS whose import/ folder we just wrote to,
    before wiping anything: LOAD CSV only sees files in the connected DBMS's import/ folder."""
    try:
        [row] = runner.run(f'LOAD CSV WITH HEADERS FROM "file:///{PREPARED_NAME}" AS line RETURN count(*) AS n')
    except Exception as exc:
        raise SystemExit(f"Connected DBMS at {NEO4J_URI} cannot read {PREPARED_NAME} from its import "
                         f"folder - probably not the oc-case DBMS. Aborting before wiping.\n{exc}")
    if row["n"] != EXPECTED_EVENTS:
        raise SystemExit(f"Import file has {row['n']} rows, expected {EXPECTED_EVENTS}. Aborting.")


def import_events(runner, prepared_file):
    for q in load_cypher("ekg/00_wipe"):
        runner.run(q)

    print('\nImport events from CSV')
    log_header = get_log_header(prepared_file)
    runner.run(create_event_query(PREPARED_NAME, log_header))

    # split comma-separated string values into lists, for every property except timestamp
    all_properties = [r["p"] for r in runner.run(load_cypher("ekg/02_get_event_properties")[0])]
    all_properties.remove("timestamp")
    for prop in all_properties:
        for q in load_cypher("ekg/03_split_property", prop=prop):
            runner.run(q)


# --------------------------------------------------------------------------------------
# 3./4. Entities, CORR, DF (port of 2_build_event_knowledge_graph.py)
# --------------------------------------------------------------------------------------
def build_ekg(runner):
    # The authors' cleanup (delete :Entity nodes and relations to/from events) is subsumed
    # by the full wipe in import_events().
    for entity_type, attribute, where in MODEL_ENTITIES_FROM_ATTRIBUTES:
        ph = dict(entity_type=entity_type, attribute=attribute, where=where)
        for q in load_cypher("ekg/04_create_entity", **ph):
            runner.run(q)
        for q in load_cypher("ekg/05_correlate", **ph):
            runner.run(q)
    for q in load_cypher("ekg/06_create_df"):
        runner.run(q)


# --------------------------------------------------------------------------------------
# 5. Sanity checks
# --------------------------------------------------------------------------------------
def sanity_checks(runner, prepared_matches_authors):
    q_events, q_entities, q_corr, q_df, q_df_edges, q_ties = load_cypher("ekg/checks")
    quiet = Runner(runner.driver, verbose=False)

    n_events = quiet.run(q_events)[0]["n"]
    entities = quiet.run(q_entities)
    n_corr = quiet.run(q_corr)[0]["n"]
    n_df = quiet.run(q_df)[0]["n"]
    df_edges = quiet.run(q_df_edges)
    per_ts = quiet.run(q_ties)
    ties = [r for r in per_ts if r["n"] > 1]

    entity_ids = {r["id"] for r in entities}
    stats = {
        "events": n_events,
        "events_ok": n_events == EXPECTED_EVENTS,
        "entities": len(entities),
        "entities_ok": entity_ids == EXPECTED_ENTITIES and len(entities) == len(EXPECTED_ENTITIES),
        "entities_by_type": {t: sorted(r["id"] for r in entities if r["type"] == t)
                             for t in sorted({r["type"] for r in entities})},
        "corr": n_corr,
        "corr_by_type": dict(sorted(Counter(r["type"] for r in quiet.run(
            "MATCH (:Event)-[:CORR]->(n:Entity) RETURN n.EntityType AS type")).items())),
        "df": n_df,
        "df_by_type": dict(sorted(Counter(r["entity_type"] for r in df_edges).items())),
        "distinct_timestamps": len(per_ts),
        "timestamp_ties": ties,
        "prepared_csv_identical_to_authors": prepared_matches_authors,
        "server_notifications": runner.notifications,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / "ekg_stats.json", "w") as f:
        json.dump(stats, f, indent=2)
    with open(RESULTS_DIR / "df_edges.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["e1", "e2", "entity_type", "object_id", "t1", "t2"])
        for r in df_edges:
            w.writerow([r["e1"], r["e2"], r["entity_type"], r["object_id"], r["t1"], r["t2"]])

    print("\n=== Sanity checks ===")
    print(f"Events:   {n_events} (expected {EXPECTED_EVENTS}) {'OK' if stats['events_ok'] else 'MISMATCH'}")
    print(f"Entities: {len(entities)} {'OK' if stats['entities_ok'] else 'MISMATCH'}")
    for t, ids in stats["entities_by_type"].items():
        print(f"  {t:15s} {', '.join(ids)}")
    print(f"CORR:     {n_corr}  by type {stats['corr_by_type']}")
    print(f"DF:       {n_df}  by type {stats['df_by_type']}")
    for r in df_edges:
        print(f"  {r['e1']:>4} -> {r['e2']:<4} [{r['entity_type']} {r['object_id']}]")
    print(f"Timestamps: {len(per_ts)} distinct for {n_events} events; ties: "
          + (", ".join(f"{r['timestamp']}: {r['events']}" for r in ties) if ties else "none"))
    print(f"Prepared CSV identical to authors' prepared_logs file: {prepared_matches_authors}")
    print(f"Server notifications: {len(runner.notifications)}")
    print(f"\nWrote {RESULTS_DIR / 'ekg_stats.json'} and {RESULTS_DIR / 'df_edges.csv'}")
    return stats


def main():
    t0 = time.time()
    prepare_log(INPUT_FILE, PREPARED_DIR, PREPARED_NAME)
    prepared_file = PREPARED_DIR / PREPARED_NAME
    prepared_matches_authors = filecmp.cmp(prepared_file, AUTHORS_PREPARED, shallow=False)
    print(f"Prepared {prepared_file} (identical to authors' file: {prepared_matches_authors})")

    copy_to_import_dir(prepared_file)

    driver = get_driver()
    try:
        runner = Runner(driver)
        check_target_dbms(runner)
        import_events(runner, prepared_file)
        build_ekg(runner)
        stats = sanity_checks(runner, prepared_matches_authors)
    finally:
        driver.close()
    print(f"Done in {time.time() - t0:.1f} s")
    return 0 if stats["events_ok"] and stats["entities_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
