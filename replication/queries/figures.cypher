// =====================================================================================================
// Neo4j Browser queries reproducing Fig. 4-12 of Fahland & Montali, "What is an Object-Centric Case?"
//
// Prerequisites: run 01_build_ekg.py, 02_materialize.py and 03_executions.py (the last one leaves the
// 13 :Execution nodes of OCPM 3.1 Sect. 4 in the graph; Fig. 6 and Fig. 7 use them).
//
// Browser settings before taking screenshots (Settings, gear icon, bottom left):
//   - UNTICK "Connect result nodes". Otherwise the Browser adds every relationship between returned
//     nodes, e.g. the Supplier Order DF edges that Fig. 11/12 filter out, or :CORR edges to :Execution.
//   - Initial node display / max neighbours: default is fine (all figures have < 60 nodes).
// Captions: :Event -> Activity (or EventID), :Entity -> ID, :DF -> ID, :Execution -> ID.
//
// Each block is one statement; paste it into the Browser on its own. Blocks are ours (built from the
// tutorial queries cited per block); they return
//   paths (events + DF edges), corr (:CORR edges to the objects), and where the figure shows an
//   object layer, rels (:REL edges between the returned objects, from OCPM 1).
// Note: the paper's figures label O2's Pack Shipment / Ship as e31 / e32; in Table 1 and the data
// they are e33 / e34.
// =====================================================================================================


// ---- Fig. 4: OCED-Graph of the running example ---------------------------------------------------
// All events and DF edges; like the paper, only the :CORR edge to the first event of each object.
MATCH p=(:Event)-[:DF]->(:Event)
RETURN p
UNION
MATCH p=(e:Event)-[:CORR]->(n:Entity) WHERE (e)-[:START]->(n)
RETURN p;


// ---- Fig. 5: start-to-end execution D[e3 -> e28] = D[A -> O1] ------------------------------------
// Paths as in OCPM 3.1 Sect. 2.1/2.3 (start event of A to end event of O1), with object layer.
MATCH (nStart:Entity {ID:"A"})<-[:START]-(eStart:Event)
MATCH (nEnd:Entity {ID:"O1"})<-[:END]-(eEnd:Event)
MATCH p=(eStart)-[:DF*]->(eEnd)
WITH collect(p) AS paths
UNWIND paths AS p UNWIND nodes(p) AS e
MATCH c=(e)-[:CORR]->(n:Entity)
WITH paths, collect(DISTINCT c) AS corr, collect(DISTINCT n) AS objs
OPTIONAL MATCH r=(o1:Entity)-[:REL]->(o2:Entity) WHERE o1 IN objs AND o2 IN objs
RETURN paths, corr, collect(r) AS rels;


// ---- Fig. 6: all cases D[SupplierOrder -> Order], with D[A -> O1] and D[A -> O2] as case nodes ----
// Paths as in OCPM 3.1 Sect. 3.1 (fixed "Order"); case nodes = :Execution A_O1, A_O2 (Sect. 3.2/4)
// with their :CORR edges from events and :START/:END edges from objects.
MATCH (nStart:Entity {EntityType:"Supplier Order"})<-[:START]-(eStart:Event)
MATCH (nEnd:Entity {EntityType:"Order"})<-[:END]-(eEnd:Event)
MATCH p=(eStart)-[:DF*]->(eEnd)
WITH collect(p) AS paths, collect(DISTINCT nStart) + collect(DISTINCT nEnd) AS objs
MATCH (x:Execution) WHERE x.ID IN ["A_O1", "A_O2"]
MATCH cx=(:Event)-[:CORR]->(x)
MATCH se=(:Entity)-[:START|END]->(x)
UNWIND paths AS p UNWIND nodes(p) AS e
MATCH so=(e)-[:CORR]->(o:Entity) WHERE o IN objs
RETURN paths, collect(DISTINCT cx) AS case_corr, collect(DISTINCT se) AS case_ends, collect(DISTINCT so) AS corr;


// ---- Fig. 7: all start-to-end cases of the running example (13 :Execution nodes) ------------------
// Verbatim from OCPM 3.1 Sect. 4.
MATCH (yStart:Entity)-[s:START]->(x:Execution)<-[e:END]-(yEnd:Entity) RETURN yStart,s,x,e,yEnd;


// ---- Fig. 8 (left): cases from Order to Payment / Invoice ---------------------------------------
MATCH (nStart:Entity {EntityType:"Order"})<-[:START]-(eStart:Event)
MATCH (nEnd:Entity)<-[:END]-(eEnd:Event) WHERE nEnd.EntityType IN ["Payment", "Invoice"]
MATCH p=(eStart)-[:DF*]->(eEnd)
WITH collect(p) AS paths
UNWIND paths AS p UNWIND nodes(p) AS e
MATCH c=(e)-[:CORR]->(n:Entity)
WITH paths, collect(DISTINCT c) AS corr, collect(DISTINCT n) AS objs
OPTIONAL MATCH r=(o1:Entity)-[:REL]->(o2:Entity) WHERE o1 IN objs AND o2 IN objs
RETURN paths, corr, collect(r) AS rels;


