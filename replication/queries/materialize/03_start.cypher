// Source: tutorial-ocpm-object-traces.md, Sect. 2.2 (infer start event of an object)
MATCH (n:Entity)
// find e with no incoming DF edge that refers to n (i.e., there is no edge df with df.ID = n.iD)
MATCH (n)<-[c:CORR]-(e:Event) WHERE NOT ()-[:DF {ID:n.ID}]->(e)
// materialize as :START relation 
MERGE (n)<-[:START]-(e);
