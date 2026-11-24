"""DQ009 unknown-reference.

Three reference shapes, one check. A scalar column holds one id, a list column holds
several, and a weight table holds one per entry. They are separate code paths in most
tools and that is how one of them ends up unchecked, so the shapes are resolved to a list
of ids first and compared against the target once.
"""

from __future__ import annotations

from ..coerce import coerce
from ..model import Dataset, Finding
from ..schema import Schema


def _target_ids(dataset: Dataset, table_name: str, column_name: str) -> set[str]:
    table = dataset.table(table_name)
    if table is None:
        return set()
    return {
        str(row.values.get(column_name)).strip()
        for row in table.rows
        if row.values.get(column_name) is not None and str(row.values.get(column_name)).strip()
    }


def _referenced_ids(value: object, declared_type: str) -> list[str]:
    coerced = coerce(value, declared_type)
    if coerced is None:
        return []  # DQ005 owns a value that is not even the right shape
    if declared_type == "weight_table":
        return [item for item, _weight in coerced]
    if declared_type in ("string_list", "number_list"):
        return [str(item) for item in coerced]
    return [str(coerced)]


def check_unknown_reference(dataset: Dataset, schema: Schema) -> list[Finding]:
    findings = []
    for name, spec in schema.tables.items():
        table = dataset.table(name)
        if table is None:
            continue
        for column in spec.columns.values():
            if column.references is None or column.name not in table.columns:
                continue
            target_table, target_column = column.references.split(".")
            # A target table that failed to load would give an empty id set, which would
            # report every reference as unknown. That is a cascade from one defect, so
            # the check stands down and lets DQ001 or DQ002 report the real cause.
            if dataset.table(target_table) is None:
                continue
            known = _target_ids(dataset, target_table, target_column)
            for row in table.rows:
                raw = row.values.get(column.name)
                if raw is None or (isinstance(raw, str) and not raw.strip()):
                    continue
                for referenced in _referenced_ids(raw, column.type):
                    if referenced.strip() in known:
                        continue
                    findings.append(
                        Finding(
                            rule_id="DQ009",
                            table=name,
                            where=f"row {row.number}, column {column.name}",
                            message=(
                                f"{referenced!r} is not an id in {target_table}.{target_column}"
                            ),
                        )
                    )
    return findings
