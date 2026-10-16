---
name: pa-model-scan
description: >-
  Scan a TM1 or Planning Analytics database read-only to inventory cubes, dimensions,
  rules, processes, chores, views and security; map cube-to-cube links from DB() rules,
  feeders, TI reads and writes, and chores; draw a Mermaid architecture diagram; feed
  pa-model-review for a health check, best-practice review or migration analysis. Use
  for "scan my TM1 database", "map my cubes", "how do my cubes connect", "architecture
  diagram of my model", "health check my model", "migration assessment", "inventory
  the model", "dependency map", "lineage between cubes".
user-invocable: true
---

# PA model scan

Scan a TM1 database read-only, map how cubes connect, and produce an inventory and
dependency graph for review. Static analysis only: a name built at run time cannot
be resolved.

## Purpose and limits

This skill reads structure and code from a database and traces data flow between
cubes. It does not run processes, write data, or resolve dynamic references (names
built with string concatenation at run time). Those appear in the graph under
`dynamic_refs` for a human to review.

**Scanning a database you don't own needs its owner's permission.** The scan reads
cube and dimension structure, rules, feeders, process code, chore definitions, views
and security settings.

## Step 1. Scan the database

Run `scan_model.py` to inventory the database. The script connects read-only and
writes `inventory.json`.

```bash
export PA_API_KEY=...        # set by the user, never pasted into chat

python3 -I scripts/scan_model.py \
  --host https://{region}.planninganalytics.saas.ibm.com \
  --tenant {tenantId} \
  --database "{Database}" \
  --key-env PA_API_KEY \
  --out scan/inventory.json
```

**Check warnings:** The scan records any errors it encountered in the `warnings` field. Verify this list is empty before trusting the inventory is complete.

The inventory contains:

| Section | What it holds |
|---|---|
| `schema_version` | Schema version of the inventory format |
| `scanned_at` | Timestamp when the scan was performed |
| `source` | Database name and server_version |
| `cubes` | Name, is_control flag, dimensions list, rules text (or null), last_data_update, last_schema_update, views list |
| `dimensions` | Name, is_control flag, hierarchies with element_count, leaf_count, consolidated_count, string_count, attributes |
| `processes` | Name, is_control flag, parameters, datasource (type, name, view), prolog/metadata/data/epilog code |
| `chores` | Name, active status, start_time, frequency, processes list |
| `security` | Groups list, cell_security_cubes, element_security_dimensions |
| `error_logs` | Count and latest log file names |
| `warnings` | List of warnings encountered during the scan |

## Step 2. Build the graph

Run `build_graph.py` to trace dependencies and produce the architecture diagram.

```bash
python3 -I scripts/build_graph.py scan/inventory.json --out-dir scan
```

This writes:

| File | Contains |
|---|---|
| `dependencies.json` | Nodes, edges, dynamic_refs, observations (isolated cubes, unused dimensions, unscheduled processes, inactive chores) |
| `architecture.mmd` | Mermaid diagram of cube-to-cube data flow |

## Step 3. Read the outputs

### Edge types

The graph traces these links in data-flow direction (source → consumer):

| Edge type | Meaning | Traced from |
|---|---|---|
| `rule_reads` | Cube X → Cube Y: DB('X', ...) in Y's calculation rules | Rules files |
| `feeds` | Cube Y → Cube X: DB('X', ...) in Y's FEEDERS section | FEEDERS sections |
| `ti_source` | Cube → Process: process datasource is TM1CubeView | Process datasource |
| `ti_reads` | Cube → Process: CellGetN/CellGetS reads the cube | Process code |
| `ti_writes` | Process → Cube: CellPutN/CellPutS/CellIncrementN writes to cube | Process code |
| `ti_clears` | Process → Cube: ViewZeroOut/CubeClearData clears the cube | Process code |
| `calls` | Process → Process: ExecuteProcess/RunProcess calls another process | Process code |
| `runs` | Chore → Process: chore task list | Chore definitions |
| `shares_dimension` | Cube → Cube: both cubes share ≥1 dimension | Cube structure |

**Data flow vs structure:** All edge types except `shares_dimension` show data movement. `shares_dimension` shows structural relationship only; it does not mean data flows between the cubes.

### Observations

The graph lists these conditions for review in the `observations` section of `dependencies.json`:

| Observation | What it suggests | Check before calling it a finding |
|---|---|---|
| `isolated_cubes` | Cube has no rule, feeder or TI link to any other cube | May be intentional: an input cube or a reporting cube. Or it may be dead |
| `unused_dimensions` | Dimension is used by no cube | May be under construction, or retired but not deleted |
| `unscheduled_processes` | Process is in no chore and called by no other process | May be ad-hoc or retired. Or it should be scheduled |
| `inactive_chores` | Chore is marked inactive | May be seasonal or retired. Verify the schedule reflects reality |

An observation is a candidate for review, not automatically a defect.

**Dynamic references:** Names built at run time (e.g., string concatenation in process code) cannot be resolved by static analysis. These appear in the top-level `dynamic_refs` list in `dependencies.json`, not in observations. List the possible targets in the design spec for a human to verify.

## Step 4. Hand to review

Run `pa-model-review` in Health check mode with the inventory and graph as evidence.
The review skill will verify each candidate against the model and write a report.

See `../pa-model-review/SKILL.md` for the Health check mode workflow.

## Large models

Do not paste `inventory.json` into context if it is large. Query it with small
scripts per cube or per check:

```bash
# List cubes with rules
python3 -c "import json; d=json.load(open('scan/inventory.json')); \
  print('\\n'.join([c['name'] for c in d['cubes'] if not c['is_control'] and c.get('rules')]))"

# Count processes by data source type
python3 -c "import json, collections; d=json.load(open('scan/inventory.json')); \
  print(collections.Counter((p['datasource'] or {}).get('type') for p in d['processes']))"

# Find cubes with no views
jq -r '.cubes[] | select(.is_control|not) | select((.views|length)==0) | .name' scan/inventory.json
```

## Hard constraints

- Read-only. Never write to the database.
- Never print the API key or any credentials.
- Never claim a dynamic reference resolves to a specific cube. List it as
  unresolved and note the possible targets for a human to verify.
- Scanning a database you don't own requires the owner's permission.
