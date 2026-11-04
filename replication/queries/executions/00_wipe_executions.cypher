// Ours: remove :Execution nodes and all their relationships (START/END from objects and events, CORR from events).
// In batches: on real logs the executions have millions of CORR edges, too many for one transaction.
MATCH (x:Execution) CALL (x) { DETACH DELETE x } IN TRANSACTIONS OF 100 ROWS;
