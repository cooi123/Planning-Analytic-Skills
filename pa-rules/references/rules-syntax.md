# TM1 rules syntax

A working reference for writing rule and feeder statements. Element, dimension and
cube names are illustrative. Check function availability for your release against
`{{config.platform.docs_base}}/{{config.platform.pa_version}}` (TM1 Rules /
TM1 Reference).

## File structure

```
FEEDSTRINGS;          # must be the first statement, and only if any rule returns a string
SKIPCHECK;            # sparse consolidation: skip cells believed empty
# rule statements
FEEDERS;              # everything after this line is a feeder
# feeder statements
```

- Every statement ends with `;`.
- `#` starts a comment, which runs to the end of the line.
- One rule file per cube, stored on the server as `<cube>.rux`.

## Rule statement

```
[area] = formula;
[area] = N: formula;                  # leaf cells only
[area] = C: formula;                  # consolidated cells only
[area] = N: formula1; C: formula2;    # different formula per level
```

### Area forms

| Form | Matches |
|---|---|
| `[]` | Every cell in the cube |
| `['Revenue']` | Any cell where any dimension is at `Revenue` |
| `['Measure':'Revenue']` | `Revenue` in dimension `Measure`. Use this whenever a name could exist in two dimensions |
| `['Budget', 'Revenue']` | Cells at both `Budget` and `Revenue` |
| `[{'Jan', 'Feb', 'Mar'}, 'Revenue']` | `Revenue` in any of the listed periods |

### Precedence

Statements are evaluated top to bottom, and **the first one whose area matches the
cell wins**. Everything below it is ignored for that cell.

- Put specific statements above general ones.
- `STET` makes a matching cell behave as if no rule applied: input is allowed, and
  it consolidates normally.
- `CONTINUE` passes evaluation to the next matching statement. Use it sparingly,
  because it makes tracing hard.

```
['Budget', 'Price'] = STET;                 # budget price is typed in
['Price'] = N: ['Revenue'] \ ['Units'];     # every other version derives it
```

## Operators

### Arithmetic

| Op | Meaning |
|---|---|
| `+ - * ^` | Add, subtract, multiply, power |
| `/` | Divide. **Division by zero returns an undefined value** (shows as N/A) |
| `\` | Divide. **Division by zero returns 0.** The safe choice whenever the denominator can be empty |

### Comparison

| Numbers | Strings | Meaning |
|---|---|---|
| `=` | `@=` | Equal |
| `<>` | `@<>` | Not equal |
| `>` `<` | `@>` `@<` | Greater, less |
| `>=` `<=` | `@>=` `@<=` | Greater or equal, less or equal |

A string compared with `=` is not a string comparison. Use the `@` form.

### Logical and string

| Op | Meaning |
|---|---|
| `&` | AND |
| `%` | OR |
| `~` | NOT, e.g. `~(x = 5)` is the same as `x <> 5` |
| `\|` | String concatenation, **not** OR |

## Referencing data

| Construct | Meaning |
|---|---|
| `['Units']` | The value of `Units` at the current cell's other coordinates, in this cube |
| `!Period` | The name of the current cell's element in dimension `Period` |
| `DB('Cube', a1, a2, …)` | A value from any cube. One argument per dimension **of that cube, in its order**. Use `!Dim` to pass the current element through, or a quoted name to fix one |
| `ATTRS('Dim', elem, 'Attr')` / `ATTRN(…)` | String or numeric attribute of an element |

```
['Revenue Reporting'] = N:
    ['Revenue Local'] * DB('Exchange Rates', !Version, !Period,
                           ATTRS('Organization', !Organization, 'Currency'), 'Rate');
