// Ours: read materialized :Execution nodes into the common result format.
// 1) one row per execution; $startType / $endType / $id are optional filters (null = no filter).
// 2) one row per (execution, event) :CORR edge, grouped in Python: aggregating on the server runs
//    out of transaction memory on real logs (millions of :CORR edges).
MATCH (nStart:Entity)-[:START]->(x:Execution)<-[:END]-(nEnd:Entity)
WHERE ($startType IS NULL OR nStart.EntityType = $startType)
  AND ($endType IS NULL OR nEnd.EntityType = $endType)
  AND ($id IS NULL OR x.ID = $id)
MATCH (eStart:Event)-[:START]->(x)<-[:END]-(eEnd:Event)
RETURN x.ID AS execution_id, nStart.ID AS start_object, nEnd.ID AS end_object,
       eStart.EventID AS start_event, eEnd.EventID AS end_event;
MATCH (e:Event)-[:CORR]->(x:Execution) RETURN x.ID AS execution_id, e.EventID AS event;
