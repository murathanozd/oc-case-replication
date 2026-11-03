// Source: OCPM 3.1, Sect. 4 - verbatim
// Query all executions between global start/end events of different objects
MATCH (nStart:Entity)<-[:START]-(eStart:Event) WHERE NOT ()-[:DF]->(eStart)
MATCH (nEnd:Entity)<-[:END]-(eEnd:Event)  WHERE NOT (eEnd)-[:DF]->() AND nEnd <> nStart
MATCH p=(eStart)-[:DF*]->(eEnd)

// materialize execution (same query as before, included for completeness)
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
