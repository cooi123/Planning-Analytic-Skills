---
id: time-phasing
applies_when: An annual or periodic total is entered once and must be spread across time periods by a profile, rather than typed period by period.
---

## Structure

```
{Module}_Profile          named spread profiles: seasonal, straight-line, custom
{Module}_Plan             annual input plus the phased result
```

Profiles live in their own cube keyed by a profile name and period, so a profile is
defined once and reused. The profile applied to a given plan line is a **member
attribute** on the planning dimension, not a literal in the rule. See
`../references/dimensional-modelling.md` §7.

## Rules

On `{Module}_Plan`:

```
SKIPCHECK;

[{Measure}:'Phased'] = N:
  DB( '{Module}_Profile',
      ATTRS( '{Module}_{Entity}', !{Module}_{Entity}, 'SpreadProfile' ),
      !{Period}, 'Weight' )
  * DB( '{Module}_Plan', !{Module}_{Entity}, '{AnnualMember}', 'Annual' );

FEEDERS;
```

The `ATTRS` lookup is what keeps this extensible. Adding a new profile means adding
profile data and setting an attribute. The rule never changes. A rule containing
`IF( !{Entity} @= 'Marketing', ... )` is this pattern done wrong; it needs editing
every time the business adds a line.

Weights should sum to 1.0 per profile. Validate that in the load process, not in a
rule. It is a data quality check that belongs where the data arrives.

## Feeders

```
FEEDERS;
[{Measure}:'Annual'] => [{Measure}:'Phased'];
```

Feed from the annual input: it is entered for comparatively few combinations, while
profile weights exist for every period of every profile. Feeding from the profile
cube fans out across the entire period dimension for every entity.

This feeder crosses the period dimension, since `Annual` sits on one period member
and `Phased` on many, so it must not be conditioned on the period.

## Failure modes

| Symptom | Cause |
|---|---|
| Phased values sum to more or less than the annual | Profile weights do not sum to 1.0 |
| Only one period shows a phased value | Feeder conditioned on the source period member |
| Phased is zero for a new entity | `SpreadProfile` attribute unset. Default it on load |
| Rule breaks when a profile is renamed | Profile referenced by literal rather than attribute |
| Annual total double-counts | `{AnnualMember}` included in the period consolidation |
