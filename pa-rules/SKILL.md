---
name: pa-rules
description: >-
  Write, explain, fix and deploy IBM Planning Analytics (TM1) business rules and
  feeders: area statements, N:/C: scope, DB() cross-cube references, STET,
  SKIPCHECK, FEEDSTRINGS, conditional and cross-cube feeders, and putting the rule
  file on a server through the PAW Modeling workbench, TurboIntegrator or the TM1
  REST API. Use for "write a TM1 rule", "rule for this calculation", "add a feeder",
  "convert this Excel formula to a rule", "explain this rule", "my rule isn't
  calculating", "rule returns N/A", "total shows zero", "string rule disappears",
  "conditional feeder", "cross-cube rule", "import rules into PAW", "rules editor",
  "load a .rux file", or "validate my rules".
user-invocable: true
---

# PA rules

Write TM1 rules that calculate the right number, are fed exactly enough, and reach
the server without overwriting anything. This skill authors and debugs individual
rule files. For cube-level architecture (which cubes, which calculations belong in
rules at all), use `pa-model-design`. Its `references/rules-and-feeders.md` is the
design standard this skill applies.

Read `references/rules-syntax.md` before writing any statement, and
`references/rules-functions.md` when choosing a function. Read
`references/rule-examples.md` when the request matches a known shape. Point the user
to `references/writing-and-deploying-guide.md` when they need the click-path to put
rules on a server.

## Step 0. Load conventions and get the facts

1. **Conventions.** First hit wins: `./pa-conventions.yaml`,
   `./config/pa-conventions.yaml`, `../config/pa-conventions.yaml`. The `rules:`
   keys (`require_skipcheck`, `require_feeder_for_every_leaf_rule`,
   `feedstrings_when_string_rules`, `protect_calculated_measures`) are
   authoritative. If no file is found, use those keys as `true` and say so.
2. **The cube's facts.** Get them from the live connection if there is one. With
   the PA MCP tools:
   - `get_cube_dimensions` gives the dimensions **in order**. Every `DB()` and
     `!Dim` reference depends on that order.
   - `lookup_potential_members` and `get_cube_sample_members` give real element
     names.

   Without a connection, ask the user to paste the dimension list and the element
   names involved. **Never invent an element or dimension name.** A misspelt name
   doesn't fail loudly. The rule simply never matches.
3. **The existing rule file.** Saving a cube's rules replaces the whole file. Get
   the current text before writing anything: from the user, from the workbench, or
   via REST `GET /api/v1/Cubes('<cube>')?$select=Rules`.
4. **Input versus calculated.** Which cells do people type into, and which must the
   rule fill? A rule-calculated cell can no longer be typed into.
5. **Numeric or string.** A string rule needs a string element in the cube's
   **last** dimension, plus `FEEDSTRINGS`.

## Step 1. Check a rule is the right tool

Rules are evaluated every time a cell is read, for the life of the model. If the
value is static, set once, needed only at period end, or expensive and read
constantly, a TI process is usually better. See section 4 of
`../pa-model-design/references/rules-and-feeders.md` and check `RUL-006`. Say so
when a rule is the wrong tool rather than writing one anyway.

## Step 2. Write each statement

`[area] = [N: | C: | S:] formula;` Work through this checklist for every statement:

- **Area.** Make it as narrow as the logic needs. Qualify an element with its
  dimension (`['Measure':'Revenue']`) whenever the name could exist in another
  dimension.
- **Scope.** Default to `N:`. Leave the scope off only when the consolidated value
  genuinely isn't the sum of its children: ratios, averages, rates, balances. Then
  record why in a comment (`RUL-003`). Text results need `S:`, because `N:` never
  reaches a string cell. Put the qualifier right before the formula, never at the
  start of the statement.
- **Precedence of operators.** `*` binds before `/`, so `a \ b * c` is
  `a \ (b * c)`. Use parentheses whenever you mix them.
- **Division.** Use `\` when the denominator can be zero. It returns 0, where `/`
  returns an undefined value (`RUL-005`).
- **Strings.**
  - Compare with `@=`, `@<>` and so on, not `=`.
  - Read a string cell with `DB()`, even in the same cube.
  - Both `IF` branches must be the same type.
- **Logic.** `&` is AND, `%` is OR, `~` is NOT, and `|` joins strings. `|` is
  **not** OR.
- **Cross-cube.** `DB('Cube', arg1, …)` takes one argument per dimension of the
  target cube, in its order. Use `!Dim` to pass the current element through. `!Dim`
  must be a dimension of **this** cube.
- **Time series.** Step periods with `DIMNM('Month', DIMIX('Month', !Month) - 1)`
  and guard the first period. Hold "current month" in a control cube, not
  `NOW`.
- **Functions.**
  - If the dimension has alternate hierarchies, use the hierarchy-aware
    `Element…` functions. Otherwise match the family the file already uses.
  - Never put `NOW`, `TODAY`, `TIME` or `RAND` in a rule.
  - For a total that must not sum, use a `C:` rule with a `Consolidated…`
    function.
- **Exceptions.** Put `STET` statements, and anything else specific, **above** the
  general statement. The first matching statement wins (`RUL-004`).
- **Comments.** Add a `#` comment saying what the statement does and why.

## Step 3. Write its feeder in the same step

With `SKIPCHECK` on, an unfed rule cell is treated as empty and vanishes from totals
and from zero-suppressed views. Never hand over a rule without its feeder, or a
written reason it needs none. Apply `FED-001` to `FED-006`:

- Feed from the **sparsest** operand: the one most often empty. If the rule is
  non-zero only when every operand is, one feeder from that operand is enough.
