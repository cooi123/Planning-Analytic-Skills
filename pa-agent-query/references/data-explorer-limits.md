# Data explorer limits: a worked retrieval test

Observed August 2026 on PA as a Service, TM1 12.6.3, against a retail P&L cube with
seven dimensions. The two large ones were a profit centre dimension of 11,499 members
and a GL account dimension of 5,470 members with no descriptions in source. About 150
profit centres and 300 accounts held data.

One question, run four ways: three times through `get_data_from_data_explorer` and
once through `execute_mdx_and_get_view` as ground truth.

> "Which store had the worst sales variance to budget in FY2025?"

**Result:** the data explorer answered none of the three. The MDX answered it exactly.

## Ground truth: MDX

`lookup_potential_members` first confirmed the account was named exactly `Sales`. The
dimension also held `Sales - Instore`, `Sales - Online`, `Comp Sales` and `IFRS Sales`.

```mdx
WITH
  MEMBER [Version].[Version].[Act vs Bud] AS
    [Version].[Version].[Actual] - [Version].[Version].[Budget]
  MEMBER [Version].[Version].[Act vs Bud %] AS
    IIF([Version].[Version].[Budget] = 0, NULL,
        ([Version].[Version].[Actual] - [Version].[Version].[Budget])
        / ABS([Version].[Version].[Budget])),
    FORMAT_STRING = '#,##0.0%'
SELECT
  {[Version].[Version].[Actual], [Version].[Version].[Budget],
   [Version].[Version].[Act vs Bud], [Version].[Version].[Act vs Bud %]} ON COLUMNS,
  ORDER(TM1SUBSETTOSET([Profit_Centre].[Profit_Centre], 'Selected Stores'),
        [Version].[Version].[Act vs Bud %], BASC) ON ROWS
FROM [Financials]
WHERE ([Year].[Year].[2025], [Period].[Period].[12 YTD],
       [Reporting_GL_Accounts].[Reporting_GL_Accounts].[Sales],
       [Company_Code].[Company_Code].[<company>], [Currency].[Currency].[AUD])
```

Ten stores came back, worst first. A second query against
`}ElementAttributes_Profit_Centre` turned the store codes into names, because the
names lived only in an attribute.

The worst store by percentage was -6.0%. A different store missed by more dollars at
-5.5%. The answer depends on which "worst" the user means, so the answer has to say.

## Attempt 1: the question verbatim

| Dimension | Data explorer chose | Problem |
|---|---|---|
| Version | `Budget` only | No Actual, so variance can't be expressed |
| Profit centre | `All Obsolete Profit Centres` | Fuzzy-matched "store" to an empty node, and put it in context, not on rows |
| Account | default `Company P&L` subset | "Sales" dropped |
| Period | default `Months` subset | Not the full-year YTD member |

Output: a grid of zeros.

## Attempt 2: dimensions named explicitly

"Show Sales for Actual and Budget in year 2025 period 12 YTD for the selected stores
in Profit_Centre"

Year, period and version all landed correctly. Naming them worked. Two failures
remained:

- "selected stores" matched `TOTAL STORES`, another empty node, again in context.
- "Sales" was ignored again in favour of the default account subset.

Output: zeros again.

## Attempt 3: one plain cell

"Sales for ST1001 Northside, Actual, year 2025, period 12 YTD"

This attempt checked whether the zeros were a member problem or a data problem. It is
the important one.

The explorer reported that it put `D1001EL` in context "because it was the most
similar" to the store requested. `D1001EL` is one department leaf under the store
rollup `ST1001`. The account was dropped a third time.

Output: real, plausible numbers. Retail EBIT 2,120,467, gross profit 2,040,767, and
so on, all internally consistent, for the wrong profit centre and the wrong account.
The correct figure, Sales for the store, was 43,005,110. Nothing in the output said
anything was off.

## Diagnosis

Two separate causes.

**Variance is out of reach by construction.** In this cube variance exists only as
MDX calculated members inside saved views. There are no variance members in `Version`
and no rules. The data explorer places dimension members on axes. It can't subtract,
so "worst variance" can't be asked of it. The same applies to ad-hoc users in PAW and
Excel, and it was an accepted design trade-off (see
`../../pa-model-design/references/views-and-calculated-members.md`).

**Member resolution is fuzzy string matching over large, code-named dimensions.**

| Asked for | Got | Kind of node |
|---|---|---|
| "store", implied | `All Obsolete Profit Centres` | empty |
| "selected stores" | `TOTAL STORES` | empty |
| `ST1001`, an exact member name | `D1001EL` | wrong level, a leaf of the right store |
| "Sales", three times | the default account subset | dimension ignored |

The explorer didn't use the `Comment` attribute holding real store names, or the
loaded-scope subsets that narrow the dimensions to the members with data. It also put
the profit centre in context, one member, so even perfect matching couldn't have
produced a per-store ranking.

## What to do about it

- Don't test single-cell retrieval, variance or ranking through the data explorer.
  Use `execute_mdx_and_get_view`, or run a saved view's MDX.
- Use the data explorer to explore, then confirm its member choices before quoting a
  number.
- Keep attempt 3 as a **standing regression case** in the agent test set. A question
  with a known answer where the tool returns a confident wrong number is worth more
  than any number of questions that return zeros. Zeros get caught. `2,120,467`
  doesn't.
- Retest after each PA MCP upgrade. Member resolution is the part most likely to
  change, and an improvement there would move some questions back within the
  explorer's reach.
