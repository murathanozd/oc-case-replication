// Source: OCPM 3.3, Sect. 6.3, first query - verbatim
MATCH (eStart:Event)-[:START]->(:Entity)
MATCH (eEnd:Event)-[:END]->(:Entity {EntityType: "Order"})
MATCH p=(eStart)-[:DF*]->(eEnd) 
WITH eEnd,collect(p) AS execution
RETURN execution;
