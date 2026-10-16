# Glossary

Use these terms in every design spec, review, explanation and generated document.
Precise words make findings checkable: "an overfed cube" can be tested, "slow
calculations" can't.

**Tags.** `core` is how TM1 works. `convention` is a widely used practice that TM1
does not enforce (the Bedrock/Cubewise white papers, 2011); follow it only if
`pa-conventions.yaml` or the project says so. `v12` is behaviour observed on TM1
v12.6.3 on 2026-10-16; see the tested-behaviour files linked at the end.

## Model objects

| Say | Not | Meaning | Tag |
|---|---|---|---|
| **cube** | table, dataset | Multi-dimensional store; the unit that holds data and rules | core |
| **dimension** | column, field category | A named axis of a cube, holding a hierarchy of elements | core |
| **element** | row, record, item, member (see below) | One entry in a dimension | core |
| **leaf element** (type `N`) | detail row | Has no children and stores base data | core |
| **consolidated element** (type `C`) | total, subtotal | Aggregates its children by weighted sum | core |
| **string element** (type `S`) | text field | Holds a string value; lives in the measures dimension | core |
| **hierarchy** | tree, grouping | The parent-child structure of a dimension | core |
| **member** | | The MDX word for an element. Use "element" in TM1 prose, "member" when writing MDX | core |
| **alias** | description column | An alternate display name for an element | core |
| **principal name** | element name (when ambiguous) | The stored key. Rules, TI and feeders use it, never an alias | core |
| **measures dimension** | fact column, KPI dimension | The last dimension of the cube; its element types set the cell type | core |
| **subset** | filter | A saved list of elements from one dimension | core |
| **view** | report | A saved slice of a cube. An **MDX view** is defined by a query | core |
| **control cube** (`}` prefix) | config table | System cube holding security or configuration | core |
| **database** | server | The v12 word for a TM1 server instance. Use "server" only for v11 | v12 |

## Dimension order

| Say | Not | Meaning | Tag |
|---|---|---|---|
| **presentation order** | display order | The user-facing order of dimensions, set at creation | core |
| **physical order** | storage order | The internal order used for memory and speed; can be changed by re-dimensioning | core |
| **re-dimensioning** | re-ordering | Changing a cube's physical order | core |
| **sparsity** | | How few of a cube's possible cells hold data. Drives physical order and feeder cost | core |
| **shared dimension** | | A dimension used by several cubes (Version, Period, Organisation). Put these first and in the same order everywhere | convention |

## Rules and feeders

| Say | Not | Meaning | Tag |
|---|---|---|---|
| **rule** | formula, calculated field | A server-side calculation applied to an area of a cube at read time | core |
| **area statement** | left-hand side | The part before `=` saying which cells the rule covers | core |
| **`N:` / `C:` / `S:` qualifier** | leaf filter | Restricts a rule to leaf, consolidated or string cells | core |
| **shorthand** `['Elem']` / **longhand** `DB()` | | Intra-cube and cross-cube reference styles. Cross-cube references need `DB()` | core |
| **feeder** | trigger, pointer | A statement marking a target cell as non-empty so consolidation includes it | core |
| **`SKIPCHECK`** | sparse flag | File directive that lets consolidation skip cells not marked by a feeder. A performance choice: without it results are right but slower (v12) | core, v12 |
| **`FEEDERS;`** | | The section of a rule file that holds the feeders | core |
| **underfeeding** | missing feeders | A rule-calculated cell is not fed, so consolidations silently omit it. The leaf looks right and the total is blank (v12) | core, v12 |
| **overfeeding** | over-signalling | Feeding cells that never hold a value. Costs memory and speed, not correctness | core |
| **conditional feeder** | | A feeder whose target depends on an `IF`. It decides once, when it fires, and doesn't re-decide when the condition later changes (v12) | core, v12 |
| **`STET`** | pass-through, ignore | Stops rule evaluation for an area so the stored value shows | core |
| **precedence** | | Rules are read top to bottom and the first match wins. Write specific before general | core |
| **recursion depth** | | How many steps a rule chain follows (opening = prior closing). Past a limit the cell returns `#N/A` with no error. About 600 on the tested rule (v12) | core, v12 |
| **calculation cube** | | A cube whose time dimension is flat so period-to-period logic is a consolidation, not recursion | convention |
| **comment cube** | | A separate cube of string comments, kept out of the numeric cube | convention |

## TurboIntegrator

| Say | Not | Meaning | Tag |
|---|---|---|---|
| **TurboIntegrator (TI)**, **TI process** | script, macro, job | TM1's scripting and load engine | core |
| **Parameters, Prolog, Metadata, Data, Epilog** | | The process stages. Prolog runs once first, Metadata and Data run per source record, Epilog runs last | core |
| **chore** | batch job, scheduled task | A scheduled sequence of processes | core |
| **`CellPutN` / `CellPutS`** | write cell | Replace a numeric or string cell | core |
| **`CellIncrementN`** | | Add to a cell. Run twice, it doubles (v12) | core, v12 |
| **`ItemReject`** | | Skip one source record | core |
| **`ProcessBreak`** | | Stops reading source data and runs the Epilog. Status: completed | core, v12 |
| **`ProcessQuit`** | | Stops immediately. Status `QuitCalled`, caller code 9, Epilog does **not** run. Not an error status | v12 |
| **`ProcessError`** | | Stops immediately. Status `Aborted`, caller code 12, Epilog does **not** run | v12 |
| **minor error** | warning | A bad value (unknown key, consolidated or rule cell) logged while the process carries on. Status `HasMinorErrors` | v12 |
| **idempotent** | | Safe to re-run: the second run leaves the same result | core |
| **update (not recreate)** | | Changing a dimension without deleting its elements first. Recreate loses data silently | core, v12 |
| **`p` / `v` / `c` / `n` / `s` prefixes** | | Parameter, variable, constant, numeric, string naming | convention |
| **`pDebug`** (0, 1, 2) | | Normal, normal plus debug output, debug output and no updates | convention |
| **`zSys_`** prefix | | Name prefix for utility cubes and processes | convention |

## PAW content

| Say | Not | Meaning | Tag |
|---|---|---|---|
| **book** | report, dashboard (loosely) | A PAW container of sheets or tabs. **Classic book**: sheets of grid widgets. **Dashboard**: tabs of widgets, including charts | core |
| **widget** | tile, visual | One element on a sheet or tab: grid, chart, selector, cube viewer | core |
| **selector** | filter, slicer | A widget that sets a member for other widgets that share its hierarchy | core |
| **synchronised hierarchy** | linked filter | A hierarchy that several widgets on a tab follow together | core |

## When writing output

1. Use these terms exactly. Never substitute generic BI words.
2. Describe a rule by area, qualifier and calculation, and name its feeder.
3. Describe a TI process by its stages, with its parameters.
4. State dimension order as presentation order and, where it matters, physical
   order.
5. Name a risk with its TM1 word: underfeeding, overfeeding, recursion depth,
   conditional feeder, recreate, minor error.
6. Mark a `convention` as a convention. Don't present it as a rule of TM1.

Details behind the `v12` tags:
`../../pa-rules/references/v12-tested-behaviour.md` and
`../../pa-ti/references/v12-tested-behaviour.md`.
