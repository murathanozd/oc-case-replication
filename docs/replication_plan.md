# Replication plan

## What the paper evaluates
- Running example (Sect. 4-5, Fig. 5-12): 21 events, 5 object types. Public.
- Implementation: Cypher queries on an event knowledge graph (footnote 2 -> eventgraph_tutorial).
- Three industrial cases (baggage handling, sterilization, PET recycling): data not public, out of scope.

## Claims to check on the running example
- D[SupplierOrder -> Order]: 4 cases (A->O1, A->O2, B->O1, B->O2); A->O1 and A->O2 overlap on e3, e6, e8
- D[Order -> Payment]: 2 cases, D[Order -> Invoice]: 4 cases (same executions, shared end event e30)
- D[Payment -> Invoice]: 2 cases, D[Order -> Order]: 1 case (O2 -> O1 via Update SO e7)
- 13 executions in total between objects with global start/end events
- No executions Order -> Supplier Order, Supplier Order -> Invoice / Payment
- Start/end cases and filtered cases of Fig. 10, 11, 12

## Points to check (paper vs code)
1. Def. 4/7 use the transitive closure, the Cypher code enumerates all paths (`[:DF*]`).
   Same result by Lemma 1, but enumeration can blow up on larger logs. Feasibility only shown on 21 events.
2. Def. 10 only allows end objects whose end event is a global end; tutorial 3.3 (6.2) groups over any END event.
3. Def. 8 assumes one start and one end event per object; Def. 3 uses strict `<` on timestamps,
   the code breaks ties with the internal node id.
4. Sect. 5.2: "their own invoice P1 and P2" should be I1 and I2.

## Parts
- R1: authors' Cypher in Neo4j on the running example, claim-by-claim table.
- R2: own Python implementation of Def. 1-11, diff against R1.
- R3: OCEL 2.0 logs (Order Management, Logistics, P2P): case notions, #cases, case size,
  overlap, runtime (repeated runs, mean/std), sensitivity to timestamp ties.

## Timeline
- Week 5 (until 4 Oct): setup + R1
- Week 6 (until 11 Oct): R2 + comparison
- Week 7: start R3, questions for the Q&A on Thu 15 Oct
- Week 8-10: report
