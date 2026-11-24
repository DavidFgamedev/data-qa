# data-qa

[![qa](https://github.com/DavidFgamedev/data-qa/actions/workflows/ci.yml/badge.svg)](https://github.com/DavidFgamedev/data-qa/actions/workflows/ci.yml)

Validation for gameplay data tables: the CSV and JSON files holding weapon stats, enemy
stats, ability definitions and wave definitions. Pure Python, no runtime dependencies.

```bash
python -m data_qa check path/to/data
python -m data_qa check path/to/data --schema my-game.json --format json
python -m data_qa rules
```

Exit `0` clean, `1` findings, `2` the tool could not run. The third code is the one that
matters: a run that could not start must never be mistaken for a clean bill of health,
and the way that breaks is a pipeline reading "could not start" as "nothing found".

## What it checks

<!-- rules:start -->

| id | rule | what it catches |
|---|---|---|
| `DQ001` | **unreadable-file** | A declared table exists but cannot be parsed. |
| `DQ002` | **missing-table** | A table named by the schema has no file. |
| `DQ003` | **missing-column** | A required column is absent from a table. |
| `DQ004` | **unknown-column** | A column is present that the schema does not declare. |
| `DQ005` | **wrong-type** | A value is not the type the column declares. |
| `DQ006` | **out-of-range** | A value is outside the declared bounds, or outside the allowed set. |
| `DQ007` | **duplicate-id** | Two rows in a table share an id. |
| `DQ008` | **missing-id** | A row has a blank or absent id. |
| `DQ009` | **unknown-reference** | A value points at an id that exists in no table. |
| `DQ010` | **curve-decreases** | A stat curve declared non-decreasing goes down between levels. |
| `DQ011` | **cooldown-not-positive** | A value declared positive is zero or negative. |
| `DQ012` | **weights-do-not-sum** | A drop table's weights do not sum to the declared total. |

<!-- rules:end -->

That table is generated from `data_qa/rules.py`, which is the only place a rule is
defined. `tests/test_docs.py` fails if this block and the rule table disagree, because a
rule written down twice is two rules that agree until someone edits one of them.

## The three kinds of defect, and why they need separate checks

**Shape** (DQ001-DQ004) is what a schema validator does: the file parses, the columns are
the declared columns. A renamed column fires DQ003 and DQ004 together, and that pair is
what tells you it was renamed rather than dropped.

**Values** (DQ005-DQ008) is per cell: the type, the bounds, the id. A value that fails its
type check is skipped by the range check rather than reported by both, so one wrong cell
produces one finding. Without that, a single typo in a large table buries the real defects
under its own output.

**Relationships** (DQ009-DQ012) is what a schema validator cannot reach, and it is where
the interesting bugs live. Every value is individually legal. What fails is how they sit
together: a wave naming an enemy that was renamed last week, a power curve whose level 3
is below its level 2 because two cells were transposed, a drop table whose weights sum to
1.2 so the last entry can never roll.

## What it deliberately does not do

**It does not decide whether the numbers are good.** A weapon doing 310 damage on a 2.6
second cooldown passes every rule here. Whether that is balanced is a design judgement
and this tool has no opinion. It checks that the data says what it claims to say.

**It does not fix anything.** No rewriting, no normalising, no "helpfully" coercing a
value and carrying on. The data is read and reported on, never written.

**It does not infer the schema from the data.** An inferred schema passes whatever it was
inferred from, which makes the check a tautology. The schema is declared, and a schema
the tool cannot use is exit 2 rather than a degraded run.

**It does not check the game.** Whether the ability actually applies its effect is a
question for a test that runs the game. This reads tables.

## The schema

`data_qa/schemas/default.json` describes one game's tables and ships as the example. Point
`--schema` at your own. Column types are `string`, `integer`, `number`, `string_list`,
`number_list` and `weight_table`; constraints are `required`, `min`, `max` (inclusive),
`one_of`, `positive`, `non_decreasing`, `references` and `weights_sum_to`.

A `references` entry reads `table.column` and is validated when the schema loads, so a
reference pointing at a column that does not exist is a usage error rather than a check
that silently compares against an empty set and passes everything.

Lists in a CSV cell are pipe-separated, because the comma is the delimiter and a quoted
comma-separated list is what the next tool to open the file will corrupt.

## Structure

Detection is pure functions over a loaded dataset. Printing and exit codes live in the
CLI and nowhere else, which is what lets every test assert on what a check found without
capturing stdout or spawning a process.

```
data_qa/rules.py        the rule table: the single definition of every rule
data_qa/schema.py       reading the schema that describes your tables
data_qa/loader.py       CSV and JSON into a common Dataset
data_qa/checks/         one function per rule, registry asserted against rules.py
data_qa/report.py       rendering, text and json, from the same findings
data_qa/cli.py          arguments and the exit-code contract
```

The check registry is asserted against the rule table **at import time**, not in a test.
A rule with no check is a broken build rather than a check that silently never runs; a
test can be skipped, an import cannot.

## Tests

```bash
pip install -e ".[dev]"
pytest
pytest --cov=data_qa --cov-report=term-missing
```

Three kinds, for three different jobs:

- **Named unit tests** per check, against tables built in memory, so a failure points at
  the check rather than at a fixture, the loader or the CLI.
- **Property-based tests** with Hypothesis for the checks that are predicates over
  numbers: range, positivity, monotonicity, summation and the CSV coercion round trip.
  The honest test of "fires exactly when the value is out of bounds" is the predicate,
  not six values somebody thought of.
- **Fixture tests.** `tests/fixtures/clean` passes every rule. `tests/fixtures/broken`
  holds one directory per rule, each differing from clean in exactly one way, and each is
  asserted to fire **its own rule and no other**. A fixture that quietly stops being
  broken is the quietest failure this tool can have, so the fixtures are themselves under
  test.

## CI

`pytest` on Python 3.10, 3.11, 3.12 and 3.13, a lint job, and a self-check job that runs
the CLI against every broken fixture and asserts it exits non-zero, then against the clean
set and asserts zero. A checker that cannot fail is not a checker.

## License

MIT.
