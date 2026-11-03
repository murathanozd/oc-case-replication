// Ours: read materialized :Execution nodes into the common result format.
// $startType / $endType / $id are optional filters (null = no filter).
MATCH (nStart:Entity)-[:START]->(x:Execution)<-[:END]-(nEnd:Entity)
WHERE ($startType IS NULL OR nStart.EntityType = $startType)
  AND ($endType IS NULL OR nEnd.EntityType = $endType)
  AND ($id IS NULL OR x.ID = $id)
MATCH (eStart:Event)-[:START]->(x)<-[:END]-(eEnd:Event)
MATCH (e:Event)-[:CORR]->(x)
OPTIONAL MATCH (e)-[:CORR]->(o:Entity)
RETURN x.ID AS execution_id, nStart.ID AS start_object, nEnd.ID AS end_object,
       eStart.EventID AS start_event, eEnd.EventID AS end_event,
       collect(DISTINCT e.EventID) AS events, collect(DISTINCT o.ID) AS objects;
