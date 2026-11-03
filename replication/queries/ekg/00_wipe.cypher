// Source: 1_import_events.py, Step 1.a (delete existing DB contents)
MATCH ()-[r]->() DELETE r;
MATCH (n) DELETE n;
