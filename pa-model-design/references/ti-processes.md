# TurboIntegrator process design

Version-neutral. Verify syntax against
`{{config.platform.docs_base}}/{{config.platform.pa_version}}`.

## 1. Execution model

A process has four procedures, executed in order:

| Tab | Runs | Purpose |
|---|---|---|
| **Prolog** | Once, before the data source opens | Parameter validation, build views and subsets, set up |
| **Metadata** | Once per source record | Dimension and hierarchy maintenance only |
| **Data** | Once per source record | Cell writes (`CellPutN`, `CellPutS`) |
| **Epilog** | Once, after the last record | Teardown, logging, chained process calls |

With no data source, Metadata and Data do not run at all. A process that "does
nothing" when scheduled is usually a Data-tab process with its source unset.

**Variable scope:** variables declared in Prolog are visible in Metadata and Data.
Variables declared in Metadata or Data are visible only within that tab. Declare
anything shared in Prolog.

## 2. Tab discipline

Enforced when `{{config.ti.tab_policy}}` is `strict`:

- Dimension updates belong in **Metadata**, never Data.
- Cell writes belong in **Data**, never Metadata.
- Views and subsets are **created in Prolog and destroyed in Epilog**.

That last point is not stylistic. Reusing a pre-existing named view or subset means
another process or user can modify it underneath you, and two concurrent runs will
corrupt each other. Build a uniquely named temporary one in Prolog, prefixed with
`{{config.naming.reserved_prefixes.scratch}}`, and destroy it in Epilog.

Writing cells in Metadata is the subtler bug: the dimension may not yet contain the
element you are writing to, and the failure is intermittent because it depends on
source record order.

## 3. Variables

TI variables are **Numeric or String only**. There is no Boolean type, so use a
numeric 0/1 and name it so the intent is obvious (`nIsValid`).

Source variables are typed on the Variables tab. A numeric column typed as String will
silently fail arithmetic rather than error.

## 4. Parameters

Required when `{{config.ti.require_parameters}}` is true.

Anything that varies between environments or runs is a parameter: database or server
name, target cube, version, year, file path, clear-before-load switch.

Forbidden when `{{config.ti.forbid_hardcoded_object_names}}` is true: a literal server,
database, cube, or file path in process code. This is what makes a process promotable
from dev to prod without editing. Resolve names from parameters or from a control
cube, never from a literal.

Validate every parameter in Prolog and exit before touching anything:

```
IF( pCube @= '' );
  ItemReject( 'pCube is required' );
ENDIF;
IF( CubeExists( pCube ) = 0 );
  ItemReject( 'Cube not found: ' | pCube );
ENDIF;
```

## 5. Error handling

Required when `{{config.ti.require_error_handling}}` is true.

- Validate inputs in Prolog and reject early, before partial writes occur.
- `ItemReject` skips the record, `ProcessQuit` stops the run. Choose between them.
  A bad record and a bad configuration deserve different outcomes.
- Log to a known location in Epilog: rows read, rows written, rows rejected.
- A process that writes nothing and reports success is indistinguishable from one that
  worked. Always report counts.

## 6. One job per process

Split load, transform, and clear into separate processes and orchestrate with a chore.
A single process that does all three cannot be re-run after a partial failure, which is
exactly when you most need to re-run it.

The exception is object creation: creating a dimension and the cube that uses it should
be **one atomic process**, because a cube referencing a half-built dimension is a worse
state than no cube at all.

## 7. Idempotency

A correctly designed process produces the same result run twice as run once.

- Clear the target scope before loading, using a parameter-controlled view.
- Clear through a view built in Prolog, not a blanket `CubeClearData`, which wipes
  data the process was never responsible for.
- Prefer `CellPutN` over `CellIncrementN` unless accumulation is genuinely intended.

## 8. Design output

For every process, the spec records: name (per `{{config.naming.process}}`), purpose,
parameters with types and defaults, data source, tab-by-tab logic, error handling,
and the chore that schedules it.
