// Source: tutorial-ocpm-relations.md, Sect. 2 (undirected related object pairs, query only)
MATCH (n1:Entity)<-[:CORR]- (:Event)-[:CORR]->(n2:Entity) 
WHERE n1.EntityType <> n2.EntityType
RETURN DISTINCT n1.ID,n2.ID;
