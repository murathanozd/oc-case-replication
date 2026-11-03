// Source: 2_build_event_knowledge_graph.py, q_create_directly_follows (option_df_typed = False)
// Note: ID(e) is deprecated in Neo4j 5 (elementId). Kept as published; used only for tie-breaking.
MATCH (n:Entity)
MATCH (n)<-[:CORR]-(e)
WITH n, e AS nodes ORDER BY e.timestamp, ID(e)
WITH n, collect(nodes) AS event_node_list
UNWIND range(0, size(event_node_list)-2) AS i
WITH n, event_node_list[i] AS e1, event_node_list[i+1] AS e2
MERGE (e1)-[df:DF {EntityType:n.EntityType, ID:n.ID}]->(e2);
