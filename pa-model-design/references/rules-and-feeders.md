# Rules and feeders

Version-neutral. Verify syntax against
`{{config.platform.docs_base}}/{{config.platform.pa_version}}`.

Design rules and feeders **together**. A rule without its feeder is an incomplete
design, not a design awaiting a later step.

## 1. Rule statement anatomy

```
[Area] = Formula;          applies to both leaf and consolidated cells
[Area] = N: Formula;       leaf cells only
[Area] = C: Formula;       consolidated cells only
```

Qualify with the dimension name whenever an element name could appear in more than
one dimension:

```
[{Measure}:'Revenue'] = N: [{Measure}:'Units'] * [{Measure}:'Price'];
```

### Scope discipline

Default to `N:`. An unqualified rule also overrides consolidation, which is rarely
what is intended and is a common cause of "the total doesn't match the parts".

Use `C:` only when the consolidated value genuinely is not the sum of its children,
such as ratios, averages, opening and closing balances, or period-end rates. When
you write a `C:` rule, record *why* the natural consolidation is wrong. That justification is what a
reviewer needs a year later.

### Precedence

Rules evaluate top to bottom and **the first matching statement wins**. Later
statements for the same area are ignored.

Order from most specific to most general. A broad rule placed above a narrow one
silently disables it. There is no warning, and the symptom appears far from the cause.

- `STET` bypasses the rule for this area and falls back to normal consolidation.
- `CONTINUE` evaluates the next matching statement instead of stopping. Use it
  sparingly, since it makes tracing much harder.

## 2. SKIPCHECK, FEEDSTRINGS, FEEDERS

Required structure when `{{config.rules.require_skipcheck}}` is true:

```
FEEDSTRINGS;      <- first line, only if any rule returns a string
SKIPCHECK;        <- before the rules
... rule statements ...
FEEDERS;          <- after the rules
... feeder statements ...
```

**SKIPCHECK** turns on the sparse consolidation algorithm: TM1 skips cells it believes
are empty. That is the performance win, and it is also the trap. A rule-derived cell
that is not fed is *believed empty* and will not appear in a consolidation. The
classic symptom is a total that reads zero while its children clearly hold values.

**FEEDSTRINGS** must be the literal first line when any rule produces a string. Omit it
and string-derived cells vanish under zero suppression and behave unreliably in
cross-cube references. Governed by `{{config.rules.feedstrings_when_string_rules}}`.

**A cube with SKIPCHECK needs FEEDERS.** Removing SKIPCHECK to "fix" unfed cells trades
a correctness bug for a performance one, and on a large cube that is usually the
worse trade.

## 3. Feeder design

A feeder marks a target cell as potentially non-empty. It does not calculate anything.

```
[{Measure}:'Rate'] => [{Measure}:'Amount'];
```

Rule of thumb when `{{config.rules.require_feeder_for_every_leaf_rule}}` is true:
**every `N:` rule needs a feeder from a source cell that is populated whenever the
rule produces a value.**

### Feed from the sparsest source

Feed from the operand most likely to be empty. If `Amount = Rate * Quantity`, and Rate
is populated for every valid combination while Quantity is entered for only a few, feed
from **Quantity**. Feeding from Rate marks every rate-bearing cell as potentially
populated, most of which will never hold a value.

This single choice is the difference between a lean model and one that doubles in
memory.

### Overfeeding

Overfeeding is feeding more cells than can ever hold a value. It does not produce wrong
numbers, which is what makes it dangerous. It produces a model that is quietly too
big and too slow, and the cost is permanent for the life of the model.

Feed exactly the cells required: no more, no fewer.

Watch for:

| Smell | Fix |
|---|---|
| Feeder source is a consolidated cell | Feed from leaf level |
| Feeder targets a whole dimension with no qualifier | Qualify the target |
| Feeder ignores a condition the rule enforces | Make it a conditional feeder |
| Cross-cube feeder with an unqualified target | Qualify every dimension on the target side |

Conditional feeders are the normal remedy. Mirror the rule's own condition so the
feeder fires exactly when the rule produces a value.

Check designed fan-out against `{{config.review.thresholds.max_feeder_fanout}}` and
flag anything above it for justification.

### Cross-cube feeders

A rule using `DB()` to read another cube needs a feeder **in the source cube**,
pointing at the target cube. This is the most commonly missed feeder, because the rule
and its feeder live in different files.

Record every cross-cube feeder explicitly in the design spec, naming both cubes.

## 4. What not to solve with rules

| Situation | Better tool |
|---|---|
| Value is static and set once | Load it with TI |
| Calculation is expensive and read constantly | Precompute into a reporting cube via TI |
| Logic varies by member | Attribute plus one generic rule, not one rule per member |
| Needed only at month end | TI process on a chore |

Every rule is evaluated on read, forever. A TI process runs once. When a value does not
change between loads, a rule is the more expensive choice.

## 5. Design output

For every rule, the spec records: cube, target area, scope (`N:`/`C:`/both), formula,
precedence position, and, without exception, its feeder or a note saying none is
needed and why.