```

- **Arguments can be expressions.** Any `DB()` argument can itself be an expression
  that returns a valid element name of that position's dimension: `ATTRS(…)` as
  above, or a nested `DB()` reading an element name stored in another cube. IBM's
  example:
  `DB('CurrencyExchangeRate', DB('Currency', !market, 'MarketCurrency'), !date)`.
- **`!Dim` must be a dimension of the cube the rule is in.** Using `!Currency` in
  a cube without a Currency dimension fails validation with `Syntax error on or
  before: … invalid string expression`.
- **Feed in the opposite direction.** Calculation statements live in the target
  cube. Their feeders live in the **source** cube and point back with `DB()`. IBM
  describes the feeder as the inverse of the calculation statement.

## Frequently used functions

The full list by category is in `rules-functions.md`, including which of each
legacy/hierarchy-aware pair to use.

| Function | Returns |
|---|---|
| `IF(cond, a, b)` | `a` if `cond` is true, else `b` |
| `ISLEAF` | 1 when the current cell is a leaf cell |
| `ELLEV('Dim', elem)` | Element level, where 0 is a leaf |
| `ELPAR('Dim', elem, n)` | The nth parent |
| `ELISANC('Dim', anc, elem)` | 1 if `anc` is an ancestor of `elem` |
| `DIMIX('Dim', elem)` / `DIMNM('Dim', idx)` | Index of an element / element at an index |
| `DTYPE('Dim', elem)` | `N`, `C` or `S` (numeric, consolidated, string) |
| `ABS` `ROUND` `ROUNDP(x, d)` `INT` `MOD` `MAX` `MIN` | Numeric helpers |
| `SUBST(s, start, len)` `LONG(s)` `SCAN(sub, s)` `TRIM` `UPPER` | String helpers |
| `STR(n, len, dec)` / `NUMBR(s)` | Number to string / string to number |

## Feeder statements

```
FEEDERS;
['Units'] => ['Revenue'];                                       # same cube
['Units'] => DB('Margin', !Version, !Period, !Product, 'Units'); # into another cube
```

- The left side is the **source** area in this cube. The right side is the target
  cell or cells.
- A feeder only marks the target as possibly non-empty. It calculates nothing.
- Feeders fire when a source cell gets a value, and when the rules are saved or
  the server loads them.
- A feeder whose target is a consolidation feeds every leaf beneath it. That's a
  common source of overfeeding.
- A rule-calculated source only feeds onward if it is itself fed (feeder chains).

### Conditional feeder

Put an `IF` in the cube-name argument of `DB()`. An empty or blank cube name is not
a valid target, so nothing is fed when the condition is false.

```
['Units'] => DB(IF(['Active Flag'] = 1, 'Revenue', ''),
                !Version, !Period, !Product, 'Revenue');
```

Mirror the rule's own condition, so the feeder fires exactly when the rule can
produce a value.

### Feeders for string rules

`FEEDSTRINGS;` as the first line allows string cells to be fed. Feed the string
target from a source that's populated whenever the string should show.

## Sources

- IBM, TM1 Rules guide:
  [Using DB functions to move data between cubes](https://www.ibm.com/docs/en/planning-analytics/2.1.0?topic=rules-using-db-functions-move-data-between-cubes),
  [Writing nested DB functions](https://www.ibm.com/docs/en/planning-analytics/2.1.0?topic=cube-writing-nested-db-functions),
  [Feeding one cube from another](https://www.ibm.com/docs/en/planning-analytics/2.0.0?topic=feeders-feeding-one-cube-from-another),
  [Logical operators](https://www.ibm.com/docs/SSD29G_2.0.0/com.ibm.swg.ba.cognos.tm1_ref.2.0.0.doc/c_logicaloperatorsintm1rules_n8053c.html),
  [Comparison operators](https://www.ibm.com/docs/en/planning-analytics/2.0.0?topic=functions-comparison-operators-in-tm1-rules).
- IBM, PAW:
  [Use the rules editor in Planning Analytics Workspace](https://www.ibm.com/docs/en/planning-analytics/2.0.0?topic=editor-use-rules-in-planning-analytics-workspace),
  [Create and edit rules](https://www.ibm.com/support/knowledgecenter/SSD29G_2.0.0/com.ibm.swg.ba.cognos.tm1_prism_gs.2.0.0.doc/t_paw_create_and_edit_rules.html).
  The guide's worked example is the Fishcakes International model (Purchase,
  Inventory, CurrencyExchangeRate cubes).

## Often forgotten

Concepts that come up repeatedly in reviews. The first three are summarised from
Lee Lazarow,
[Rule Concepts that are often Forgotten](https://revelwood.com/ibm-planning-analytics-tips-tricks-rule-concepts-that-are-often-forgotten/)
(Revelwood, 2019).

| Concept | Remember |
|---|---|
| Two division operators | `/` gives an undefined value on division by zero. `\` gives 0 |
| String comparison | Prefix the comparison with `@`: `IF(['Status'] @= 'Approved', …)` |
| Negation | `~( … )` inverts any condition |
| OR is `%` | `\|` concatenates strings, so `a \| b` is not a logical OR |
| First match wins | A broad statement above a narrow one silently disables it |
| No `N:` overrides totals | An unqualified rule also replaces the consolidated value |
| `DB()` arity | One argument per dimension of the **target** cube, in that cube's order |
| Strings live in the last dimension | A string rule needs a string element in the cube's last dimension, plus `FEEDSTRINGS` |
| Saving replaces the file | Any save, whether workbench, REST or `RuleLoadFromFile`, overwrites the whole rule file |
| Rule cells are read-only | Add `STET` above, or narrow the area, where input must stay possible |
