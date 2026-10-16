# From a selected cell to its dimensions, parents and roll-ups

A PAW selected cell arrives as a position and a value only:

```json
{"rowIndex": 0, "colIndex": 0, "value": 11867784, "formattedValue": "11,867.8K"}
```

No dimension names, no member names, no hierarchy. Everything else has to be
rebuilt from the widget's MDX and from TM1. This page shows how, using four
`[PAW_CONTEXT_VERIFIED]` captures from the DRP Route Profitability Control Tower
dashboard (`pa-context-json-example.md`, 2026-10-06).

## 1. What the captures show

| # | Capture | Selected entry | Cells | Notable |
|---|---|---|---|---|
| 1 | Single cell, P&L table | cube entry 4 of 5 | `(0,0)` = 126,527,424 | Columns are a literal list of 4 measures |
| 2 | Two cells, same column | cube entry 4 of 5 | `(1,0)`, then `(0,0)` | Click order kept: row 1 came first |
| 3 | "All column selected" | cube entry 4 of 5 | `(0,0)` only | MDX changed to `DRILLDOWNMEMBER(Total Revenue)` |
| 4 | Single cell, budget variance table | cube entry 8 of 9 | `(0,0)` = 11,867,784 | Rows `ORDER(..., Var to Budget %, BASC)`. Entry 4's earlier selection is now empty |

Findings:

1. **One "widget" means the whole sheet.** `widget_count` is 1. Every
   visualisation on the sheet (KPI tiles, the P&L table, the variance table) is a
   separate entry under `cubes`, numbered by `cube_id` in layout order. Adding the
   variance visualisations took the count from 5 to 9.
2. **The selection markers don't identify the selection.** Throughout,
   `selected_widget_id` and top-level `selected_cube_name` are null and every
   `is_selected_cube` is false. The widget-level `selected_cube_name` is just the
   cube name, which every entry shares. **The selected visualisation is the entry
   whose `selected_cells` is non-empty.**
3. **Only one visualisation holds a selection at a time.** Selecting in the
   variance table (capture 4) cleared the P&L table's cells.
4. **Selecting a column header does not give you the column.** Capture 3 still has
   one cell. The MDX shows `Total Revenue` was drilled, so the header click
   expanded the member rather than selecting cells. Treat header and
   row/column selection as not reported.
5. **Use `value`, not `formattedValue`.** The raw `value` is present and exact.
   `formattedValue` formats differ between visualisations (`126.5M` against
   `11,867.8K`).
6. **Row order often can't be predicted from the text.** Capture 4 sorts rows by
   value (`ORDER ... BASC`), so row 0 is the route with the worst variance, not
   the first route in the dimension. `EXCEPT(DESCENDANTS(...))` is dynamic too.
   Always execute the MDX to find row labels.
7. **Column members may stop being readable from the text.** In captures 1, 2
   and 4 the columns are a literal list. After the drill in capture 3 they're
   `DRILLDOWNMEMBER(...)`, so column labels must also come from executing it.
8. **KPI tiles use calculated members.** `Weak Route Count` and `Worst Route
   Var %` are `WITH MEMBER` definitions. They have no parents or children. Explain
   them from their formula, not from the hierarchy.
9. **The plugin output is twice as big as it needs to be.** `summary` and
   `normalized_context` are identical. Drop one in `paw_data_context_guard.py`
   (pass only `summary=summary`) to save roughly half the tokens per turn.

## 2. What a cell coordinate is made of

Every cube cell has exactly one member from **every** dimension of the cube. For
a selected cell those members come from four places:

| Source | Where | Example (capture 4, cell 0,0) |
|---|---|---|
| Column axis | `ON 0` set, at `colIndex` | `DRP Version` = `Actual` |
| Row axis | `ON 1` set, at `rowIndex` | `DRP Route` = *the route at row 0 after sorting* |
| Slicer | `WHERE (...)` | `DRP Period` = `FY2026`, `DRP Aircraft Type` = `All Aircraft`, `DRP P&L Line` = `Contribution Margin` |
| Not in the MDX | cube dimensions minus the above | the hierarchy's default member |

Nested axes (two dimensions crossjoined on rows) contribute one member per
dimension each. None of the captured views are nested.

## 3. Procedure

```
data_context
  └─ find the cube entry with selected_cells               (finding 2)
       ├─ describe_selected_view(mdx)                       -> axis dims, slicer, calc members
       ├─ execute_mdx_and_get_view(mdx, unmodified)         -> table
       ├─ resolve_selected_cells(table, cells, value)       -> row label, column label, MATCH
       ├─ get_selected_cell_coordinates(mdx, rows, cols)    -> full coordinate
       ├─ get_cube_dimensions(cube)                         -> any dimension not in the coordinate is at its default
       └─ build_lineage_queries(cube, coords, dimension)    -> MDX for parents / roll-up / children / ...
              └─ execute_mdx_and_get_view(each query)
```

Tools come from `assets/resolve_selected_cell/` and `assets/cell_lineage/`.
`execute_mdx_and_get_view` and `get_cube_dimensions` are PA MCP tools.

