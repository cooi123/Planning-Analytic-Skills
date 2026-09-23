---
name: pa-model-design
description: >-
  Design an IBM Planning Analytics (TM1) model, covering cube inventory, dimensions
  and hierarchies, rules and feeder architecture, TurboIntegrator processes, views,
  and build sequencing, then emit a design spec that the build and review skills
  consume. Use for "design a TM1 model", "what cubes do I need", "design a
  budget/forecast/planning model", "how should I structure this cube", "design
  dimensions for", "rules architecture", "feeder strategy", "TI process design",
  "driver-based model", "rate times quantity", "model design document", or when
  reviewing the architecture of an existing PA/TM1 model before it is built.
user-invocable: true
---

# PA model design

Produce a **design spec** for a Planning Analytics model. Design only. This skill
never writes to a server. `pa-model-build` implements the spec, and
`pa-model-review` verifies what was built against it.

## Step 0. Load conventions (always first)

Read the project conventions file before anything else. Search in order and stop at
the first hit:

1. `./pa-conventions.yaml`
2. `./config/pa-conventions.yaml`
3. `../config/pa-conventions.yaml`

**The file is authoritative.** Never invent a naming scheme, version target,
dimension-order policy, or threshold that the file already specifies.

If no file is found, use `config/pa-conventions.example.yaml` as the default set,
state in one line which defaults you adopted, and offer to write a project copy.
Do not silently proceed on defaults.

Throughout this skill, `{{config.x.y}}` means "read this from the conventions file".

## Step 1. Establish the decision inputs

Do not start drawing cubes. Get these on the record first, asking only for what is
missing and cannot be inferred from the request:

| Input | Why it changes the design |
|---|---|
| Planning question the model answers | Determines cube count and grain |
| Grain of input (who types what, at what level) | Determines leaf level of every dimension |
| Grain of reporting | Determines whether a separate reporting cube is justified |
| Data sources and load cadence | Determines TI process inventory |
| Versions / scenarios in scope | Usually a dimension, occasionally a cube split |
| Expected member counts per dimension | Drives sparsity and dimension order |
| Who may see and write what | Determines security and whether cell security is needed |

Record any assumption you had to make. Assumptions go in the spec, not in your head.

## Step 2. Select patterns

List the files in `patterns/` and read the ones whose `applies_when` matches the
problem. Do not work from memory of what patterns exist. The directory is the
registry, and it is meant to grow.

Each pattern file declares `applies_when`, `structure`, `rules`, `feeders`, and
`failure_modes`. If two patterns conflict, prefer the more specific `applies_when`
and say why in the spec.

If nothing matches, design from `references/dimensional-modelling.md` and add a new
pattern file. See `patterns/README.md` for the contract.

## Step 3. Design, in dependency order

Work in this order. Later steps depend on earlier ones, so do not jump ahead.

1. **Dimensions.** Leaf grain, hierarchies, element types, attributes.
   See `references/dimensional-modelling.md`.
2. **Cube inventory.** One cube per coherent grain. Apply
   `{{config.modelling.max_dimensions_per_cube}}`; a cube that exceeds it usually
   has two grains fused together.
3. **Dimension order.** Apply `{{config.modelling.dimension_order_policy}}`.
   Under `hourglass`, order smallest-sparse, largest-sparse, smallest-dense, then
   largest-dense. Under `manual`, record the order given and offer no advice.
4. **Rules and feeders.** Design them together, never separately. Every rule that
   derives a leaf cell gets its feeder designed in the same breath.
   See `references/rules-and-feeders.md`.
5. **TI processes.** One process per job, tab-correct.
   See `references/ti-processes.md`.
6. **Views and security.** Input views, reporting views, who writes where.
7. **Build sequence.** Dimensions, cubes, rules, TI, chores, then views, with the
   checkpoints at which `pa-model-review` should run.

## Step 4. Self-check before emitting

Run every applicable check in `../pa-model-review/checks/checks.yaml` against your own
design. A design that would fail review must not be emitted as final. Fix it, or
record the deviation with a justification in the spec's `deviations` section.

The review checks are the design standard, held in one place so design and review
cannot drift apart.

## Step 5. Emit the spec

Write `design/<module>.spec.yaml` using `references/design-spec-template.md`. This
file is a contract, not prose.

- `pa-model-build` reads it to know what to create.
- `pa-model-review` reads it to know what "correct" means for conformance mode.

Also produce a human-readable summary in chat: the cube inventory table, the rules
and feeder architecture, the build sequence, and every assumption and deviation.
Write the long-form design document only if asked.

## Hard constraints

- **Never hard-code** a server, database, cube, dimension, or element name that came
  from an example rather than from the user or the conventions file.
- **Never ask for credentials.** Connections belong to the MCP session or environment
  variables.
- **Never pin a PA version** in generated content or doc links. Build links as
  `{{config.platform.docs_base}}/{{config.platform.pa_version}}`.
- **Never design a feeder you cannot justify.** An unjustifiable feeder is
  overfeeding, and overfeeding costs memory permanently.
- Flag any design element that depends on `{{config.platform.edition}}`. On-prem and
  SaaS differ. See `references/platform-matrix.md`.

## Files in this skill

| Path | Contains |
|---|---|
| `references/dimensional-modelling.md` | Grain, hierarchies, element types, sparsity, dimension order |
| `references/rules-and-feeders.md` | Rule scoping, SKIPCHECK/FEEDSTRINGS, feeder design and overfeeding |
| `references/ti-processes.md` | Tab semantics, variable types, parameters, error handling |
| `references/platform-matrix.md` | What differs between on-prem and SaaS |
| `references/design-spec-template.md` | The spec contract emitted by Step 5 |
| `patterns/` | Extensible pattern registry. Read the directory, do not assume |
