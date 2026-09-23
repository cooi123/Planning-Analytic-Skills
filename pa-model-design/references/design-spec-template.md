# Design spec contract

`pa-model-design` writes it. `pa-model-build` implements it. `pa-model-review` checks
against it. Keep it machine-readable. Prose belongs in the summary, not here.

Path: `design/<module>.spec.yaml`

```yaml
schema_version: 1
module: <Module>              # feeds every {Module} naming template
conventions_ref: ./pa-conventions.yaml
generated_by: pa-model-design

context:
  planning_question: <what this model answers>
  input_grain: <who types what, at what level>
  reporting_grain: <finest level anyone must see>
  edition: <paas | on-prem>   # copied from conventions at design time

assumptions:                  # every gap you filled yourself
  - id: A1
    statement: <assumption>
    impact_if_wrong: <what would have to change>

deviations:                   # checks knowingly not met, with reasons
  - check_id: <id from checks.yaml>
    reason: <why this design is correct anyway>
    approved_by: <name or "pending">

dimensions:
  - name: <per naming.dimension>
    entity: <Entity>
    leaf_grain: <what one leaf represents>
    estimated_members: <n>            # drives dimension order
    density: <sparse | dense>         # drives dimension order
    hierarchies:
      - name: <hierarchy>
        top_member: <All ...>
        levels: [<level>, ...]
    attributes:
      - name: <Attr>
        type: <alias | string | numeric>
        purpose: <what logic or display depends on it>

cubes:
  - name: <per naming.cube>
    purpose: <one line>
    dimension_order: [<dim>, ...]     # ordered per modelling.dimension_order_policy
    order_rationale: <which goal this order optimises>
    writable: <true | false>
    measures:
      - name: <Measure>
        kind: <input | rule_derived | loaded>
        protected: <true | false>     # true required for rule_derived

rules:
  - cube: <cube>
    target_area: <[...]>
    scope: <N | C | both>
    formula: <expression>
    precedence: <integer, lower evaluates first>
    justification: <required when scope is C or both>
    feeder:
      source_area: <[...]>
      source_cube: <cube>             # differs from cube for cross-cube feeders
      conditional_on: <condition or null>
      estimated_fanout: <n>
      rationale: <why this source, not another operand>
    # or:
    # feeder: none
    # feeder_none_reason: <required when feeder is none>

processes:
  - name: <per naming.process>
    purpose: <one line>
    parameters:
      - name: p<Name>
        type: <numeric | string>
        required: <true | false>
        default: <value or null>
    data_source: <type or none>
    tabs:
      prolog: [<step>, ...]
      metadata: [<step>, ...]
      data: [<step>, ...]
      epilog: [<step>, ...]
    idempotent: <true | false>
    error_handling: <how bad records and bad config are handled>

chores:
  - name: <per naming.chore>
    schedule: <cadence>
    processes: [<process>, ...]

views:
  - name: <per naming.view>
    cube: <cube>
    purpose: <input | reporting>
    rows: [<dim>, ...]
    columns: [<dim>, ...]
    context: {<dim>: <member>, ...}

security:
  - role: <role>
    cube: <cube>
    access: <none | read | write | admin>
    cell_security: <true | false>

build_sequence:
  - phase: <n>
    creates: [<object>, ...]
    depends_on: [<object>, ...]
    review_checkpoint: <true | false>
```

## Field rules

- Every `rule` carries either a `feeder` or a `feeder_none_reason`. No third option.
- `scope: C` or `scope: both` requires `justification`.
- `kind: rule_derived` requires `protected: true` when
  `{{config.rules.protect_calculated_measures}}` is set. Otherwise a user can
  type over a calculated cell.
- `estimated_members` and `density` are mandatory: without them the dimension order
  cannot be checked, and the order is the expensive thing to change later.
- No credentials, hosts, tenants, or regions. Environments resolve from
  `{{config.environments}}`.
