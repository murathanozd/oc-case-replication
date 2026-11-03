// Source: OCPM 3.1, Sect. 4.2 - verbatim
// Retrieve executions (events and DF-relations) between start/end objects of the same type
WITH "Order" AS startType, "Payment" AS endType
MATCH (nStart:Entity {EntityType:startType}) -[starts:START]-> (x:Execution) <-[ends:END]- (nEnd:Entity {EntityType:endType})
OPTIONAL MATCH (x)<-[:CORR]-(e:Event)-[df:DF]->(e2:Event) WHERE (e2)-[:CORR]->(x)
RETURN e,df,e2;
