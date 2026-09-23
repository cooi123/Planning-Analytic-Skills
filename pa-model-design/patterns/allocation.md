---
id: allocation
applies_when: A pooled cost must be distributed to receivers in proportion to a driver, rather than entered directly against each receiver.
conflicts_with: [driver-rate-quantity]
---

## Structure

```
{Module}_Pool             the cost to distribute, entered or loaded at pool level
{Module}_Driver           the basis: headcount, floor area, revenue share
{Module}_Allocated        result, read-only and rule-derived
```

Keep the driver in its own cube. Drivers are reused across several allocations and
maintained on their own cadence; embedding one in the pool cube guarantees it gets
duplicated the second time someone needs it.

Store the **raw driver** (headcount), not the percentage. Percentages computed by rule
always sum to 100%; percentages entered by hand drift, and nobody notices until a
reconciliation fails.

## Rules

On `{Module}_Allocated`:

```
SKIPCHECK;

[{Measure}:'DriverShare'] = N:
  DB( '{Module}_Driver', !{Receiver}, !{Period}, 'Driver' )
  \ DB( '{Module}_Driver', '{AllReceivers}', !{Period}, 'Driver' );

[{Measure}:'Allocated'] = N:
  [{Measure}:'DriverShare']
  * DB( '{Module}_Pool', !{Pool}, !{Period}, 'Amount' );

FEEDERS;
```

Use `\` (TM1's safe divide), which returns zero rather than erroring when the
denominator is zero. A period with no driver data is normal, say a new cost centre in
its first month, and `/` turns that normal case into a rules error that blocks the
whole cube.

Both rules stay `N:`. Allocated totals consolidate naturally.

## Feeders

Feed from the pool, in `{Module}_Pool`:

```
FEEDERS;
['Amount'] => DB( '{Module}_Allocated', !{Receiver}, !{Period}, 'Allocated' );
```

Feed from the **pool**, not the driver. The driver is populated for every receiver in
every period; the pool holds values only where there is a cost to spread.
Feeding from the driver fans out across the full receiver set and is the main way this
pattern bloats a model.

The target must qualify every dimension. An unqualified `{Receiver}` feeds the whole
dimension including consolidations.

## Failure modes

| Symptom | Cause |
|---|---|
| Allocated total ≠ pool total | Driver denominator is not the true total of the same receivers |
| Rules error on the cube | `/` used instead of `\` with a zero driver |
| Allocation silently shifts when a receiver is added | Denominator points at a consolidation that now includes the new member. Usually correct, but confirm it is intended |
| Memory bloat | Fed from driver instead of pool |
| Allocated reads zero in totals only | Missing cross-cube feeder from the pool |
