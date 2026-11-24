"""Reading a directory of data files into a Dataset.

Nothing here decides whether the data is correct. It decides only what the data *is*, and
hands every failure to parse along as text for the checks to report. A loader that raises
on a malformed file would make the tool unable to report the one defect it was run to
find.
"""

from __future__ import annotations

import csv
import json
import os

from .model import Dataset, Row, Table
from .schema import Schema, TableSpec


def _load_csv(path: str, spec: TableSpec) -> Table:
    with open(path, encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = tuple(reader.fieldnames or ())
        if not columns:
            raise ValueError("no header row")
        rows: list[Row] = []
        for number, raw in enumerate(reader, start=1):
            # A short row gives DictReader a None value; a long one collects the extras
            # under the None key. Both are shape defects, and both are left visible to
            # the checks rather than smoothed over here.
            values = {k: v for k, v in raw.items() if k is not None}
            rows.append(Row(number=number, values=values))
    return Table(name=spec.name, path=path, columns=columns, rows=tuple(rows))


def _load_json(path: str, spec: TableSpec) -> Table:
    with open(path, encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, list):
        raise ValueError("expected a JSON array of objects")
    rows: list[Row] = []
    seen: list[str] = []
    for number, entry in enumerate(raw, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"entry {number} is not an object")
        rows.append(Row(number=number, values=dict(entry)))
        for key in entry:
            if key not in seen:
                seen.append(key)
    return Table(name=spec.name, path=path, columns=tuple(seen), rows=tuple(rows))


def load_dataset(root: str, schema: Schema) -> Dataset:
    tables: dict[str, Table] = {}
    unreadable: dict[str, str] = {}

    for name, spec in schema.tables.items():
        path = os.path.join(root, spec.file)
        if not os.path.isfile(path):
            continue  # absence is DQ002, decided by a check and not here
        try:
            if spec.file.lower().endswith(".json"):
                tables[name] = _load_json(path, spec)
            else:
                tables[name] = _load_csv(path, spec)
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError, OSError) as err:
            unreadable[name] = str(err)

    return Dataset(root=root, tables=tables, unreadable=unreadable)
