// Source: 2_build_event_knowledge_graph.py, q_correlate_events_to_entity
MATCH (e:Event) <<where>>
UNWIND e.<<attribute>> AS id
MATCH (n:Entity {EntityType: "<<entity_type>>" }) WHERE n.ID = id
CREATE (e)-[:CORR]->(n);
