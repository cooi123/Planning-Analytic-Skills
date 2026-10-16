# MDX patterns for querying TM1 through the PA MCP tools

Each template ran against TM1 12.6.3 through `execute_mdx_and_get_view` and as saved
MDX views. Replace dimension, member and subset names with the model's own. Confirm
every member name with `lookup_potential_members` first.

## Contents
- [Variance members](#variance-members)
- [Prior year](#prior-year)
- [Ranking](#ranking)
- [Totals the dimension doesn't have](#totals-the-dimension-doesnt-have)
- [Names in every client](#names-in-every-client)
- [Reading names from attributes](#reading-names-from-attributes)
- [Client and tool caveats](#client-and-tool-caveats)

## Variance members

```mdx
WITH
  MEMBER [Version].[Version].[Act vs Bud] AS
    [Version].[Version].[Actual] - [Version].[Version].[Budget]
  MEMBER [Version].[Version].[Act vs Bud %] AS
    IIF([Version].[Version].[Budget] = 0, NULL,
        ([Version].[Version].[Actual] - [Version].[Version].[Budget])
        / ABS([Version].[Version].[Budget])),
    FORMAT_STRING = '#,##0.0%', SOLVE_ORDER = 10
```

- `ABS()` in the denominator assumes costs are stored negative. Then a cost overrun
  gives a more negative actual, a negative numerator and a negative result, the same
  as a revenue shortfall. Negative is unfavourable on every line. Confirm the
  convention from the weights before relying on it.

  | Line | Actual | Budget | Variance | Reads as |
  |---|---|---|---|---|
  | Revenue | 100 | 110 | -10 | unfavourable |
  | Revenue | 120 | 110 | +10 | favourable |
  | Cost, overspent | -50 | -45 | -5 | unfavourable |
  | Cost, underspent | -40 | -45 | +5 | favourable |

- `FORMAT_STRING` is required. Without it the cell shows `-0.03`, not `-2.5%`. Adding
  an explicit negative section such as `'#,##0.0%;-#,##0.0%'` changed nothing.
- `IIF(... = 0, NULL, ...)` keeps empty budgets out of the ratio, so `NON EMPTY`
  can drop them.
- The percentage recomputes at every level from consolidated Actual and Budget. A
  total's variance % is not an average of its children's percentages.

Swap `Budget` for `Forecast` for `Act vs FCT`.

## Prior year

```mdx
  MEMBER [Version].[Version].[Actual LY] AS
    ([Version].[Version].[Actual], [Year].[Year].CurrentMember.PrevMember)
  MEMBER [Version].[Version].[Act vs LY] AS
    [Version].[Version].[Actual]
    - ([Version].[Version].[Actual], [Year].[Year].CurrentMember.PrevMember)
```

`.PrevMember` follows element index order. It works on a flat Year dimension indexed
in year order. It breaks if Year has consolidations between the years or the index
order isn't chronological. The first year has no predecessor and returns an error, so
restrict the Year set instead of relying on it.

## Ranking

```mdx
SELECT {<measures>} ON COLUMNS,
  NON EMPTY ORDER(<entity set>, [Version].[Version].[Act vs Bud %], BASC) ON ROWS
```

`BASC` sorts worst-first and breaks the hierarchy, which a league table needs. `ORDER`
runs on the server on true values, so the order stays correct even through a renderer
that shows signs wrong.

Ranking only makes sense among entities that all carry the line. Ranking on `Sales`
returns only stores if distribution centres and admin centres carry no sales. That is
`NON EMPTY` working, not failing. Pick a line every entity carries, such as EBIT, for
a cross-channel table.

Keep subtotals out of any set you rank or sum.

## Totals the dimension doesn't have

When a dimension lacks a consolidation you need, for example three sibling leaves
that together make one site, build it in the `WITH` block:

```mdx
  MEMBER [Profit_Centre].[Profit_Centre].[Site A] AS
      [Profit_Centre].[Profit_Centre].[<leaf 1>]
    + [Profit_Centre].[Profit_Centre].[<leaf 2>]
    + [Profit_Centre].[Profit_Centre].[<leaf 3>], SOLVE_ORDER = 1
```

**`SOLVE_ORDER` decides who wins the intersection.** Where the site member meets
`Act vs Bud %`, both are calculated, and the higher solve order evaluates last. With
the site member higher, it summed the three leaves' percentages and read -10.6%. With
`Act vs Bud %` at 10 and the site at 1, the ratio ran over summed Actual and Budget
and read -3.5%. Dollar differences are additive and come out right either way.

These members are view-local. They don't exist in the dimension browser, PAW's member
tree, or any other query. Say so wherever they appear.

**TM1py caveat:** `execute_mdx_rows_and_values` assumes every row member is a real
element and raises `TypeError` on a calculated row member, whose `Element` comes back
null. Read the raw cellset instead.

## Names in every client

To put a display name in a column every client shows, use a string calculated member:

```mdx
  MEMBER [Version].[Version].[Description] AS
    IIF([Profit_Centre].[Profit_Centre].CurrentMember.Properties("Alias") = "",
        [Profit_Centre].[Profit_Centre].CurrentMember.Properties("MEMBER_NAME"),
        [Profit_Centre].[Profit_Centre].CurrentMember.Properties("Alias")),
    SOLVE_ORDER = 5
```

Three parts carry weight:

1. **The `IIF` fallback.** `Properties("Alias")` returns `""`, not the member name,
   where no alias is set. Without the fallback every unaliased row goes blank.
2. **`SOLVE_ORDER` above any summing member.** Left at the default, it evaluated
   inside a calculated site total, and `+` on strings concatenates. One site rendered
   as three names run together.
3. **`NONEMPTY()`, not `NON EMPTY`.** A string cell is never empty, so with this
   column on the axis every row qualifies and suppression stops. One view grew from 24
   rows to 497. Filter against numeric tuples only:

   ```mdx
   NONEMPTY(<row set>, {([Version].[Version].[Actual])}) ON ROWS
   ```

## Reading names from attributes

```mdx
SELECT {[}ElementAttributes_<dim>].[}ElementAttributes_<dim>].[Comment]} ON COLUMNS,
       {TM1SUBSETTOSET([<dim>].[<dim>], '<subset>')} ON ROWS
FROM [}ElementAttributes_<dim>]
```

An alias also resolves inside MDX. `[Northside VIC]` returns the member it aliases.

## Client and tool caveats

| Path | Variance % on a cost row | Shows aliases |
|---|---|---|
| `execute_mdx_and_get_view` | correct | only via a string column |
| TM1py `execute_mdx`, raw | correct, `-0.0251` | no, by default |
| TM1 REST `FormattedValue` | correct, `-2.5%` | n/a |
| PAW, PAfE | correct | yes |
| `get_saved_view` rendered | **sign inverted**, `2.5%` | no |

The inversion hit every row with a negative base. It is a rendering defect in that one
tool, not the view or the data. Compute from the first row of this table.
