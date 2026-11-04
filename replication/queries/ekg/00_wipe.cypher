// Source: 1_import_events.py, Step 1.a (delete existing DB contents)
// Ours: in batches instead of `MATCH ()-[r]->() DELETE r; MATCH (n) DELETE n;` - after the executions
// of a real log the DB has millions of relationships, too many for one transaction. Same result.
MATCH (n) CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 100 ROWS;
