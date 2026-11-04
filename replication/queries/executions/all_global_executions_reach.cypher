// Ours: same result as all_global_executions.cypher (OCPM 3.1, Sect. 4), without enumerating DF paths.
// The published query collects the events on all paths (eStart)-[:DF*]->(eEnd). That set equals
// {e | eStart -DF*-> e -DF*-> eEnd}: descendants of eStart that are ancestors of eEnd.
// Equal because DF follows one global order (timestamp, ID(e)), so the DF graph is acyclic and
// every walk eStart ->* e ->* eEnd is a path. Both sets come from breadth-first searches
// (apoc.path.subgraphNodes visits every node once), so the cost is polynomial, not #paths.
// Materialization (MERGE part) is the same as in the published query, but committed in one
// transaction per global start event: on real logs it creates millions of :CORR edges, more than
// Neo4j's default transaction memory limit (dbms.memory.transaction.total.max) allows at once.

MATCH (eStart:Event)-[:START]->(:Entity) WHERE NOT ()-[:DF]->(eStart)
WITH DISTINCT eStart
CALL (eStart) {
  // descendants of eStart (incl. itself)
  CALL apoc.path.subgraphNodes(eStart, {relationshipFilter: "DF>"}) YIELD node
  WITH collect(node) AS fromStart

  // global end events reachable from eStart
  UNWIND [e IN fromStart WHERE e <> eStart AND NOT EXISTS { (e)-[:DF]->() } AND EXISTS { (e)-[:END]->(:Entity) }] AS eEnd

  // ancestors of eEnd among the descendants of eStart: every node on a path e ->* eEnd with e
  // reachable from eStart is itself reachable from eStart, so this search needs no other nodes
  CALL apoc.path.subgraphNodes(eEnd, {relationshipFilter: "<DF", whitelistNodes: fromStart}) YIELD node
  WITH eEnd, collect(node) AS executionEvents
  MATCH (nStart:Entity)<-[:START]-(eStart)
  MATCH (nEnd:Entity)<-[:END]-(eEnd) WHERE nEnd <> nStart

  // materialize execution for chosen start/end objects and events (as in the published query)
  MERGE (nStart)-[:START]->(x:Execution {ID: nStart.ID+"_"+nEnd.ID})<-[:END]-(nEnd)
  MERGE (eStart)-[:START]->(x)<-[:END]-(eEnd)

  // link events to execution
  WITH x, executionEvents
  UNWIND executionEvents AS event
  MERGE (event)-[:CORR]->(x)
} IN TRANSACTIONS OF 1 ROW;
