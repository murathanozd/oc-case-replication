// Source: OCPM 3.1, Sect. 3.1 - verbatim, INCLUDING the published typo "Order " (trailing space)
// Query DF-paths from start object type to end object type 
WITH "Supplier Order" AS startType, "Order " AS endType
// get start event of object of the startType
MATCH (n1:Entity {EntityType:startType})<-[c1:START]-(e1:Event)
// get end event of object of endType
MATCH (eN:Event)-[cN:END]->(n2:Entity {EntityType:endType})
// get path from start event to end event
MATCH p=(e1)-[:DF*]->(eN)
RETURN p;
