// Source: OCPM 3.1, Sect. 2.3 - verbatim (query graph of the materialized execution from A to O1)
// query graph of object-centric start-to-end execution from A to O1
MATCH (nStart:Entity {ID:"A"}) -[starts:START]-> (x:Execution) <-[ends:END]- (nEnd:Entity {ID:"O1"})
OPTIONAL MATCH (x)<-[:CORR]-(e:Event)-[df:DF]->(e2:Event) WHERE (e2)-[:CORR]->(x)
RETURN e,df,e2;
