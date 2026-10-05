// Exports for Step 3 (ours). 1) REL edges with first timestamps, 2) START/END events per object
MATCH (n1:Entity)-[:REL]->(n2:Entity)
MATCH (e1:Event)-[:CORR]->(n1)
MATCH (e2:Event)-[:CORR]->(n2)
WITH n1, min(e1.timestamp) AS t1, n2, min(e2.timestamp) AS t2
RETURN n1.ID AS n1, n1.EntityType AS type1, toString(t1) AS t1,
       n2.ID AS n2, n2.EntityType AS type2, toString(t2) AS t2
ORDER BY t1, n1, t2, n2;
MATCH (n:Entity)
OPTIONAL MATCH (s:Event)-[:START]->(n)
WITH n, s ORDER BY s.timestamp
WITH n, collect(s.EventID) AS starts
OPTIONAL MATCH (t:Event)-[:END]->(n)
WITH n, starts, t ORDER BY t.timestamp
WITH n, starts, collect(t.EventID) AS ends
RETURN n.ID AS object, n.EntityType AS type, starts, ends
ORDER BY type, object;
