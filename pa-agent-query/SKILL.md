---
name: pa-agent-query
description: >-
  Get correct numbers out of an IBM Planning Analytics (TM1) cube through the PA MCP
  tools, and build and test an AI agent that does the same. Covers choosing between
  the natural-language data explorer, MDX and saved views, resolving members exactly,
  variance and ranking as MDX calculated members, sign conventions, reading raw
  cellsets instead of rendered views, turning codes into names, and a tiered
  regression test set for an agent. Use for "ask the cube", "what were sales for",
  "which store missed budget", "rank by variance", "the agent gave the wrong number",
  "data explorer returns zeros", "get_data_from_data_explorer picked the wrong member",
  "execute_mdx_and_get_view", "get_saved_view shows the wrong sign", "variance
  percentage", "test my PA agent", "agent instructions for Planning Analytics", or
  whenever an assistant or wxO agent answers a business question from TM1 data.
user-invocable: true
---

# PA agent query

Answer a business question from a TM1 cube through the PA MCP tools and be right, or
say plainly that the cube can't answer it. Use this when you are the one querying, and
when you are writing the instructions, tools and tests for an agent that will query.

Connection comes first. If the tools aren't showing up, use `pa-mcp-connect`. If the
question is about a cell the user selected in PAW, resolve the cell with
`paw-wxo-context` first and come back here with real member names.

The failure that matters is not an error or a page of zeros. Zeros get noticed. The
dangerous result is a real, plausible, internally consistent number for the wrong
member, and the natural-language data explorer produced exactly that in testing
(see `references/data-explorer-limits.md`).

## Step 0. Know the cube before the first query

Most wrong answers come from facts about the cube that aren't visible in its member
names. Establish these once per cube and keep them in the agent's instructions or a
cube profile file, never in your head:

| Fact | Why it changes answers | How to find it |
|---|---|---|
| Sign convention | Decides whether a negative variance is good or bad | Read consolidation weights on the measure/account dimension, then sample a cost line |
| Fiscal calendar | "FY2025" and "period 01" mean different months per model | Ask, or read the Period dimension's attributes |
| Which periods hold Actual | A YTD past the last closed month reads as a collapse | Query Actual by month for the current year |
| Data scope | Which years, versions, currencies and entities are loaded at all | Sample members, loaded-scope subsets |
| Reporting subsets | Narrow 10,000-member dimensions to the few hundred that carry data | `list_cube_views`, the subset list per dimension |
| Name attributes | Codes like `S200000` mean nothing to a user | Look for `Alias`, `Comment`, `Description` attributes |
| Calculations that live only in saved views | Variance members may not exist in any dimension | Read the saved views' MDX `WITH` blocks |

Write down the traps too: members that look loadable but are empty by design, data
quality defects, hierarchies known to be broken. An agent that knows "the rolling-3
hierarchies are broken" can refuse a rolling-3 question instead of answering it wrong.

## Step 1. Pick the tool

| Question shape | Use | Why |
|---|---|---|
| Exploring, no exact answer needed | `get_data_from_data_explorer` | Fast, no MDX. Treat its member choices as a guess and read them back |
| One cell, an exact figure | `execute_mdx_and_get_view` | You name every coordinate. Nothing is fuzzy-matched |
| Variance, ratio, ranking, top-N | `execute_mdx_and_get_view` with `WITH MEMBER` and `ORDER` | The data explorer places members on axes. It can't subtract or sort by a computed value |
| A question a saved view already answers | Run the view's MDX through `execute_mdx_and_get_view` | Same numbers as the view, raw values instead of rendered text |
| Display a view to a person | `get_saved_view` | Fine for looking at. Don't compute from its rendered output (Step 4) |

Default to MDX for anything you will quote as a number. The data explorer resolves
members by fuzzy string match and doesn't use alias or description attributes, so on
large, code-named dimensions it picks empty nodes and wrong levels. Naming the
dimensions explicitly in the query fixed year, period and version in testing. It did
not fix the entity or the account.

