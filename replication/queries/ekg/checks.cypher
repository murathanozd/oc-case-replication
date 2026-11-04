// Sanity checks for the EKG (ours, not from the tutorial). One statement per check, in this order:
// 1) events, 2) entities, 3) CORR count, 4) DF count, 5) DF edge list, 6) events per timestamp
MATCH (e:Event) RETURN count(e) AS n;
MATCH (n:Entity) RETURN n.EntityType AS type, n.ID AS id ORDER BY type, id;
MATCH (:Event)-[c:CORR]->(:Entity) RETURN count(c) AS n;
MATCH (:Event)-[d:DF]->(:Event) RETURN count(d) AS n;
MATCH (a:Event)-[d:DF]->(b:Event)
RETURN a.EventID AS e1, b.EventID AS e2, d.EntityType AS entity_type, d.ID AS object_id,
       toString(a.timestamp) AS t1, toString(b.timestamp) AS t2
ORDER BY a.timestamp, toInteger(substring(a.EventID, 1)), b.timestamp, toInteger(substring(b.EventID, 1)), object_id, entity_type;
MATCH (e:Event)
WITH e ORDER BY toInteger(substring(e.EventID, 1))
WITH e.timestamp AS ts, collect(e.EventID) AS events
RETURN toString(ts) AS timestamp, size(events) AS n, events ORDER BY ts;
