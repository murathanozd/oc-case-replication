// Source: 1_import_events.py, CreateEventQuery(fileName, logHeader, 'order_process')
// <<file>> = name of the prepared CSV in the DBMS import/ folder (authors: absolute path)
// <<properties>> = one "col: line.col" per CSV column, timestamp as datetime(line.timestamp)
CALL {LOAD CSV WITH HEADERS FROM "file:///<<file>>" as line CREATE (e:Event { Log: "order_process", <<properties>> })} IN TRANSACTIONS;
