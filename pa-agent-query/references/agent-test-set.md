# Regression question set for a PA agent

Build this before anyone uses the agent, and rerun it after every change to the
agent's instructions, its tools, the model, or the PA MCP version.

## Shape

Five tiers, each with an expected answer you computed yourself by MDX. Write the
expected value and the exact slice it came from, so a failing answer can be traced.

| Tier | Tests | Example shape | What a failure looks like |
|---|---|---|---|
| 1. Single-cell retrieval | Picking the right slice | "What were <store>'s sales for FY2025?" | Wrong period member, wrong level, wrong account |
| 2. Variance and ranking | Computing what the cube doesn't store | "Which store had the worst sales variance to budget?" | Zeros, a non-answer, or no statement of % vs dollars |
| 3. Sign convention | Reading negatives correctly | "Did employee costs come in over or under budget?" | Calling a cost overrun favourable, or "costs fell" |
| 4. Structure | Time, hierarchy, scope | "Show sales by month", "How is this year tracking?" | Month 01 labelled January in a July-start year, full-year Budget against two months of Actual |
| 5. Traps | Knowing when there's nothing | "Show me sales in NZD", "What was the FY2023 result?" | Any plausible number |

## Cases worth including in every set

- **An ambiguous period.** "FY2025 sales" must resolve to the full-year YTD member,
  not a month and not a member that double-counts.
- **A rollup whose code resembles its leaves.** The store total versus one of its
  department leaves. This is the case that produced a confident wrong number.
- **A cost-line variance.** Expected answer stated as "over budget by X,
  unfavourable". A second question asking whether it is favourable checks which tool
  path the agent used, because `get_saved_view` flips the sign.
- **A ranking where % and dollars disagree.** The answer must say which it used.
- **The current, partly closed year.** The correct answer compares YTD to the last
  month with Actual.
- **A prior-year comparison.** Exercises `.PrevMember` or the model's LY member.
- **A drill-down that hits a known data quality issue**, such as a mis-parented leaf.
  The agent should mention it.
- **Blanks by design.** A line one channel never carries, or a data set excluded to
  avoid double counting. Expected answer: empty, with the reason.
- **An out-of-scope currency, year, or a hierarchy known to be broken.** Expected
  answer: no data, or a refusal with the reason.

## Two smoke tests

Run these first after any change. Between them they catch most regressions:

1. The ambiguous-period single cell. Can it pick the right slice?
2. The cost-line variance. Does it understand the sign convention?

## Scoring

Mark each answer on three things, not one:

| | Pass when |
|---|---|
| Number | Matches the expected value to the stated rounding |
| Slice | The agent states the members it used and they match |
| Path | The number came from MDX or raw cellset, not a rendered view or an unchecked data explorer guess |

A right number from the wrong path is a pass that will fail next month. Check the
reasoning trace, not only the reply.

Weight Tier 5 heavily. An agent that invents a figure for a trap question is worse than
one that fails a Tier 1 lookup, because nobody double-checks a confident answer.

Keep every confident wrong answer you ever see as a permanent case, with the wrong
value recorded next to the right one. Those are the cases most likely to come back.
