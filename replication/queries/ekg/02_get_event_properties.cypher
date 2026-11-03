// Source: 1_import_events.py, qGetAllEventProperties
MATCH(e:Event) WITH DISTINCT keys(e) AS props
UNWIND props AS prop WITH DISTINCT prop AS p
RETURN p;
