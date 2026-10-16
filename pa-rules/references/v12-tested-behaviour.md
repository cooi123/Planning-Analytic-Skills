# Rule and feeder behaviour tested on v12

Observed on a PA as a Service database, TM1 server **v12.6.3**, on 2026-10-16.
A throwaway cube of two dimensions (three leaves under one consolidation, and a
measures dimension) was built, ruled, loaded and read back, then deleted. The
checks were prompted by the Bedrock/Cubewise white paper on rules (2011, v9/v10
era). Re-test after a server upgrade.

## 1. Division by zero

| Rule | Result at a leaf with a zero denominator |
|---|---|
| `['A'] = N: ['B'] / ['C'];` | `#N/A` |
| `['A'] = N: ['B'] \ ['C'];` | `0` |

The paper's advice holds: use `\` (`RUL-005`). Reading it over REST: the zero from
`\` comes back with `Value` null and `FormattedValue` `0.00`, so a client that
only reads `Value` can't tell a computed zero from an empty cell. Read
`FormattedValue`, or compare against the leaves.

## 2. SKIPCHECK and feeders

Three cases were compared: two measures in a cube whose file starts `SKIPCHECK;` and
has a `FEEDERS;` section, and one measure in a cube whose file has neither. Leaf
values were 50 and 20.

| Measure | File has SKIPCHECK | Feeder | Consolidated value |
|---|---|---|---|
| Fed | yes | yes | **70** (correct) |
| Unfed | yes | none | **blank** (should be 70) |
| Unfed | no SKIPCHECK or FEEDERS | none | **70** (correct) |

So:

- **Underfeeding is silent.** The leaves show correct rule values. The
  consolidation shows blank, with no error. A rule that "works at leaf but the
  total is empty" is an unfed rule first (`FED-001`).
- **`SKIPCHECK` is a performance choice, not a correctness rule.** Without it the
  cube consolidates correctly with no feeders, but evaluates every cell. With it,
  every rule-calculated cell the consolidation depends on must be fed. Say this
  accurately: don't tell a user an unfed rule is "wrong" without `SKIPCHECK` in
  the file.
- Run time and memory were not measured. The performance claim comes from the
  paper, not from this test.

## 3. Conditional feeders fire once

Setup: two rules, `['RevA'] = N: ['Qty']` and `['RevB'] = N: ['Qty'] * 2`, and a
feeder `['Qty'] => DB(..., IF(<flag cell> = 1, 'RevA', 'RevB'))`. The flag
was 1 when the quantity was entered.

| Step | RevB at the consolidation | Right answer |
|---|---|---|
| Flag = 1, quantity entered | 8 (only another leaf) | 8 |
| Flag changed 1 to 0 | 8 | **28** |
| Quantity rewritten | 8 | **30** |

The feeder that was decided at entry time was not re-decided, and the
consolidation stayed under-reported even after the quantity was rewritten. The
paper's warning holds on v12.6.3 with the default configuration (`FED-007`).

Configuration: `ReevaluateConditionalFeeders`, the setting the paper names, is
**not present** in this server's `ActiveConfiguration`. The server does list
`ForceReevaluationOfFeedersForFedCellsOnDataChange` (false), `PersistentFeeders`
(true) and `MTFeeders`. Whether changing the first one alters the result above was
**not tested**. Don't tell a user it fixes this.

Safe patterns: an unconditional feeder (accept some overfeeding), or a condition
that reads something that does not change after load, such as an element
attribute (`DIM-006`).

## 4. Recursive rules fail silently at depth

Setup: a period chain where `Open` = the previous period's `Close` (found through
an attribute), and `Close = Open + Move`.

| Chain depth (periods) | Value at the last period |
|---|---|
| 100, 500, 550, 600 | correct |
| 650, 700, 750, 1000, 2000, 8000 | `#N/A` |

- The failure is **silent**: HTTP 200, no message log entry, and
  `TraceCellCalculation` reports `NaN`. Nothing says "stack".
- The break point is between 600 and 650 for this rule shape. A heavier rule
  will break sooner. Treat roughly 500 as the order of magnitude, not a promise.
- Symptom: the early periods of a chain are right and a later one is `#N/A`.
- Fix is the paper's: break the chain at a cycle boundary (a year-end
  carry-forward written by TI) so recursion stays within one cycle (`RUL-007`).

## 5. Validating a rule file over REST

- Save: `PATCH Cubes('<cube>')` with `{"Rules": "<text>"}`.
- Check: `POST Cubes('<cube>')/tm1.CheckRules`. **`GET` is rejected** ("GET not
  supported on this resource"). A clean file returns `{"value": []}`.
- A problem returns `{"LineNumber": n, "Message": "..."}`.

| Mistake | Message |
|---|---|
| Area names an element that doesn't exist | `Element not found '<elem>'` followed by the statement |
| Statement missing its closing `;` | `Syntax error on or before: (end of line) missing semicolon` |
| Feeder targets an element that doesn't exist | `Element not found '<elem>'` with the feeder's line number |

Whether `PATCH` itself rejects an invalid file was not tested. Always run
`CheckRules` after saving and read its result.

## 6. Not tested

Conditional-feeder behaviour with the `ForceReevaluation...` setting changed;
calculation speed and memory with and without `SKIPCHECK`; string rules and
`FEEDSTRINGS`; `STET`, `ELPAR`, `ELCOMP`; rule worksheets; anything on v11.