1. **Pick the entry.** Use the cube entry whose `selected_cells` is non-empty.
   If several have cells, ask the user which one they mean.
2. **Describe the view.** `describe_selected_view(mdx)` returns which dimensions
   are on each axis, whether the axis members can be read from the MDX text, whether
   rows are sorted by value, the slicer members and any calculated members.
3. **Resolve labels.** Run the MDX unchanged, then `resolve_selected_cells` with
   `expected_value` set to the cell's raw `value`. Continue only on `RESOLVED` +
   `MATCH`.
4. **Build the coordinate.** `get_selected_cell_coordinates(mdx, [row label],
   [column label])`. It errors if the number of labels doesn't match the number of
   dimensions on the axis (a sign of a nested axis or a wrong label).
5. **Fill missing dimensions.** Compare the coordinate against
   `get_cube_dimensions`. Any dimension that's missing is at its default member.
   Say so rather than inventing one.
6. **Walk the hierarchy.** `build_lineage_queries(cube, coordinates, dimension)`
   returns ready-to-run MDX. Each query holds every other coordinate fixed, so
   every row it returns comes with its matching cube value.

## 4. The lineage queries

For the route `SYD-BNE`, cell Total Revenue / Actual / FY2026 / All Aircraft:

| Query | Row set | Answers |
|---|---|---|
| `rollup_path` | `ASCENDANTS([DRP Route].[DRP Route].[SYD-BNE])` | The member and each ancestor up to the top, **with values**: SYD-BNE → its parent group → … → All Domestic Routes |
| `all_direct_parents` | `FILTER(TM1SUBSETALL(dim), COUNT(INTERSECT(dim.CURRENTMEMBER.CHILDREN, {m})) > 0)` | Every consolidation the member rolls into directly, **including multiple parents** |
| `children` | `m.CHILDREN` | What a consolidated member is made of |
| `siblings` | `m.SIBLINGS` | Peers under the same parent, for comparison |
| `leaf_descendants` | `TM1FILTERBYLEVEL(DESCENDANTS(m), 0)` | Every leaf that rolls into a consolidated member |
| `share_of_parent` | `{m, m.PARENT}` | Member and parent values: divide them for the share |
| `attributes` | all attributes of `m` from `}ElementAttributes_<dim>` | Captions, codes, flags |

Example `rollup_path`:

```sql
SELECT {[DRP P&L Line].[DRP P&L Line].[Total Revenue]} ON 0,
       {ASCENDANTS([DRP Route].[DRP Route].[SYD-BNE])} ON 1
FROM [DRP Route P&L]
WHERE ([DRP Version].[DRP Version].[Actual],
       [DRP Period].[DRP Period].[FY2026],
       [DRP Aircraft Type].[DRP Aircraft Type].[All Aircraft])
```

The same works for every dimension of the cell. Exploring `DRP P&L Line` from
`Total Revenue` gives its children (the revenue lines). Exploring `DRP Period`
from `FY2026` gives its quarters and months.

### TM1 caveats

- `.PARENT` and `ASCENDANTS` follow the **first** parent only. When a member has
  several parents (alternate roll-ups), use `all_direct_parents`, and run
  `rollup_path` again from each parent you care about.
- **Element weights** (e.g. a `-1` that turns a cost into a subtraction) aren't
  available through MDX. The roll-up values are already weighted, but the weight
  itself needs the TM1 REST API (`Edges`) or a TI process.
- **Alternate hierarchies.** The parser keeps the hierarchy named in the MDX. If
  the view uses `[Dim].[AltHier]`, the lineage queries walk that hierarchy, not
  the main one.
- **Rule-calculated cells.** A cell can be leaf-level and still calculated by a
  rule. Lineage shows consolidation structure only. Use the rules (or impact
  analysis) to explain a rule-derived value.
- **Calculated members** (`WITH MEMBER`) are not in the dimension. The tools
  flag them and refuse to build lineage queries for them.

## 5. What to tell the model

```text
To explain what a selected cell is or how it rolls up:
1. Use the cube entry whose selected_cells is non-empty. Ignore is_selected_cube,
   selected_widget_id and selected_cube_name; they don't identify the selection.
2. Run its MDX unchanged, resolve with resolve_selected_cells using the cell's raw
   value, then call get_selected_cell_coordinates with the resolved labels.
3. For parents, roll-ups, children, siblings or leaves, call
   build_lineage_queries for the dimension the user asked about and run the
   returned MDX unchanged. Never write hierarchy MDX yourself.
4. If a member is flagged calculated, explain it from its WITH MEMBER definition.
5. For a member with several parents, report all of them from all_direct_parents.
   Don't present the first-parent roll-up path as the only one.
```

## Status

The parser is unit-tested against all four captured MDX statements
(`assets/cell_lineage/test_cell_lineage.py`, 9 tests). The generated lineage MDX
has **not yet been run against TM1**. Before relying on it, run each query once
on `Airline-asset` with `execute_mdx_and_get_view`, especially `SIBLINGS`,
`all_direct_parents` and the attributes query, whose support varies across TM1
versions.
