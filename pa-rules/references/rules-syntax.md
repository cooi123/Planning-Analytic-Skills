# TM1 rules syntax

A working reference for writing rule and feeder statements. Element, dimension and
cube names are illustrative. Behaviour described here follows IBM's TM1 Rules guide
(see Sources). Check function availability for your release against
`{{config.platform.docs_base}}/{{config.platform.pa_version}}`.

## File structure

```
FEEDSTRINGS;          # first line, only if any rule returns a string
SKIPCHECK;            # immediately before the calculation statements
# calculation statements
FEEDERS;              # everything after this line is a feeder
# feeder statements
```

- Every statement ends with `;`. A missing semicolon is the most common syntax
  error. One statement can span several lines.
- Without `SKIPCHECK`, feeder statements are ignored and every consolidation scans
  every cell. That's correct, but slow on any sparse cube.
- `#` starts a comment. A comment line is limited to **255 bytes**: split longer
  comments into several `#` lines.
- `#Region Name` … `#EndRegion` marks a collapsible block in the editor.
- Rules syntax is **not case-sensitive**.
- One rule file per cube, stored on the server as `<cube>.rux`.

## Calculation statement

`[area] = qualifier: formula;`

```
[area] = formula;                     # all cells in the area
[area] = N: formula;                  # leaf numeric cells only
[area] = C: formula;                  # consolidated cells only
[area] = S: formula;                  # string cells only
[area] = N: formula1; C: formula2;    # different formula per level
```

- A cell is **N** if every coordinate is a leaf. It's **C** if any coordinate is a
  consolidation. It's **S** if its last coordinate is a string element. A rule that
  produces text needs `S:`, or no qualifier. `N:` never reaches a string cell.
- The qualifier goes **right before the formula**. Putting it at the start of the
  statement is a syntax error.

### Area forms

| Form | Matches |
|---|---|
| `[]` | Every cell in the cube |
| `['Revenue']` | Any cell where any dimension is at `Revenue` |
| `['Measure':'Revenue']` | `Revenue` in dimension `Measure`. Use whenever a name could exist in two dimensions |
| `['Budget', 'Revenue']` | Cells at both `Budget` and `Revenue` |
| `[{'Jan', 'Feb', 'Mar'}, 'Revenue']` | `Revenue` in any of the listed periods |
| `['}Groups':'ADMIN']` | The dimension-qualified form also handles dimension names with special characters |

Object names containing `@` must be quoted (`'products@location'`). Avoid `!` in
object names that rules use: it clashes with `!Dim`.

### Precedence

TM1 calculates each cell once, using **the first statement whose area matches**.
Order statements from most to least specific.

- `STET` makes a matching cell behave as if no rule applied: input is allowed, and
  it consolidates normally. Use a separate statement above the general one, or
  `IF(!Region @= 'France', STET, …)` inside it.
- `CONTINUE` hands the cell to the next statement with the same area:
  `['Jan'] = IF(!Region @= 'Argentina', 10, CONTINUE); ['Jan'] = 20;`.
  Use it sparingly.
- A rule may refer to cells calculated by other rules (stacking). A loop fails with
  `Error Evaluating Rule: Possible Circular Reference`. For example, Sales from
  Price × Units together with Price from Sales ÷ Units.

### Rules and consolidations

- Rules take precedence over dimension consolidations. When a rule reads a
  consolidated cell, TM1 consolidates first. When a consolidation includes
  rule-calculated cells, TM1 calculates them first.
- Define totals in the dimension, not with rules. Dimension consolidation is much
  faster.
- **Don't override a consolidated cell that is a component of another
  consolidation.** TM1 picks the consolidation path itself, so a grand total can
  differ between requests. If you must, `['Total'] = ConsolidateChildren('Month');`
  pins the path, but views still look inconsistent.

## Formula

### Arithmetic

