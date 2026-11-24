"""DQ007 duplicate-id, DQ008 missing-id.

Ids are the join key for every cross-table reference, so these run before the reference
check and the reference check trusts their result.
"""

from __future__ import annotations

from ..model import Dataset, Finding
from ..schema import Schema


def check_duplicate_id(dataset: Dataset, schema: Schema) -> list[Finding]:
    findings = []
    for name, spec in schema.tables.items():
        table = dataset.table(name)
        if table is None or spec.id_column not in table.columns:
            continue
        first_seen: dict[str, int] = {}
        for row in table.rows:
            raw = row.values.get(spec.id_column)
            if raw is None or not str(raw).strip():
                continue  # DQ008 owns the blank ones
            identifier = str(raw).strip()
            if identifier in first_seen:
                findings.append(
                    Finding(
                        rule_id="DQ007",
                        table=name,
                        where=f"row {row.number}, column {spec.id_column}",
                        message=(f"{identifier!r} is already used by row {first_seen[identifier]}"),
                    )
                )
            else:
                first_seen[identifier] = row.number
    return findings


def check_missing_id(dataset: Dataset, schema: Schema) -> list[Finding]:
    findings = []
    for name, spec in schema.tables.items():
        table = dataset.table(name)
        if table is None or spec.id_column not in table.columns:
            continue
        for row in table.rows:
            raw = row.values.get(spec.id_column)
            if raw is None or not str(raw).strip():
                findings.append(
                    Finding(
                        rule_id="DQ008",
                        table=name,
                        where=f"row {row.number}, column {spec.id_column}",
                        message="blank id: nothing can reference this row",
                    )
                )
    return findings
