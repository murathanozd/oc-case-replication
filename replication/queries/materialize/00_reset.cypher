// Ours: remove relationships derived by this step, so 02_materialize.py is re-runnable on the EKG of 01_build_ekg.py
MATCH (:Entity)-[r:REL]->(:Entity) DELETE r;
MATCH (:Event)-[r:START|END]->(:Entity) DELETE r;
