// Source: OCPM 3.1, Sect. 3.2 - verbatim
// Query exeuction from multiple start/end object of the same type and materialize each as new execution node
WITH "Supplier Order" AS startType, "Order" AS endType
MATCH (nStart:Entity {EntityType:startType})<-[:START]-(eStart:Event)
MATCH (nEnd:Entity {EntityType:endType})<-[:END]-(eEnd:Event)
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
