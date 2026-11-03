// Source: OCPM 3.1, Sect. 4.3 - not printed in the tutorial; the text says to use WITH "Order" AS startType, "Invoice" AS endType in the query of 4.2
// Retrieve executions (events and DF-relations) between start/end objects of the same type
WITH "Order" AS startType, "Invoice" AS endType
MATCH (nStart:Entity {EntityType:startType}) -[starts:START]-> (x:Execution) <-[ends:END]- (nEnd:Entity {EntityType:endType})
OPTIONAL MATCH (x)<-[:CORR]-(e:Event)-[df:DF]->(e2:Event) WHERE (e2)-[:CORR]->(x)
RETURN e,df,e2;