| Op | Meaning |
|---|---|
| `+ - * ^` | Add, subtract, multiply, power |
| `/` | Divide. **Division by zero returns an undefined value** (shows as N/A) |
| `\` | Divide. **Division by zero returns 0.** The safe choice whenever the denominator can be empty |

**Evaluation order is `^`, then `*`, then `/`, then `+`, then `-`.** Multiplication
binds before division, so `['Sales'] \ ['Units'] * 1000` means `Sales \ (Units *
1000)`. Use parentheses whenever you mix them.

Numeric constants are up to 20 characters, and scientific notation is allowed.

### Comparison

| Numbers | Strings | Meaning |
|---|---|---|
| `=` | `@=` | Equal |
| `<>` | `@<>` | Not equal |
| `>` `<` | `@>` `@<` | Greater, less |
| `>=` `<=` | `@>=` `@<=` | Greater or equal, less or equal |

**Floating point:** `.35` is stored as `.34999999999999998`. Don't test a sum of
fractions with `= 1`. Hold percentages as whole numbers, or compare within a
tolerance.

### Logical and string

| Op | Meaning |
|---|---|
| `&` | AND |
| `%` | OR |
| `~` | NOT, e.g. `~(x > 5)` is the same as `x <= 5` |
| `\|` | String concatenation, **not** OR. Results over 254 bytes are an error |

### IF

`IF(test, value1, value2)` can be nested. **Both values must be the same type**:
both numeric or both strings.

## Referencing data

| Construct | Meaning |
|---|---|
| `['Units']` | The value of `Units` at the current cell's other coordinates, in this cube |
| `!Period` | The name of the current cell's element in dimension `Period` |
| `DB('Cube', a1, a2, …)` | A value from any cube. One argument per dimension **of that cube, in its order** |
| `ATTRS('Dim', elem, 'Attr')` / `ATTRN(…)` | String or numeric attribute of an element |

```
['Revenue Reporting'] = N:
    ['Revenue Local'] * DB('Exchange Rates', !Version, !Period,
                           ATTRS('Organization', !Organization, 'Currency'), 'Rate');
```

- **Each `DB()` argument** is a quoted element, `!Dim`, or any expression that
  returns a valid element of that position's dimension. That includes a nested
  `DB()`: `DB('CurrencyExchangeRate', DB('Currency', !market, 'MarketCurrency'), !date)`.
- **`!Dim` must be a dimension of the cube the rule is in.** Using `!Date` in a
  cube without Date fails with `Syntax error on or before: … invalid string
  expression`.
- **Dimensions can differ when element names match.** `DB()` only checks that the
  argument is a valid element of the target position. So a monthly Plan cube can
  read a daily Production cube's `January` consolidation with `!Month`, as long as
  Production's Date dimension has an element called `January`.
- **To read a string cell, use `DB()`**, even from the same cube. `['Status']`
  reads numbers only.
- **Numeric attributes can't be calculated by rules.** Calculate a text attribute
  and convert it with `NUMBR`.

## Time series

Rules have no lead or lag functions. Build them from element positions:

```
# previous month
DB('Plan', !Product, DIMNM('Month', DIMIX('Month', !Month) - 1), 'Units')

# actuals before the current month, projection from it onwards
['Units'] = IF(DIMIX('Month', !Month) < DIMIX('Month', DB('Control', 'Value', 'Current Month')),
               DB('Actuals', !Product, !Month, 'Units'),
               DB('Plan', !Product, DIMNM('Month', DIMIX('Month', !Month) - 1), 'Units') * ['Growth %']);
```

- **Guard the first period:** `IF(DIMIX('Month', !Month) = 1, 0, …)`.
- **Hold "current month" in a small control cube** that users can set. Don't use
  `TIMVL(NOW, 'M')`: it changes on its own, and you can't roll back to review an
  earlier month.
- **`DIMIX` order is dimension order.** If consolidations sit after the leaves
  (Dec, then Q1…Q4, then Total Year), index arithmetic and `DNEXT` walk into them.

## Feeder statements

```
FEEDERS;
['Units'] => ['Revenue'];                                        # same cube
['Units'] => DB('Margin', !Version, !Period, !Product, 'Units');  # into another cube
['Purchase Cost'] => ['Avg Price'], ['Cost Used'];               # one source, several targets
```

- The left side is the **source** area. The right side is the target.
- **Feeding starts only from leaf cells.** A consolidation on the left side means
  "any leaf under it". A consolidation on the **right** side feeds every leaf
  beneath it, which is the usual cause of overfeeding.
- **Feeders take no `N:`/`C:` qualifier,** so some overfeeding is often
  unavoidable.
- A feeder only marks the target as possibly non-empty. It calculates nothing. The
  source must be **non-zero** for the feeder to fire.
- **Underfeeding gives wrong totals and must be avoided. Overfeeding gives right
  numbers, just slower.** When unsure, overfeed.
- **Where feeders live.** Within a cube, in that cube's rule. Across cubes, in the
  **source** cube's rule, pointing at the target with `DB()`. When a formula
  multiplies values from two cubes, the feeder can go in either. Put it in the
  **sparser** one.
- **When the rule is non-zero only if both operands are,** feed from one operand
  only, the sparser one. IBM's example is `Used = MIN(Available, Required)`, fed
  by `['Available'] => ['Used'];`.
- Feeders fire when a source cell gets a value (typed, loaded by TI), and when
  rules are saved or the server loads them.
- A rule-calculated source only feeds onward if it is itself fed (feeder chains).
- **Feeders must give the same result whatever order cells change in.** On
  startup, feeders are rebuilt in storage order, not in the order users changed
  cells.

### Keeping a feeder off consolidations

Next-element functions walk into consolidations. Fall back to a leaf when they do:

```
['Remaining'] => DB('Inventory', !FishType,
    IF(DTYPE('Date', DNEXT('Date', !Date)) @= 'N', DNEXT('Date', !Date), 'Dec-31'),
    'Quantity in Stock - Kgs');
