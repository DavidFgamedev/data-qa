"""The rule table. One entry per rule, and the only place a rule is defined.

Three things are generated from this table and none of them is maintained by hand:

  * the check registry, which must cover every id here and invent none (`checks/`)
  * the rule list in the README (`docs.py`, asserted by `tests/test_docs.py`)
  * the `data-qa rules` output

The reason is the ordinary one: a rule documented in two places is two rules that agree
until someone edits one of them.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    summary: str
    detail: str


RULES: tuple[Rule, ...] = (
    Rule(
        id="DQ001",
        name="unreadable-file",
        summary="A declared table exists but cannot be parsed.",
        detail=(
            "Malformed CSV or JSON. Reported as a finding rather than a crash, because a "
            "half-saved export is a defect in the data and the run should name it and "
            "carry on checking the other tables."
        ),
    ),
    Rule(
        id="DQ002",
        name="missing-table",
        summary="A table named by the schema has no file.",
        detail=(
            "Separate from DQ001 on purpose: a file that is absent and a file that is "
            "corrupt are different conversations with different people."
        ),
    ),
    Rule(
        id="DQ003",
        name="missing-column",
        summary="A required column is absent from a table.",
        detail=(
            "A renamed column fires this and DQ004 together, which is the pair that "
            "tells you it was renamed rather than dropped."
        ),
    ),
    Rule(
        id="DQ004",
        name="unknown-column",
        summary="A column is present that the schema does not declare.",
        detail=(
            "Catches the typo that silently does nothing: a column called `dmg` is read "
            "by no code, so without this check the table looks fine and the value is "
            "ignored at runtime."
        ),
    ),
    Rule(
        id="DQ005",
        name="wrong-type",
        summary="A value is not the type the column declares.",
        detail=(
            "CSV has no types, so every value arrives as text and the check is a "
            "coercion. JSON has types and they are checked as given. A value that fails "
            "here is skipped by the range and balance checks rather than reported twice."
        ),
    ),
    Rule(
        id="DQ006",
        name="out-of-range",
        summary="A value is outside the declared bounds, or outside the allowed set.",
        detail=(
            "Covers numeric `min`/`max` and string `one_of`. Bounds are inclusive, which "
            "is stated here because off-by-one at the boundary is the usual argument."
        ),
    ),
    Rule(
        id="DQ007",
        name="duplicate-id",
        summary="Two rows in a table share an id.",
        detail=(
            "Whichever row loads last wins at runtime, so the row the designer edited is "
            "often not the row the game reads."
        ),
    ),
    Rule(
        id="DQ008",
        name="missing-id",
        summary="A row has a blank or absent id.",
        detail="Nothing can reference it and nothing can override it.",
    ),
    Rule(
        id="DQ009",
        name="unknown-reference",
        summary="A value points at an id that exists in no table.",
        detail=(
            "Checked across all three reference shapes: a scalar column, a list column, "
            "and the item field of a weight table. A wave naming an enemy that was "
            "renamed is the case this exists for."
        ),
    ),
    Rule(
        id="DQ010",
        name="curve-decreases",
        summary="A stat curve declared non-decreasing goes down between levels.",
        detail=(
            "Equal consecutive values are allowed: a curve that flattens for a level is "
            "a design choice, a curve that reverses is a transposed pair of cells."
        ),
    ),
    Rule(
        id="DQ011",
        name="cooldown-not-positive",
        summary="A value declared positive is zero or negative.",
        detail=(
            "A zero cooldown is not a fast ability, it is an ability that fires every "
            "frame. This is why zero fails rather than passing as in-range."
        ),
    ),
    Rule(
        id="DQ012",
        name="weights-do-not-sum",
        summary="A drop table's weights do not sum to the declared total.",
        detail=(
            "Compared within a tolerance, because the values are floating point and a "
            "table of thirds cannot sum to exactly 1.0 in binary."
        ),
    ),
)

BY_ID: dict[str, Rule] = {rule.id: rule for rule in RULES}


def rule(rule_id: str) -> Rule:
    try:
        return BY_ID[rule_id]
    except KeyError:
        raise KeyError(f"no such rule: {rule_id}") from None
