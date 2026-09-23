---
id: driver-rate-quantity
applies_when: A planned cost or revenue equals a rate multiplied by a volume, and users enter the volume rather than the amount.
---

## Structure

Three cubes, each with a single job:

```
{Module}_Rates            reference, no user input
      |  DB() lookup
      v
{Module}_Detail           input, user enters Quantity and Amount is rule-derived
      |  consolidation (or TI aggregate for a different grain)
      v
{Module}_Summary          reporting, read-only
```

The rates cube is separate because rates change on a different cadence than volumes,
are usually maintained by different people, and often carry a different grain (a rate
may apply per region where volume is entered per cost centre).

Measure dimension on `{Module}_Detail`:

| Measure | Kind |
|---|---|
| `Rate` | rule_derived, looked up from the rates cube |
| `Quantity` | input |
| `Amount` | rule_derived, never entered |

## Rules

On `{Module}_Detail`:

```
SKIPCHECK;

[{Measure}:'Rate'] = N:
  DB( '{Module}_Rates', !{RateDim1}, !{RateDim2}, 'Rate' );

[{Measure}:'Amount'] = N:
  [{Measure}:'Rate'] * [{Measure}:'Quantity'];

FEEDERS;
```

Both rules are `N:` scoped. `Amount` at a consolidated level must be the sum of its
children, so leave that to natural consolidation. Making `Amount` a `C:` rule
recalculates rate times quantity on aggregated values, which is wrong whenever the
rate varies across the children being aggregated. This is the single most common
error in this pattern.

## Feeders

```
FEEDERS;
[{Measure}:'Quantity'] => [{Measure}:'Amount'];
```

Feed from **Quantity**, not Rate. Rates are typically populated for every valid
combination; quantities are entered for comparatively few. Feeding from Rate marks
every rate-bearing cell as potentially populated and overfeeds the cube. See
`../references/rules-and-feeders.md` §3.

The cross-cube feeder, in `{Module}_Rates`:

```
FEEDERS;
['Rate'] => DB( '{Module}_Detail', !{RateDim1}, !{RateDim2}, 'Rate' );
```

Required because `Rate` on the detail cube is itself rule-derived from another cube.
Missing this is why `Rate` reads correctly in a single cell but disappears from
consolidations.

## Failure modes

| Symptom | Cause |
|---|---|
| Total `Amount` is zero, leaves are correct | `Amount` not fed, or SKIPCHECK present without FEEDERS |
| Total `Amount` ≠ sum of children | `Amount` rule scoped `C:` or unqualified |
| `Rate` shows in a cell but not in totals | Missing cross-cube feeder from the rates cube |
| Memory grows far beyond expectation | Fed from `Rate` instead of `Quantity` |
| A user's typed `Amount` is overwritten | `Amount` not protected, set `protected: true` |
| Rates load wipes entered quantities | Load process clears the whole cube rather than a rate-scoped view |
