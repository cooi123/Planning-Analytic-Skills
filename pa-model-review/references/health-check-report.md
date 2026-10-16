# Health check report template

Fill in this template after running a health check review. Use the glossary at
`../../pa-model-design/references/glossary.md` for consistent wording.

## 1. Summary

| Item | Value |
|---|---|
| Database | `{Database}` |
| Server version | `{version}` |
| Scan date | `{YYYY-MM-DD}` |
| Review mode | Health check |
| Verdict | **{SIGN-OFF / SIGN-OFF WITH FINDINGS / BLOCKED / INCONCLUSIVE}** |

### Scores by area

| Area | Status | Reason |
|---|---|---|
| Structure | {Green / Amber / Red} | {one-line summary} |
| Rules & feeders | {Green / Amber / Red} | {one-line summary} |
| Processes | {Green / Amber / Red} | {one-line summary} |
| Operations | {Green / Amber / Red} | {one-line summary} |
| Security | {Green / Amber / Red} | {one-line summary} |
| Migration readiness | {Green / Amber / Red} | {one-line summary} |

**Scoring rule:** Red if any critical finding in the area, Amber if any warning,
Green otherwise.

## 2. Model map

### Architecture

```mermaid
{paste architecture.mmd content here}
```

### Cube inventory

| Cube | Dimensions (in order) | Rules | SKIPCHECK | Feeders | Views | Last data update |
|---|---|---|---|---|---|---|
| `{CubeName}` | {Dim1, Dim2, ...} | {Yes / No} | {Yes / No} | {Yes / No} | {count} | {YYYY-MM-DD or timestamp} |

## 3. How cubes connect

### Data flow edges

| Source | Target | Link type | Notes |
|---|---|---|---|
| `{SourceCube}` | `{TargetCube}` | {rule_reads / feeds / ti_source / ti_reads / ti_writes / ti_clears / calls / runs} | {brief note if needed} |

### Shared dimensions

| Dimension | Used by cubes |
|---|---|
| `{DimensionName}` | {Cube1, Cube2, ...} |

### Isolated cubes

| Cube | Reason |
|---|---|
| `{CubeName}` | {Intentional input cube / Reporting cube / Under investigation} |

## 4. Findings by severity

### Critical

{If none, state "None."}

```
[{ID}] CRITICAL. {title}
Object:   {cube / dimension / process / rule area}
Observed: {what is actually there, quoted}
Why:      {the consequence, concretely}
Fix:      {the specific action}
```

### Warning

{If none, state "None."}

```
[{ID}] WARNING. {title}
Object:   {cube / dimension / process / rule area}
Observed: {what is actually there, quoted}
Why:      {the consequence, concretely}
Fix:      {the specific action}
```

### Info

{If none, state "None."}

```
[{ID}] INFO. {title}
Object:   {cube / dimension / process / rule area}
Observed: {what is actually there, quoted}
Why:      {the consequence, concretely}
Fix:      {the specific action}
```

## 5. Best-practice deviations

Checks run: DIM-*, CUB-*, RUL-*, FED-*, TI-*, VW-*, SEC-*, NAM-*

{Summarize findings by area. If an area has no findings, state "No deviations found."}

### Dimensions

{List DIM-* findings or state "No deviations found."}

### Cubes

{List CUB-* findings or state "No deviations found."}

### Rules and feeders

{List RUL-* and FED-* findings or state "No deviations found."}

### Processes

{List TI-* findings or state "No deviations found."}

### Views

{List VW-* findings or state "No deviations found."}

### Security

{List SEC-* findings or state "No deviations found."}

### Naming

{List NAM-* findings or state "No deviations found."}

## 6. Operational health

Checks run: HLT-*

{Summarize HLT-* findings. If none, state "No operational issues found."}

| Check | Status | Notes |
|---|---|---|
| Isolated cubes | {Pass / Review} | {brief note} |
| Unused dimensions | {Pass / Review} | {brief note} |
| Unscheduled processes | {Pass / Review} | {brief note} |
| Dynamic references | {Pass / Documented} | {brief note} |
| Process errors | {Pass / Review} | {brief note} |
| Security coverage | {Pass / Review} | {brief note} |
| Stale cubes | {Pass / Review} | {brief note} |
| Inactive chores | {Pass / Review} | {brief note} |

## 7. Migration readiness

Checks run: MIG-*

**Overall status:** {Ready / Ready with changes / Blocked}

{If migration is not in scope, state "Migration analysis not requested." and skip this section.}

### Blocking issues (MIG-* critical)

{List critical MIG-* findings or state "None. Model is ready to migrate."}

### Changes required (MIG-* warning/info)

{List warning/info MIG-* findings or state "None."}

### Migration checklist

| Item | Status | Notes |
|---|---|---|
| No removed TI functions | {Pass / Fail} | {brief note} |
| No local file paths | {Pass / Fail} | {brief note} |
| ODBC sources reviewed | {Pass / Review} | {brief note} |
| Debug files reviewed | {Pass / Review} | {brief note} |
| Cube logging removed | {Pass / N/A} | {brief note} |

## 8. Design improvements

Recommendations linked to findings, ordered by impact and effort.

| Recommendation | Linked findings | Effort | Impact |
|---|---|---|---|
| {Specific action} | {ID-001, ID-002} | {S / M / L} | {High / Medium / Low} |

**Effort scale:** S = hours, M = days, L = weeks or requires design change.

## 9. Evidence and limits

### What was scanned

- Database structure: {count} cubes, {count} dimensions
- Rules: {count} cubes with rules, {count} with SKIPCHECK
- Processes: {count} processes, {count} chores
- Views: {count} views
- Security: {count} cubes with cell or element security

### What was not scanned

{List anything not covered: specific cubes excluded, external data sources not traced, etc.}

### Dynamic references

{List unresolved dynamic references from the graph. State the possible targets for each.}

| Process or rule | Dynamic reference | Possible targets |
|---|---|---|
| `{ProcessName}` | {expression} | {list or "unknown, requires design spec"} |

### Intrinsic-mode caveat

This review assessed the model's internal consistency and adherence to best practices.
It did **not** verify whether the model implements the business requirements correctly.
That requires a conformance review against the design specification.

---

**Report prepared by:** {name}  
**Date:** {YYYY-MM-DD}
