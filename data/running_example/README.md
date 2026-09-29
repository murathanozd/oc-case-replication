# Running example

Copied from `external/eventgraph_tutorial/order_process/input_logs/` (LGPL-2.1, commit `31d19b8`).

- `order_process_event_table_orderhandling.csv`: 21 events, corresponds to Table 1 of the paper.
  Object types used in the paper: Order, Supplier Order, Item, Invoice, Payment.
  The columns Actor, Order Details and Tray are not treated as objects in the paper.
- `order_process_event_table_full.csv`: 34 events, includes the warehouse events (Scan, Store Item,
  Retrieve Item). Not used in the paper; kept for comparison.
