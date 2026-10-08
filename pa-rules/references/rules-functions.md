# Rules functions: what exists and which to use

The PAW rules editor's **Function list** groups rules functions into the categories
below. Function names come from IBM's rules-function reference. Check each
function's syntax page for your release before relying on an argument order you
haven't used before.

## Rules of thumb

1. **References in the same cube use `['Element']`. Another cube uses `DB()`.**
   The feeder pattern you'll write (`=> DB(...)`) mirrors `DB()`, which keeps a rule
   and its feeder easy to compare.
2. **If the model uses alternate hierarchies, use the `Element…` functions.** They
   take a hierarchy argument (`ElementAttrS(dimension, hierarchy, element,
   attribute)`). The short legacy names (`ATTRS`, `ELLEV`, `ELPAR`, `DIMIX`, …)
   are fine on a dimension's default hierarchy and are what most existing rules
   use. Pick one family per rule file and stay consistent.
3. **Keep volatile functions out of rules.** `NOW`, `TODAY`, `TIME` and `RAND`
   return different values without any data changing. A cell that changes on its
   own breaks caching, auditing and reconciliation. Stamp dates with TI instead.
4. **Drive per-member logic with an attribute plus one generic rule**, not one rule
   per member. `ATTRS` / `ElementAttrS` is the usual tool.
5. **Use `\` for division rather than testing with `ISUND`.** Reach for `ISUND` /
   `ISUNDEFINEDCELLVALUE` only when the cube deliberately uses `UNDEFVALS`.

## Legacy and hierarchy-aware pairs

| Legacy (default hierarchy) | Hierarchy-aware | Returns |
|---|---|---|
| `ATTRS` / `ATTRN` | `ElementAttrS` / `ElementAttrN` | String / numeric attribute |
| `DIMIX` | `ElementIndex` | Index of an element |
| `DIMNM` | `ElementName` | Element at an index |
| `DIMSIZ` | `ElementCount` | Number of elements |
| `DNEXT` | `ElementNext` | The next element |
| `DNLEV` | `LevelCount` | Number of levels |
| `DTYPE` | `ElementType` | Element type (numeric, consolidated, string) |
| `ELCOMP` / `ELCOMPN` | `ElementComponent` / `ElementComponentCount` | A child of a consolidation / how many children |
| `ELISANC` | `ElementIsAncestor` | Is element1 an ancestor of element2 |
| `ELISCOMP` | `ElementIsComponent` | Is element1 a child of element2 |
| `ELISPAR` | `ElementIsParent` | Is element1 a parent of element2 |
| `ELLEV` | `ElementLevel` | Level (0 = leaf) |
| `ELPAR` / `ELPARN` | `ElementParent` / `ElementParentCount` | A parent / how many parents |
| `ELWEIGHT` | `ElementWeight` | A child's weight in a consolidation |
| — | `ElementFirst` | The first element of a dimension |

## By category

### Cube data

| Function | Use |
|---|---|
| `DB` | Read a cell from any cube. The standard for cross-cube rules |
| `CellValueN` / `CellValueS` | Read a numeric / string cell explicitly typed |
| `ISLEAF` | 1 when the current cell is a leaf cell. Use it to branch leaf-versus-total logic inside one statement |
| `UNDEFVALS` | Statement that makes the cube's default value "undefined" instead of 0. It changes every empty cell's behaviour, so use it deliberately |
| `UNDEF`, `UNDEFINEDCELLVALUE`, `ISUNDEFINEDCELLVALUE` | Work with that undefined default |

### Consolidation calculation

For a `C:` rule where a total must not be the sum of its children.

| Function | Returns |
|---|---|
| `ConsolidatedAvg`, `ConsolidatedMax`, `ConsolidatedMin` | Average / maximum / minimum of the values under a consolidation |
| `ConsolidatedCount`, `ConsolidatedCountUnique` | Count of values / of unique elements with data |
| `ConsolidateChildren` | Forces a consolidation to be the sum of its immediate children along one dimension |

Example: headcount at a quarter should be the last month's figure, or the
average, not a three-month sum. These functions scan the cells under a
consolidation, so test their cost on large cubes.

### Logical

| Function | Use |
|---|---|
| `IF(cond, a, b)` | Branching. Combine conditions with `&`, `%`, `~` |
| `STET` | Exempts an area from a broader rule below it |
| `CONTINUE` | Passes evaluation to the next statement with the same area. Use sparingly |

### Element and dimension information

Use these to drive logic from structure: "is this a leaf", "is this under Total
Europe", "what's the parent or next period". See the pairs table above for both
forms.

`TABDIM(cube, n)` returns the name of a cube's nth dimension. It's useful for
checking dimension order before writing a `DB()`.

### Text

String rules, building element names, converting between numbers and strings.

`CAPIT`, `CHAR`, `CODE`, `CODEW`, `DELET`, `FILL`, `INSRT`, `LONG`, `LOWER`,
`NUMBR`, `SCAN`, `STR`, `SUBST`, `TRIM`, `UPPER`.

Common uses:

- `SUBST(!Period, 1, 4)` to take a year from a period name.
- `NUMBR(...)` to turn a numeric code held as text into a number.
- `|` to join strings.

### Date and time

`DATE`, `DATES`, `DAY`, `DAYNO`, `MONTH`, `YEAR`, `TIMST`, `TIMVL` convert between
serial numbers and date strings. They're fine when the input is data, such as a
start-date attribute.

`NOW`, `TODAY` and `TIME` are volatile. Keep them out of rules (rule of thumb 3).

### Mathematical

`ABS`, `INT`, `MOD`, `ROUND`, `ROUNDP`, `MAX`, `MIN` (of two values), `SIGN`,
`SQRT`, `EXP`, `LN`, `LOG`, `ISUND`, plus trigonometry (`SIN`, `COS`, `TAN`, `ASIN`,
`ACOS`, `ATAN`).

Avoid `RAND` in rules. It's volatile.

### Financial

`PV`, `FV` and `PAYMT` for annuities: loan or lease payments, present and future
values.

## Sources

IBM Planning Analytics rules function reference, per category:
[Cube data](https://www.ibm.com/docs/en/planning-analytics/2.0.0?topic=rf-cube-data-rules-functions),
[Consolidation calculation](https://www.ibm.com/docs/en/planning-analytics/2.0.0?topic=rf-consolidation-calculation-rules-functions),
[Date and time](https://www.ibm.com/docs/en/planning-analytics/2.0.0?topic=rf-date-time-rules-functions),
[Dimension information](https://www.ibm.com/docs/en/planning-analytics/2.0.0?topic=rf-dimension-information-rules-functions),
[Element information](https://www.ibm.com/docs/en/planning-analytics/2.0.0?topic=rf-element-information-rules-functions),
[Financial](https://www.ibm.com/docs/en/planning-analytics/2.0.0?topic=rf-financial-rules-functions),
[Logical](https://www.ibm.com/docs/en/planning-analytics/2.0.0?topic=rf-logical-rules-functions),
[Mathematical](https://www.ibm.com/docs/en/planning-analytics/2.0.0?topic=rf-mathematical-rules-functions),
[Text](https://www.ibm.com/docs/en/planning-analytics/2.0.0?topic=rf-text-rules-functions),
[ElementAttrS](https://www.ibm.com/docs/SSD29G_2.0.0/com.ibm.swg.ba.cognos.tm1_ref.2.0.0.doc/r_tm1_ref_elementattrs.html).
