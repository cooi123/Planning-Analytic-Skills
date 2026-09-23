---
name: pa-model-review
description: >-
  Review an IBM Planning Analytics (TM1) model for correctness, either against its
  design spec or on its own where no spec exists, and triage models that return wrong
  numbers. Use for "validate the model", "review this TM1 model", "is the cube built
  correctly", "check these rules", "review this TI process", "check for unfed cells",
  "consolidation is showing zero", "the total doesn't match the parts", "feeder
  trace", "overfeeding", "model handover", "post-build check", "sign off this model",
  or "compare two TM1 models". Covers dimensions, cube structure, rules, SKIPCHECK
  and FEEDERS, TurboIntegrator processes, security, and naming.
user-invocable: true
---

# PA model review

Verify a Planning Analytics model. Read-only. This skill reports, it never repairs.
If asked to fix, hand the findings to `pa-model-design` or `pa-model-build`.

## Step 0. Load conventions and checks

1. Conventions, first hit wins: `./pa-conventions.yaml`, `./config/pa-conventions.yaml`,
   `../config/pa-conventions.yaml`. If absent, use the example defaults and say so.
2. `checks/checks.yaml`, then `checks/checks.local.yaml` if present. Merge, with local
   entries overriding by `id`.

**Never enumerate checks from memory.** The registry is the standard and it is meant to
grow, so read the file every time.

## Step 1. Pick the mode

| Mode | When | Verdict |
|---|---|---|
| **Conformance** | A design spec exists | Does the build match what was designed? |
| **Intrinsic** | No spec | Is this internally consistent and sound? |
| **Triage** | Specific wrong behaviour reported | What is causing it? |

State the mode before reporting. An intrinsic review cannot tell you whether the model
does what the business wanted. It can only tell you the model is not
self-contradictory.
Say so explicitly in the verdict rather than letting it be read as full approval.

## Step 2. Gather evidence

Use whatever the session provides, in this order of preference:

1. **A live connection** (MCP server or configured REST tooling). Read structure,
   rules, processes, and sample values directly.
2. **Supplied artefacts.** Rules files, process exports, spec files.
3. **Description alone.** Possible, but say plainly that the review is limited to
   what was described.

Never ask for credentials, API keys, tenant ids, or passwords. If there is no
connection, review what you have and name the gap.

Use the environment named in `{{config.environments}}`. Never write to an environment
with `writable: false`, including for a read that has side effects.

## Step 3. Run the checks

For each check whose `phase` and `applies_to` match the target, evaluate `detect`.

Apply `config_ref` first: a check pointing at a conventions key that is disabled does
not run, and a check parameterised by a threshold uses the project's value. Reporting a
project's deliberate choice as a defect is how a review loses its audience.

**Verify before reporting.** A check that fires is a candidate, not a finding. Confirm
it against the actual model. Spec-level suspicion plus live contradiction means the
spec is stale, which is itself worth reporting, but as a different finding.

### Conformance mode

Also compare the build to the spec, in both directions:

- Designed but missing.
- Built but not designed, which is often where undocumented fixes hide.
- Present but different: dimension order, rule scope, feeder source, parameters.

A recorded entry under the spec's `deviations` is not a finding. Verify the
justification still holds and note it as accepted.

### Triage mode

Work from symptom to cause:

| Symptom | Check first |
|---|---|
| Consolidation reads zero, leaves are populated | FED-001, FED-002, RUL-001 |
| Total ≠ sum of children | RUL-003, DIM-003 |
| A rule appears to do nothing | RUL-004, a broader rule above it wins |
| String values vanish under zero suppression | RUL-002 |
| Memory far above expectation | FED-003, FED-004, FED-005, FED-006 |
| Values change on re-running a load | TI-005 |
| Load works in dev, fails in prod | TI-002 |
| Numbers change without anyone editing them | CUB-004, or a write to a consolidated cell spreading |

Report the cause, the evidence for it, and the fix. Stop at the first cause that fully
explains the symptom, then note anything else found along the way separately.

## Step 4. Report

Per finding:

```
[<id>] <SEVERITY>. <title>
Object:   <cube / dimension / process / rule area>
Observed: <what is actually there, quoted>
Why:      <the consequence, concretely>
Fix:      <the specific action>
```

Order by severity, then by blast radius. Then give the verdict:

- **SIGN-OFF.** No findings at or above `{{config.review.fail_on}}`.
- **SIGN-OFF WITH FINDINGS.** Nothing blocking, listed items to schedule.
- **BLOCKED.** One or more blocking findings, listed first.
- **INCONCLUSIVE.** Evidence was insufficient. Name exactly what was missing.

In intrinsic mode, qualify the verdict: *structurally sound; intent not assessed.*

## Hard constraints

- Report only what you verified. Mark inference as inference.
- Do not silently correct anything, including in artefacts you were given.
- Do not invent a standard. If no check covers it and it still matters, say so and
  propose a registry entry. See `checks/README.md`.
- No credentials in any output, including quoted evidence. Redact before quoting.
- An empty report is a valid outcome. Do not manufacture findings to look thorough.

## Files in this skill

| Path | Contains |
|---|---|
| `checks/checks.yaml` | The check registry, the standard as data |
| `checks/checks.local.yaml` | Optional project overrides, merged by `id` |
| `checks/README.md` | How to add or tune a check |
| `../pa-model-design/references/` | Background on why each standard exists |
