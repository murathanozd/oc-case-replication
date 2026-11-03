// Source: OCPM 3.3, Sect. 6.2, second query (excluding Supplier Orders) - verbatim
MATCH (eStart:Event)-[:START]->(:Entity {EntityType: "Order"})
MATCH (eEnd:Event)-[:END]->(:Entity)
MATCH p=(eStart)-[:DF*]->(eEnd) 
WHERE 
    NONE (df in relationships(p) WHERE df.EntityType = "Supplier Order")
WITH eStart,collect(p) AS execution
RETURN execution;
