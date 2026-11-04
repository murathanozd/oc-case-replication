// Source: 2_build_event_knowledge_graph.py, q_create_directly_follows (option_df_typed = False)
// Ours: ties broken by the event number (EventID e<n>, assigned in log order) instead of the
// published ID(e). ID(e) is Neo4j's internal id, which can be reused after deletes, so events with
// the same timestamp got a different DF order on each rebuild. No effect without timestamp ties
// (running example).
MATCH (n:Entity)
MATCH (n)<-[:CORR]-(e)
WITH n, e AS nodes ORDER BY e.timestamp, toInteger(substring(e.EventID, 1))
WITH n, collect(nodes) AS event_node_list
UNWIND range(0, size(event_node_list)-2) AS i
WITH n, event_node_list[i] AS e1, event_node_list[i+1] AS e2
MERGE (e1)-[df:DF {EntityType:n.EntityType, ID:n.ID}]->(e2);