```

### Conditional feeder

Put an `IF` in the cube-name argument of `DB()`. An empty cube name isn't a valid
target, so nothing is fed when the condition is false.

```
['Units'] => DB(IF(['Active Flag'] = 1, 'Revenue', ''),
                !Version, !Period, !Product, 'Revenue');
```

- Mirror the rule's own condition.
- **Conditional feeders aren't supported with multi-threaded feeders** (`MTFeeders`
  in `tm1s.cfg`). On servers that use them, disable multi-threaded loading for
  that cube, or avoid conditional feeders there.
- A condition is evaluated when the feeder fires. If the condition's data changes
  later, reprocess feeders (`CubeProcessFeeders`).

### Feeders for string rules

`FEEDSTRINGS;` as the first line lets string cells be fed. Without it, rule-derived
strings vanish under zero suppression and can't be referenced reliably by other
rules. String feeders go after `FEEDERS;` like any other.

## Performance and diagnostics

- **Caching.** Rule-calculated values aren't stored on disk. Each is calculated on
  first request, then cached in memory until something it depends on changes.
- **Rule statistics.** Set `RULE_STATS` to `YES` for a cube in the `}CubeProperties`
  control cube. It takes effect within about 60 seconds, with no restart. Then read
  `}StatsByRule` for run count and min/max/total time per rule line. It costs a
  little performance, so turn it off after tuning. The data clears on server
  restart.
- **Rules tracer.** Trace Calculation on any calculated cell. Trace Feeders on leaf
  cells. **Check Feeders on consolidated cells only**: an empty result means
  correctly fed. In PAW, right-click a consolidated cell in an exploration and
  choose **Check feeders**.

## Often forgotten

| Concept | Remember |
|---|---|
| Two division operators | `/` gives an undefined value on division by zero. `\` gives 0 |
| String comparison | Prefix the comparison with `@`: `IF(['Status'] @= 'Approved', …)` |
| Negation | `~( … )` inverts any condition |
| OR is `%` | `\|` concatenates strings, so `a \| b` is not a logical OR |
| Multiplication before division | `a \ b * c` is `a \ (b * c)`. Use parentheses |
| String cells need `S:` | `N:` never applies to a string cell |
| Read strings with `DB()` | Even in the same cube |
| First match wins | A broad statement above a narrow one silently disables it |
| No `N:` overrides totals | An unqualified rule also replaces the consolidated value |
| `DB()` arity | One argument per dimension of the **target** cube, in that cube's order |
| `DNEXT` walks into totals | Guard it with `DTYPE`, or `DIMIX` against the last leaf |
| Conditional feeders and `MTFeeders` | Not supported together |
| Saving replaces the file | Any save, whether workbench, REST or `RuleLoadFromFile`, overwrites the whole rule file |
| Rule cells are read-only | Add `STET` above, or narrow the area, where input must stay possible |

The first three are summarised from Lee Lazarow,
[Rule Concepts that are often Forgotten](https://revelwood.com/ibm-planning-analytics-tips-tricks-rule-concepts-that-are-often-forgotten/)
(Revelwood, 2019). The rest come from IBM's TM1 Rules guide.

## Sources

- IBM, [TM1 Rules guide](https://www.ibm.com/docs/en/planning-analytics/2.0.0?topic=resources-tm1-rules)
  ([PDF](https://www.ibm.com/docs/en/SSD29G_2.0.0/com.ibm.swg.ba.cognos.tm1_rul.2.0.0.doc/tm1_rul.pdf)):
  Introduction to rules (components, precedence, consolidations, stacking,
  floating point, rule statistics), Exchange rates and nested `DB()`, Improving
  performance with feeders, Moving data and changing levels, Time-based
  calculations, Fixed allocations, Stocks and flows, Total product costs, and the
  Rules tracer. Its worked example is the Fishcakes International model.
- IBM, [Logical operators](https://www.ibm.com/docs/SSD29G_2.0.0/com.ibm.swg.ba.cognos.tm1_ref.2.0.0.doc/c_logicaloperatorsintm1rules_n8053c.html),
  [Comparison operators](https://www.ibm.com/docs/en/planning-analytics/2.0.0?topic=functions-comparison-operators-in-tm1-rules).
- IBM, PAW:
  [Use the rules editor](https://www.ibm.com/docs/en/planning-analytics/2.0.0?topic=editor-use-rules-in-planning-analytics-workspace),
  [Create and edit rules](https://www.ibm.com/support/knowledgecenter/SSD29G_2.0.0/com.ibm.swg.ba.cognos.tm1_prism_gs.2.0.0.doc/t_paw_create_and_edit_rules.html).
