// Source: tutorial-ocpm-object-centric-process-executions-generalized.md (OCPM 3.3), Sect. 6.2, first query - verbatim
MATCH (eStart:Event)-[:START]->(:Entity {EntityType: "Order"})
MATCH (eEnd:Event)-[:END]->(:Entity)
MATCH p=(eStart)-[:DF*]->(eEnd) 
WITH eStart,collect(p) AS execution
RETURN execution;