If you do use the data explorer, read the filters it reports before reading any
value. Reject the result if any of these hold:

- A member you asked about landed in context when the question needs it on an axis,
  as in "which store" or "by month".
- The member it chose is a different level from the one you asked for, for example a
  leaf under the rollup you named.
- A dimension you named fell back to its default subset.
- A version you need is missing. Variance needs both sides.

## Step 2. Resolve every member exactly

Before writing MDX, confirm each member name with `lookup_potential_members`.
Account dimensions carry near-namesakes, such as `Sales`, `Sales - Instore`,
`Sales - Online`, `Comp Sales` and `IFRS Sales`, and picking the wrong one is silent.

Check the level as well as the name. A store code and one of its department leaves can
share most of their characters. If the member you got has no children and you asked
about a total, you have the wrong member.

For a period question, decide the period member before querying:

- "FY2025" for a closed year is the full-year YTD consolidation, such as `12 YTD`, or
  `Full Year`. It is never a single month.
- Never load or query a member that double-counts. YTD consolidations sum the monthly
  leaves, so loading YTD directly doubles everything.
- For the current year, clamp to the last month that holds Actual. Comparing a
  two-month Actual against a twelve-month Budget reports an 85% miss that isn't real.
  Say that you clamped and why.

## Step 3. Write the MDX

`references/mdx-patterns.md` has tested templates. The ones you need most:

```mdx
WITH
  MEMBER [Version].[Version].[Act vs Bud] AS
    [Version].[Version].[Actual] - [Version].[Version].[Budget]
  MEMBER [Version].[Version].[Act vs Bud %] AS
    IIF([Version].[Version].[Budget] = 0, NULL,
        ([Version].[Version].[Actual] - [Version].[Version].[Budget])
        / ABS([Version].[Version].[Budget])),
    FORMAT_STRING = '#,##0.0%', SOLVE_ORDER = 10
SELECT
  {[Version].[Version].[Actual], [Version].[Version].[Budget],
   [Version].[Version].[Act vs Bud], [Version].[Version].[Act vs Bud %]} ON COLUMNS,
  ORDER(TM1SUBSETTOSET([Entity].[Entity], '<loaded entities subset>'),
        [Version].[Version].[Act vs Bud %], BASC) ON ROWS
FROM [<cube>]
WHERE ([Year].[Year].[2025], [Period].[Period].[12 YTD],
       [Account].[Account].[Sales], <every other dimension pinned>)
```

Rules that held up in testing:

- **Pin every dimension.** Anything left out of the query takes its default member,
  which is often a top consolidation you didn't intend.
- **Divide by `ABS()` of the base** when costs are stored negative. Then a negative
  variance means unfavourable on every line, revenue and cost alike, with no per-line
  flipping. Check the model's convention first. Under the opposite convention this
  rule is wrong.
- **Give ratio members the highest `SOLVE_ORDER`.** If another calculated member
  sums entities and wins the intersection, it sums the percentages. A three-leaf
  site total read -10.6% instead of -3.5% that way.
- **Use `ORDER(..., BASC)` on the variance %** for worst-first. `ORDER` runs on the
  server on true values, so the ranking is right even when a renderer shows the
  signs wrong.
- **Use the model's loaded-scope subsets** through `TM1SUBSETTOSET` instead of
  `Descendants` of a top node. The large dimensions are mostly empty.

## Step 4. Read raw values, not rendered views

The `get_saved_view` renderer was observed **inverting the sign of a variance %
wherever the base is negative**, which is every cost line under a costs-negative
convention. It showed `+2.5%` where the cube held `-2.5%`. `execute_mdx_and_get_view`,
TM1 REST `FormattedValue`, PAW and Excel all showed `-2.5%`. Compute and quote from
`execute_mdx_and_get_view`. If you have to cross-check a rendered view, the sign on
cost rows is the first thing to distrust.

