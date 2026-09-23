# Extending the check registry

`checks.yaml` is the modelling standard in machine-readable form. Both
`pa-model-design` (as a self-check) and `pa-model-review` (as verification) read it,
which is what stops the two skills from drifting apart.

## Adding a check

Append an entry. Do not edit either SKILL.md. They read this file, they do not
enumerate it.

```yaml
  - id: <AREA-nnn>          # DIM CUB RUL FED TI SEC NAM, or a new area prefix
    severity: critical | warning | info
    phase: design | build | both
    applies_to: dimension | cube | rule | feeder | process | security | naming
    title: <what good looks like, stated positively>
    detect: <the observable condition that means it failed>
    fix: <the action, and the consequence of not taking it>
    config_ref: <conventions key>   # optional
```

## Guidance

- **`title` states the good state, `detect` states the failure.** "Every leaf rule has
  a feeder" reads as a standard; "missing feeder" reads as an error message.
- **`detect` must be observable.** If nobody can tell whether it fired, it is advice,
  not a check.
- **`fix` says what it costs to ignore.** A finding without a consequence gets waived.
- **`config_ref` makes a check tunable rather than absolute.** Anything a project might
  legitimately do differently should point at a conventions key. That is what keeps a
  project from having to fork the registry.
- **Severity is about consequence, not confidence.** `critical` = wrong numbers,
  data loss, or a leaked secret. `warning` = cost, performance, or maintainability.
  `info` = worth a look.

Which severities block sign-off comes from `review.fail_on` and `review.warn_on`, not
from anything written here.

## Project-local checks

A project can add `checks.local.yaml` beside this file. The review skill reads both
and merges, with local entries overriding registry entries of the same `id`. Use this
for organisation-specific standards instead of editing `checks.yaml`, so the registry
stays upgradable.
