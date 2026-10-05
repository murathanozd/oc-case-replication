// Source: tutorial-ocpm-object-traces.md, Sect. 2.2 (infer end event of an object)
MATCH (n:Entity)
// find e with no outgoing DF edge that refers to n (i.e., there is no edge df with df.ID = n.iD)
MATCH (n)<-[c:CORR]-(e:Event) WHERE NOT (e)-[:DF {ID:n.ID}]->()
// materialize as :END relation 
MERGE (n)<-[:END]-(e);
