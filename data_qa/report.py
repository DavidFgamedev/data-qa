"""Rendering findings. No detection here, and no exit codes either.

Two formats because they have two readers: `text` is for a person looking at a terminal,
`json` is for whatever consumes the run in a pipeline. Both are built from the same
findings, so they cannot disagree about what was found.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from .model import Finding
from .rules import rule as rule_for


def group_by_rule(findings: Sequence[Finding]) -> dict[str, list[Finding]]:
    grouped: dict[str, list[Finding]] = {}
    for finding in findings:
        grouped.setdefault(finding.rule_id, []).append(finding)
    return grouped


def render_text(findings: Sequence[Finding], root: str, table_count: int) -> str:
    lines = [f"data-qa: {table_count} tables under {root}", ""]
    if not findings:
        lines.append("No findings. Every declared table loaded and every rule held.")
        return "\n".join(lines)

    grouped = group_by_rule(findings)
    for rule_id in sorted(grouped):
        current = rule_for(rule_id)
        lines.append(f"{rule_id}  {current.name}  ({len(grouped[rule_id])})")
        lines.append(f"    {current.summary}")
        for finding in grouped[rule_id]:
            lines.append(f"    {finding.table}: {finding.where}")
            lines.append(f"        {finding.message}")
        lines.append("")

    total = len(findings)
    noun = "finding" if total == 1 else "findings"
    lines.append(f"{total} {noun} across {len(grouped)} of 12 rules.")
    return "\n".join(lines)


def render_json(findings: Sequence[Finding], root: str, table_count: int) -> str:
    payload = {
        "root": root,
        "tables": table_count,
        "findings": [
            {
                "rule": finding.rule_id,
                "name": rule_for(finding.rule_id).name,
                "table": finding.table,
                "where": finding.where,
                "message": finding.message,
            }
            for finding in findings
        ],
    }
    return json.dumps(payload, indent=2)
