"""The check registry: one function per rule id, and nothing else.

The registry is asserted against `rules.RULES` at import time. A rule with no check, or
a check for a rule that does not exist, is a broken build rather than a check that
silently never runs. That failure mode is the reason this assertion is here rather than
only in a test: a test can be skipped, an import cannot.
"""

from __future__ import annotations

from collections.abc import Callable

from ..model import Dataset, Finding
from ..rules import RULES
from ..schema import Schema
from .balance import (
    check_cooldown_not_positive,
    check_curve_decreases,
    check_weights_do_not_sum,
)
from .identifiers import check_duplicate_id, check_missing_id
from .references import check_unknown_reference
from .structure import (
    check_missing_column,
    check_missing_table,
    check_unknown_column,
    check_unreadable_file,
)
from .values import check_out_of_range, check_wrong_type

Check = Callable[[Dataset, Schema], list[Finding]]

CHECKS: dict[str, Check] = {
    "DQ001": check_unreadable_file,
    "DQ002": check_missing_table,
    "DQ003": check_missing_column,
    "DQ004": check_unknown_column,
    "DQ005": check_wrong_type,
    "DQ006": check_out_of_range,
    "DQ007": check_duplicate_id,
    "DQ008": check_missing_id,
    "DQ009": check_unknown_reference,
    "DQ010": check_curve_decreases,
    "DQ011": check_cooldown_not_positive,
    "DQ012": check_weights_do_not_sum,
}

_declared = {rule.id for rule in RULES}
_implemented = set(CHECKS)
if _declared != _implemented:
    raise RuntimeError(
        "the rule table and the check registry disagree: "
        f"declared with no check {sorted(_declared - _implemented)}, "
        f"implemented with no rule {sorted(_implemented - _declared)}"
    )


def run_all(dataset: Dataset, schema: Schema) -> tuple[Finding, ...]:
    """Every check, in rule order. Order of findings is stable so output can be diffed."""
    findings: list[Finding] = []
    for rule in RULES:
        findings.extend(CHECKS[rule.id](dataset, schema))
    return tuple(findings)
