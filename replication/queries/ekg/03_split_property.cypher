// Source: 1_import_events.py, qSplitPropertyStringsToList (run once per property except timestamp)
MATCH (e:Event) WHERE e.<<prop>> <> "null" AND e.<<prop>> CONTAINS ',' WITH e,split(e.<<prop>>, ',') AS vals
SET e.<<prop>>=vals;
