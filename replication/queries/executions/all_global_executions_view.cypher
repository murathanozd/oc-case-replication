// Source: OCPM 3.1, Sect. 4 - verbatim (retrieve the materialized execution nodes)
MATCH (yStart:Entity)-[s:START]->(x:Execution)<-[e:END]-(yEnd:Entity) RETURN yStart,s,x,e,yEnd;
