// Source: tutorial-ocpm-relations.md, Sect. 4.1 (materialize directed object relations)
MATCH (n1:Entity)<-[:CORR]-(:Event)-[:CORR]->(n2:Entity) 
WHERE n1.EntityType <> n2.EntityType
WITH DISTINCT n1,n2
MATCH (e1:Event)-[:CORR]->(n1)
MATCH (e2:Event)-[:CORR]->(n2)
WITH n1, min(e1.timestamp) AS t1, n2, min(e2.timestamp) AS t2 
WHERE t1 < t2
MERGE (n1)-[:REL]->(n2);
