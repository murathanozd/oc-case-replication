from datetime import datetime, timedelta
from pathlib import Path

import pytest

from r2_python.behaviour import directly_follows
from r2_python.oced import OCEDSet, load_csv, make_relation_consistent

DATA = Path(__file__).resolve().parents[2] / "data" / "running_example" / "order_process_event_table_orderhandling.csv"
T0 = datetime(2021, 1, 1)


def mini(events: dict[str, tuple[str, int]], corr: dict[str, list[str]], otype: dict[str, str]) -> OCEDSet:
    """Hand-made OCED-set: events {id: (activity, minute)}, corr {event: [objects]}, otype {object: type}."""
    types = {e: a for e, (a, _) in events.items()} | otype
    attrs = {e: {"time": T0 + timedelta(minutes=m)} for e, (_, m) in events.items()} | {o: {} for o in otype}
    c = frozenset((e, o) for e, os in corr.items() for o in os)
    return make_relation_consistent(OCEDSet(frozenset(otype), frozenset(events), types, c, frozenset(), attrs))


@pytest.fixture(scope="session")
def running():
    return load_csv(DATA)


@pytest.fixture(scope="session")
def running_df(running):
    return directly_follows(running)