- Feeding always starts from leaf cells. A consolidation on the left side is
  shorthand for its leaves, which suits a feeder that mirrors a rule reading that
  consolidation.
- Qualify the target fully. A consolidation on the **right** side feeds every leaf
  under it. Keep `DNEXT` or index steps off consolidations with a `DTYPE` or
  `DIMIX` guard.
- Feeders take no `N:`/`C:` qualifier. Where overfeeding is unavoidable (a target
  cube with extra dimensions), say so.
- Conditional feeders aren't supported with multi-threaded feeders
  (`MTFeeders`). Ask whether the server uses them.
- Mirror the rule's condition with a **conditional feeder** (see
  `rules-syntax.md`).
- A rule that reads another cube with `DB()` needs its feeder written **in the
  source cube's** rule file, pointing at the target cube. When the formula
  multiplies values from two cubes, put the feeder in the sparser one. Label
  cross-cube feeders with a comment such as `# Feeders for the Inventory cube`.

## Step 4. Assemble into the full rule file

```
FEEDSTRINGS;      # only if a rule returns a string
SKIPCHECK;
# ... rule statements, specific before general ...
FEEDERS;
# ... feeder statements ...
```

Merge into the existing file from Step 0. Never drop or reorder existing statements
without saying so. List what was added, changed and left alone. If the new
statement would sit below a broader existing one that already covers its area, say
so: it will never fire.

## Step 5. Self-check

Run every `RUL-*` and `FED-*` check in `../pa-model-review/checks/checks.yaml`
against the assembled file, honouring each check's `config_ref`. Fix any failure,
or state the deviation and why.

## Step 6. Validate, then deploy only when asked

**Validate** without saving: in a PAW Modeling workbench, right-click the cube and
choose **Edit business rules** (or **Create business rules**), paste the text, and
click **Validate business rules**. Ctrl+Space auto-complete there catches misspelt
element names. Over REST, use `POST
/api/v1/Cubes('<cube>')/tm1.CheckRules` (checks the saved rules). If neither is
available, say the rules are **not validated against a server**.

**Deploy** only when the user explicitly asks, and never to an environment marked
`writable: false` in `{{config.environments}}`. There are three routes, with
click-paths in `references/writing-and-deploying-guide.md`:

| Route | Use when |
|---|---|
| PAW Modeling workbench rules editor | Interactive change by a modeller (the only place PAW edits rules since 2.0.78) |
| TI `RuleLoadFromFile(cube, file)` | Promoting a `.rux` file between environments in a controlled process |
| REST `PATCH /api/v1/Cubes('<cube>')` with `{"Rules": "<text>"}` | Scripted deployment. It replaces the whole file |

The PA MCP endpoint (`ibm-pa-tools`, verified at 1.27.2) has **no rules tool**. An
agent connected only through MCP can't read or save rules. Hand the text to the
user and point them at the workbench.

Saving rules makes TM1 reprocess that cube's feeders, which can take a while on a
large cube.

## Step 7. Test

Give the user a test plan with these checks:

- **The right number.** In a sandbox, enter an input and confirm the calculated
  cell.
- **Totals add up.** Confirm the consolidation above the cell includes it. If it
  doesn't, the rule is unfed.
- **Feeders work.** In a PAW exploration, right-click the consolidation and choose
  **Check feeders**.
- **Zero suppression.** Turn it on and confirm the calculated cells still show.
- **Strings.** For string rules, confirm the text survives zero suppression.

## Explaining or fixing an existing rule

Read the whole file first, because precedence depends on position. Then work from
the symptom:

| Symptom | Usual cause |
|---|---|
| Total reads zero, leaves have values | Rule cells unfed (`FED-001`), or a cross-cube feeder is missing from the source cube (`FED-002`) |
| `N/A` or blank where a number is expected | `/` dividing by zero, or a `DB()` pointing at a non-existent element |
| Validation: `Syntax error on or before: … invalid string expression` | A `!Dim` names a dimension that isn't in this cube, or a `DB()` argument doesn't return an element name |
| Rule seems to do nothing | A broader statement above it wins, the area names an element that doesn't exist (typo, wrong dimension), or a text rule uses `N:` instead of `S:` |
| `Error Evaluating Rule: Possible Circular Reference` | Two statements depend on each other, e.g. Sales from Price and Price from Sales |
| Grand total differs between requests | A rule overrides a consolidation that is a component of another consolidation |
| A `= 1` test on summed percentages sometimes fails | Floating point. Compare within a tolerance, or hold whole-number percentages |
| A rule is slow | Turn on `RULE_STATS` in `}CubeProperties` and read `}StatsByRule` per line |
| Total ≠ sum of children | The rule has no `N:` and overrides consolidation (`RUL-003`) |
| String result vanishes | `FEEDSTRINGS` missing, or the string cell unfed (`RUL-002`) |
| Can't type into a cell | A rule covers it. Narrow the area or add `STET` above |
| Model slow or memory jumped after a change | Overfeeding: a feeder from a consolidation, or to an unqualified target (`FED-003` to `FED-006`) |

For full triage use `pa-model-review` in triage mode.

## Output

1. The rule statements and their feeders, in one code block, ready to paste.
2. A table with one row per statement: area, scope, what it calculates, its
   feeder or why it has none.
3. What changed against the existing file.
4. Validation status: validated in PAW, validated by `CheckRules`, or **not
   validated**.
5. Deployment steps, and the test plan from Step 7.

## Hard constraints

- Never write to a server unless the user explicitly asks, and confirm the cube
  and environment first.
- Read the existing rules before replacing them. Every save replaces the whole
  file.
- Never ask for credentials. Use the session's connection, or hand over the text.
- Never present a rule as verified when it wasn't validated against a server.
