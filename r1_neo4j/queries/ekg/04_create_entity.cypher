// Source: 2_build_event_knowledge_graph.py, q_create_entity (WHERE_event_property left empty, as in the authors' config)
MATCH (e:Event) <<where>>
UNWIND e.<<attribute>> AS id
MERGE (en:Entity {ID:id, uID:("<<entity_type>>"+toString(id)), EntityType:"<<entity_type>>" });
