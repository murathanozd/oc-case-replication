// Source: tutorial-ocpm-object-centric-process-executions.md (OCPM 3.1), Sect. 2.3 - verbatim
// Query execution from start object to end object and materialize as new node
WITH "A" AS start, "O1" AS end
MATCH (nStart:Entity {ID:start})<-[:START]-(eStart:Event)
MATCH (nEnd:Entity {ID:end})<-[:END]-(eEnd:Event)
MATCH p=(eStart)-[:DF*]->(eEnd)

// materialize execution
  // collect all unique events in the execution between start object/event and end object/event
  UNWIND nodes(p) AS event
  WITH DISTINCT nStart, nEnd, eStart, eEnd, event
  WITH nStart, nEnd, eStart, eEnd, collect(event) AS executionEvents

  // materialize execution for chosen start/end objects and events
  MERGE (nStart)-[:START]->(x:Execution {ID: nStart.ID+"_"+nEnd.ID})<-[:END]-(nEnd)
  MERGE (eStart)-[:START]->(x)<-[:END]-(eEnd)

  // link events to execution
  WITH x, executionEvents
  UNWIND executionEvents AS event
  MERGE (event)-[:CORR]->(x);