When reading results:

- **Blank is not zero.** A line can be empty because its channel never carries it,
  because a data set was excluded on purpose, or because the version isn't loaded for
  that period. Say which. Don't report an empty cell as "0, on budget".
- **Exclude subtotals from rankings.** A "largest cost overrun" over a set that
  includes `Cost of Doing Business` and its three children will crown the total.
- **Decide what "worst" means and say it.** The worst by percentage and the worst by
  dollars were different stores in testing. Both readings are defensible. An answer
  that doesn't say which one it used is half an answer.

## Step 5. Turn codes into names

Users ask for "the Northside store", the cube holds `ST1001`. Read names from the attribute cube,
not from the model's memory:

```mdx
SELECT {[}ElementAttributes_<dim>].[}ElementAttributes_<dim>].[<name attr>]} ON COLUMNS,
       {TM1SUBSETTOSET([<dim>].[<dim>], '<subset>')} ON ROWS
FROM [}ElementAttributes_<dim>]
```

An `Alias` attribute also works inside MDX, so `[Northside VIC]` resolves to the coded
member. Two catches:

- `DIMENSION PROPERTIES` and alias display only reach clients that ask for them. PAW
  does. `get_saved_view` and TM1py's defaults don't, and print the code. If names must
  appear in every client, put them in a string calculated column, as in
  `references/mdx-patterns.md`.
- `Properties("Alias")` returns an empty string, not the member name, when no alias is
  set. Fall back to `MEMBER_NAME` or rows outside the aliased scope go blank.

If the model's names are labelled as derived or assumed, keep the code next to the
name in the answer so someone who knows the real meaning can catch a wrong one.

## Step 6. Answer

State the slice the number came from: entity, account, version, year, period,
currency. Say what you assumed. Separate what you retrieved from what you inferred.
An explanation such as "costs ran over on a thin margin" is interpretation built on
retrieved figures, so label it that way, and make every figure in it trace to a value
you queried.

When the cube can't answer, say so. "No NZD data is loaded" is a correct answer.
A plausible number for a currency, year or hierarchy that doesn't hold data is worse
than failing a simple lookup.

## Building an agent that queries

Everything above goes into the agent's instructions or, better, into code:

- Put the cube profile from Step 0 in the instructions: sign convention, calendar,
  scope, known-empty areas, broken hierarchies.
- Prefer a Python tool that builds the MDX from validated member names over letting
  the model write MDX freehand. The model picks the question shape. Code picks the
  members and runs the query.
- Tell the agent to call `lookup_potential_members` before any MDX and to read back
  the data explorer's chosen filters before using its numbers.
- Ban `get_saved_view` as a source of numbers. It is fine to show a view.
- Clamp the current-year period in code, and tell the user it was clamped.
- The wxO Python tool runtime has **no browser**. A report tool that printed HTML to
  PDF with headless Chrome worked locally and returned null file URLs in wxO.
  Render PDF and Word natively, for example matplotlib with reportlab, and a .docx
  written as zipped XML.
- `perform_impact_analysis` and `perform_outlier_detection` take a `state` from a
  previous data explorer call, so they inherit that call's member choices. Check the
  state's filters before trusting the analysis.

Then test it with `references/agent-test-set.md` before anyone else uses it.

## Report honestly

Give the member names you resolved and the tool that produced each number. If a
number came from the data explorer, say so and list the filters it chose. If you
clamped a period, excluded subtotals or chose percentage over dollars, say that too.

## Files in this skill

| Path | Contains |
|---|---|
| `references/data-explorer-limits.md` | A worked retrieval test: one question run through the data explorer three ways and through MDX, and what failed |
| `references/mdx-patterns.md` | Tested MDX for variance, prior year, ranking, names, string columns, view-local totals, with the `SOLVE_ORDER` and `NONEMPTY` traps |
| `references/agent-test-set.md` | How to build a tiered regression question set for a PA agent, with the cases that catch the most |
