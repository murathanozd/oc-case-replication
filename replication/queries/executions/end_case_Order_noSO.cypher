// Source: OCPM 3.3, Sect. 6.3, second query (excluding Supplier Orders) - verbatim
MATCH (eStart:Event)-[:START]->(:Entity)
MATCH (eEnd:Event)-[:END]->(:Entity {EntityType: "Order"})
MATCH p=(eStart)-[:DF*]->(eEnd) 
WHERE 
    NONE (df in relationships(p) WHERE df.EntityType = "Supplier Order")
WITH eEnd,collect(p) AS execution
RETURN execution;