// ---- Fig. 8 (right): cases from Payment to Invoice ----------------------------------------------
MATCH (nStart:Entity {EntityType:"Payment"})<-[:START]-(eStart:Event)
MATCH (nEnd:Entity {EntityType:"Invoice"})<-[:END]-(eEnd:Event)
MATCH p=(eStart)-[:DF*]->(eEnd)
WITH collect(p) AS paths
UNWIND paths AS p UNWIND nodes(p) AS e
MATCH c=(e)-[:CORR]->(n:Entity)
WITH paths, collect(DISTINCT c) AS corr, collect(DISTINCT n) AS objs
OPTIONAL MATCH r=(o1:Entity)-[:REL]->(o2:Entity) WHERE o1 IN objs AND o2 IN objs
RETURN paths, corr, collect(r) AS rels;


// ---- Fig. 9: cases from Order to Order (D[O2 -> O1]) --------------------------------------------
// nEnd <> nStart as in OCPM 3.1 Sect. 4 (otherwise D[O1 -> O1] and D[O2 -> O2] are added, see claim 9).
MATCH (nStart:Entity {EntityType:"Order"})<-[:START]-(eStart:Event)
MATCH (nEnd:Entity {EntityType:"Order"})<-[:END]-(eEnd:Event) WHERE nEnd <> nStart
MATCH p=(eStart)-[:DF*]->(eEnd)
WITH collect(p) AS paths
UNWIND paths AS p UNWIND nodes(p) AS e
MATCH c=(e)-[:CORR]->(n:Entity)
WITH paths, collect(DISTINCT c) AS corr, collect(DISTINCT n) AS objs
OPTIONAL MATCH r=(o1:Entity)-[:REL]->(o2:Entity) WHERE o1 IN objs AND o2 IN objs
RETURN paths, corr, collect(r) AS rels;


// ---- Fig. 10: start cases D[Order -> *] ----------------------------------------------------------
// Paths from OCPM 3.3 Sect. 6.2 (first query).
MATCH (eStart:Event)-[:START]->(:Entity {EntityType: "Order"})
MATCH (eEnd:Event)-[:END]->(:Entity)
MATCH p=(eStart)-[:DF*]->(eEnd)
WITH collect(p) AS paths
UNWIND paths AS p UNWIND nodes(p) AS e
MATCH c=(e)-[:CORR]->(n:Entity)
WITH paths, collect(DISTINCT c) AS corr, collect(DISTINCT n) AS objs
OPTIONAL MATCH r=(o1:Entity)-[:REL]->(o2:Entity) WHERE o1 IN objs AND o2 IN objs
RETURN paths, corr, collect(r) AS rels;


// ---- Fig. 11: start cases D[Order -> * \ {SupplierOrder}] ----------------------------------------
// Paths from OCPM 3.3 Sect. 6.2 (second query, excluding Supplier Order DF edges).
MATCH (eStart:Event)-[:START]->(:Entity {EntityType: "Order"})
MATCH (eEnd:Event)-[:END]->(:Entity)
MATCH p=(eStart)-[:DF*]->(eEnd)
WHERE NONE (df in relationships(p) WHERE df.EntityType = "Supplier Order")
WITH collect(p) AS paths
UNWIND paths AS p UNWIND nodes(p) AS e
MATCH c=(e)-[:CORR]->(n:Entity)
WITH paths, collect(DISTINCT c) AS corr, collect(DISTINCT n) AS objs
OPTIONAL MATCH r=(o1:Entity)-[:REL]->(o2:Entity) WHERE o1 IN objs AND o2 IN objs
RETURN paths, corr, collect(r) AS rels;


// ---- Fig. 12: end cases D[* -> Order \ {SupplierOrder}] ------------------------------------------
// Paths from OCPM 3.3 Sect. 6.3 (second query, excluding Supplier Order DF edges).
MATCH (eStart:Event)-[:START]->(:Entity)
MATCH (eEnd:Event)-[:END]->(:Entity {EntityType: "Order"})
MATCH p=(eStart)-[:DF*]->(eEnd)
WHERE NONE (df in relationships(p) WHERE df.EntityType = "Supplier Order")
WITH collect(p) AS paths
UNWIND paths AS p UNWIND nodes(p) AS e
MATCH c=(e)-[:CORR]->(n:Entity)
WITH paths, collect(DISTINCT c) AS corr, collect(DISTINCT n) AS objs
OPTIONAL MATCH r=(o1:Entity)-[:REL]->(o2:Entity) WHERE o1 IN objs AND o2 IN objs
RETURN paths, corr, collect(r) AS rels;
