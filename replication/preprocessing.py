"""Convert the scientific-publications OCEL export into an event table for R1."""

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "ocel_scientific_publications" / "ocel_scientific_publications.csv"
DST = ROOT / "data" / "ocel_scientific_publications" / "ocel_scientific_publications_event_table.csv"
MAP = ROOT / "data" / "ocel_scientific_publications" / "scientific_event_id_map.csv"
TYPES = ["City", "Conference", "Country", "Keyword", "Paper", "Researcher"]
SPLIT = re.compile(r"(?<!\\)/")          # split on "/" but not on "\/"


def clean_objects(cell):
    if pd.isna(cell) or not str(cell).strip():
        return ""
    out = []
    for part in SPLIT.split(str(cell)):
        name = part.rsplit("#", 1)[0]                      # drop the "#type" suffix
        name = (name.replace("\\/", "/").replace("\\", " ")  # no backslashes: LOAD CSV escapes them
                    .replace(",", " ").replace('"', "").strip())
        if name and name not in out:
            out.append(name)
    return ",".join(out)


def prepare_event_table(source=SRC):
    """Return timestamped events, their source-ID map, and counts of non-event rows."""
    df = pd.read_csv(source, dtype=str, encoding="utf-8")
    required = {"id", "activity", "timestamp", *(f"ot:{t}" for t in TYPES)}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Scientific-publications CSV is missing required columns: {sorted(missing)}")

    has_identity = (
        df["id"].fillna("").str.strip().ne("")
        & df["activity"].fillna("").str.strip().ne("")
    )
    is_object_relation = has_identity & df["activity"].str.strip().str.casefold().eq("o2o")
    events = df.loc[has_identity & ~is_object_relation].copy()
    events["timestamp"] = events["timestamp"].fillna("").str.strip()
    missing_timestamp = events["timestamp"].eq("")
    if missing_timestamp.any():
        activities = sorted(events.loc[missing_timestamp, "activity"].unique())
        raise ValueError(
            f"{int(missing_timestamp.sum())} event rows have no timestamp "
            f"(activities: {activities}); refusing to invent event times."
        )

    events["_t"] = pd.to_datetime(
        events["timestamp"], format="%Y-%m-%dT%H:%M:%S%z", utc=True
    )
    events = events.sort_values("_t", kind="stable").reset_index(drop=True)

    out = pd.DataFrame({
        "EventID": [f"e{i + 1}" for i in range(len(events))],
        "event": events["activity"].str.replace(",", " ", regex=False),
        "time": events["_t"].dt.strftime("%Y-%m-%dT%H:%M:%S%z"),
    })
    for t in TYPES:
        out[t] = events[f"ot:{t}"].map(clean_objects)

    event_id_map = pd.DataFrame({"EventID": out["EventID"], "id": events["id"].values})
    counts = {
        "source_rows": len(df),
        "non_event_rows": int((~has_identity).sum()),
        "object_relation_rows": int(is_object_relation.sum()),
        "events": len(out),
    }
    return out, event_id_map, counts


def main():
    out, event_id_map, counts = prepare_event_table()
    event_table = out.copy()
    event_table["time"] = pd.to_datetime(
        event_table["time"], format="%Y-%m-%dT%H:%M:%S%z", utc=True
    ).dt.strftime("%d.%m.%Y %H:%M:%S")
    event_table.to_csv(DST, index=False, encoding="utf-8")
    event_id_map.to_csv(MAP, index=False, encoding="utf-8")

    print(f"{counts['events']} events -> {DST}")
    print(f"Skipped {counts['non_event_rows']} object-only rows and "
          f"{counts['object_relation_rows']} object-relation rows.")
    print("distinct objects per type:",
          {t: len({o for c in out[t] for o in c.split(",") if o}) for t in TYPES})
    print("events sharing a timestamp with another event:",
          int(out["time"].duplicated(keep=False).sum()))


if __name__ == "__main__":
    main()