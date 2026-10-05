// Ours: remove :Execution nodes and all their relationships (START/END from objects and events, CORR from events)
MATCH (x:Execution) DETACH DELETE x;
