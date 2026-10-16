# Views and calculated members

Version-neutral. Verify syntax against
`{{config.platform.docs_base}}/{{config.platform.pa_version}}`.

Where a calculation lives decides who can see it. That matters more now that AI agents
query cubes, because an agent's natural-language tool reads the same dimension members
an Excel user drags into a view, and nothing else.

## 1. Where to put variance

| | Members in `Version` plus rules | MDX calculated members in saved views |
|---|---|---|
| Dimension changes | Required | None |
| Rules and feeders | Required | None |
| In saved views | Yes | Yes |
| Ad-hoc PAW and PAfE users | Yes | **No** |
| The PA MCP data explorer and agents using it | Yes | **No** |
| Other cubes via `DB()` | Yes | No |

The MDX route is the right call when dimensions are frozen, for example SAP-sourced
dimensions owned by another team. It costs nothing to maintain. Record the trade-off
in the spec, because it is invisible later: an analyst who builds their own view sees
`Actual`, `Budget`, `Forecast` and nothing else, and an agent asked "which store
missed budget worst" through the data explorer can't answer at all. An agent can still
get variance by running MDX through `execute_mdx_and_get_view`. See
`../../pa-agent-query/SKILL.md`.

If self-service or agent variance through the data explorer is a requirement, put
variance in the dimension with rules.

## 2. Sign convention

Read it from the weights. Don't choose it.

When every weight on the account dimension is +1, costs **must** be stored negative,
or a rollup like `Contribution = Gross Profit + Cost of Doing Business` adds cost to
revenue. Then `Actual - Budget` is already favourable-positive on every line, and the
variance % needs `ABS()` of the base to keep that true. No `Variance Sign` attribute and
no per-line inversion are needed.

When cost branches carry -1 weights and costs are stored positive, the reverse holds
and variance needs a per-line sign attribute.

Confirm the convention against a loaded cost line before building views, and write it
in the spec. Every agent instruction and every variance formula depends on it.

## 3. `SOLVE_ORDER`

Two calculated members on different axes meet in one cell, and the higher
`SOLVE_ORDER` evaluates last. Give ratios the highest order and anything that sums
the lowest. A view-local site total that outranked `Act vs Bud %` summed three leaves'
percentages and reported -10.6% for a site that was really -3.5%. String members need
the same treatment: a name column evaluated inside a sum concatenates the names.

## 4. String calculated members and suppression

A string calculated column, such as a description pulled from an alias, is the only
way to show a display name in every client. `DIMENSION PROPERTIES` and alias display
reach only clients that request member properties. PAW does. The MCP `get_saved_view`
renderer and TM1py's defaults don't.

A string cell is never empty, so `NON EMPTY` stops suppressing once one is on the
axis. Use `NONEMPTY(<set>, {<numeric tuple>})` and filter on numeric measures only.
`Properties("Alias")` returns `""` when no alias is set, so fall back to
`MEMBER_NAME`. Tested templates are in
`../../pa-agent-query/references/mdx-patterns.md`.

## 5. Calculated members that stand in for missing consolidations

When a dimension lacks a rollup, for example three sibling leaves that make one
warehouse site, a `WITH MEMBER` sum fills the gap without changing the dimension.
These members are view-local. They don't appear in the member tree, the subset
editor, or any other view, and an agent can't find them by name. Record each one in
the spec's view section, and propose the real consolidation as follow-up work.

A related trap: a column labelled as a total isn't necessarily the parent of the
columns beside it. If `Total Division` hangs off a different hierarchy from the three
channel rollups next to it, they may foot today and stop footing after a hierarchy
change. Say so in the view's notes.

## 6. Subsets

- When dimensions are frozen, static subsets are enough and avoid MDX dialect risk.
  Use dynamic MDX subsets when membership will change.
- Hold members in hierarchy order, depth-first, so P&L subsets read top-down. Sort by
  name or hierarchy, never by element index: a member added later carries a late
  index and lands out of sequence.
- Give reporting subsets consolidations only when leaves are bare codes. Keep one
  loaded-leaves subset for drill and audit.
- Build a **loaded-scope subset** for each large dimension, such as all loaded profit
  centres or all loaded accounts. Agents and analysts both need a way to narrow
  10,000 members to the few hundred with data.
- Keep known-broken members, such as a rolling-period hierarchy with missing
  children, out of every subset.

## 7. Blank cells that mean something

In a channel-by-line view, a blank shows which channel owns a line. Store costs are
store-only, marketing sits at admin. Turn off suppression on views where the gaps are
the information, and say so in the view's notes, or a reader reports them as missing
data.

## 8. Agent readiness checklist

If an AI agent will query the cube, the design also needs:

- A display-name attribute on every dimension users will name: an `Alias` for unique
  names, a `String` attribute for descriptions that can repeat.
- Loaded-scope subsets on the large dimensions.
- The sign convention, fiscal calendar, data scope and known defects written down
  where the agent's instructions can quote them.
- A decision on where variance lives, per section 1, made knowing what it means for
  the data explorer.
