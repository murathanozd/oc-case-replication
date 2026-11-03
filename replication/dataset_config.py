from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATASETS = {
    "running_example": {
        "input": ROOT / "data" / "running_example" / "order_process_event_table_orderhandling.csv",
        "prepared_name": "order_process_event_table_orderhandling_prepared.csv",
        "date_format": "%d.%m.%Y %H:%M:%S",
        "rename": {"event": "Activity", "time": "timestamp", "User": "Actor",
                   "Supplier Order": "SupplierOrder", "Order Details": "Order_Details"},
        # [entity type name, column name after renaming, where-clause]
        "entities": [["Order", "Order", ""], ["Supplier Order", "SupplierOrder", ""],
                     ["Item", "Item", ""], ["Invoice", "Invoice", ""], ["Payment", "Payment", ""]],
        "expected_events": 21,
        "expected_entities": {"O1", "O2", "A", "B", "X1", "X2", "X3", "Y1", "Y2", "I1", "I2", "P1"},
        "authors_prepared": ROOT / "external" / "eventgraph_tutorial" / "order_process"
                            / "prepared_logs" / "order_process_event_table_orderhandling_prepared.csv",
    },
    "ocel_scientific_publications": {
        "input": ROOT / "data" / "ocel_scientific_publications" / "ocel_scientific_publications.csv",
        "preprocessor": "scientific_publications",
        "prepared_name": "ocel_scientific_publications_prepared.csv",
        "date_format": "%Y-%m-%dT%H:%M:%S%z",
        "rename": {"event": "Activity", "time": "timestamp"},
        "entities": [["City", "City", ""], ["Conference", "Conference", ""],
                     ["Country", "Country", ""], ["Keyword", "Keyword", ""],
                     ["Paper", "Paper", ""], ["Researcher", "Researcher", ""]],
        "expected_events": None,
        "expected_entities": None,
        "authors_prepared": None,
    },
}