"""Generating the README's rule list from the rule table.

`tests/test_docs.py` asserts the README contains exactly what this produces. That test is
the enforcement: without it the generator is a suggestion and the README drifts, which is
the specific failure this whole arrangement exists to prevent.
"""

from __future__ import annotations

from .rules import RULES

START = "<!-- rules:start -->"
END = "<!-- rules:end -->"


def render_rules_markdown() -> str:
    lines = ["| id | rule | what it catches |", "|---|---|---|"]
    for rule in RULES:
        lines.append(f"| `{rule.id}` | **{rule.name}** | {rule.summary} |")
    return "\n".join(lines)


def splice(readme: str) -> str:
    """Replace the generated block in a README, leaving everything else untouched."""
    if START not in readme or END not in readme:
        raise ValueError(f"README has no {START} / {END} block")
    head = readme.split(START)[0]
    tail = readme.split(END)[1]
    return f"{head}{START}\n\n{render_rules_markdown()}\n\n{END}{tail}"
