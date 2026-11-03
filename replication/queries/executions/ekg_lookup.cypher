// Ours: EKG facts used to post-process path results. 1) event -> correlated objects, 2) object start/end events
MATCH (e:Event) OPTIONAL MATCH (e)-[:CORR]->(o:Entity) RETURN e.EventID AS event, collect(o.ID) AS objects;
MATCH (s:Event)-[:START]->(n:Entity)<-[:END]-(t:Event) RETURN n.ID AS object, n.EntityType AS type, s.EventID AS start, t.EventID AS end;
