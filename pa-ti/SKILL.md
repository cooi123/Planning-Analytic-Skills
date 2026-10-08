---
name: pa-ti
description: >-
  Write, explain, debug and run IBM Planning Analytics (TM1) TurboIntegrator (TI)
  processes: Prolog, Metadata, Data and Epilog scripts, parameters, data sources
  (files, ODBC databases, cube views, dimension sets, HTTP locations), and loading
  data from external systems such as SAP, Cognos and relational warehouses. Covers
  the PAW process editor, the TM1 v12 ODBC Data Connector, and running processes
  through the PA MCP tools. Use for "write a TI process", "load this CSV into a
  cube", "load data from SQL Server / Snowflake / SAP / Cognos", "ODBC data
  source", "what goes in the Prolog", "my process does nothing", "process errors",
  "clear and reload", "copy data between cubes", "TI won't write to this cell",
  or "schedule a load".
user-invocable: true
---

# PA TurboIntegrator

Write TI processes that load the right data, can be re-run safely, and say what
they did. The design standard is
`../pa-model-design/references/ti-processes.md`: tab discipline, parameters, error
handling, idempotency, one job per process. Apply it, don't restate it.

Read `references/data-sources.md` when choosing or configuring a data source,
especially for external systems. Point the user to
`references/writing-and-running-guide.md` for the PAW click-paths.

## Step 0. Load conventions and get the facts

1. **Conventions.** First hit wins: `./pa-conventions.yaml`,
   `./config/pa-conventions.yaml`, `../config/pa-conventions.yaml`. The `ti:`
   keys (`tab_policy`, `require_parameters`, `require_error_handling`,
   `forbid_hardcoded_object_names`) are authoritative. If no file is found, treat
   them as strict and say so.
2. **TM1 version: v11 or v12.** This decides how files and ODBC work. See
   `references/data-sources.md`. PA as a Service is v12. If you don't know, ask.
3. **Target.** Get the cube and its dimensions **in order** (MCP
   `get_cube_dimensions`), and which elements are inputs. TI can't write into a
   rule-calculated cell.
4. **Source.** What system, how it's reached (file, DSN or connector, view, URL),
   its columns and a few sample rows. Never invent column names or a DSN.
5. **Existing process.** If changing one, read it first: MCP
   `get_tm1_process_details`, or the PAW process editor.

## Step 1. One job per process

Load, clear, transform and copy are separate processes chained by a chore or a
master process (`TI-008`). The exception is creating a dimension together with the
cube that uses it.

## Step 2. Choose and define the data source

| Source | TI type | When |
|---|---|---|
| Delimited text file | File (`CharacterDelimited`) | Exports from any system |
| Relational database | ODBC / Database connection | Warehouses, ERP tables, SAP HANA. On v12, through the ODBC Data Connector |
| TM1 cube | Cube view | Copy, transform or clear between cubes |
| Dimension set | Dimension set (subset) | Loop over elements |
| URL (v12) or path (v11) | Location | Files on a share, or REST/OData endpoints on v12 |
| None | NULL | Prolog/Epilog-only jobs: clears, admin, calling other processes |

For SAP, Cognos and ETL tools, see "External systems" in
`references/data-sources.md`. Some of them push data into TM1 without a TI source
at all.

## Step 3. Write the four procedures

Variables come from the source (set on the Variables step), and parameters from
the process definition. Prefix them so the reader can tell them apart: `v…` for
source variables, `p…` for parameters, `n…`/`s…` for locals.

| Procedure | Put here | Never here |
|---|---|---|
| **Prolog** | Validate parameters (`ProcessError` on failure). Build temporary views and subsets. Clear the target slice. Set the data source in code if it's dynamic | Per-record work |
| **Metadata** | Dimension and hierarchy changes (insert elements, components) | Cell writes (`TI-001`) |
| **Data** | `CellPutN` / `CellPutS`. `ItemReject` for a bad record | Dimension changes |
| **Epilog** | Destroy what Prolog built, log the counts (`TI-006`), call the next process | Anything that needs the source |

Write rules:

- **Names come from parameters or a control cube**, never literals: database,
  cube, file, DSN, version (`TI-002`).
- **Clearing.** Clear only the slice this load owns, through a temporary view built
  in Prolog: `ViewCreateByMDX(…, 1)` then `ViewZeroOut`. Not `CubeClearData`
  (`TI-004`, `TI-005`).
- **Writing.** `CellPutN` replaces. Use `CellIncrementN` only when several source
  rows really must add into one cell.
- **Counting.** Count read, written and rejected rows in Prolog-declared numeric
  variables, and log them in Epilog. A process that writes nothing and reports
  success looks identical to one that worked.
- **Types.** TI has numeric and string only. A source column typed String fails
  arithmetic silently. Fix the type on the Variables step, or convert with
  `NUMBR` / `StringToNumber`.

## Step 4. Self-check

Run every `TI-*` check in `../pa-model-review/checks/checks.yaml`, honouring
`config_ref`. Fix any failure, or state the deviation and why.

## Step 5. Create and run: only when asked

Creating or running a process writes to the server. Do it only on an explicit
request, never in an environment marked `writable: false`, and confirm the
parameters first.

| Route | How |
|---|---|
| PAW process editor | `references/writing-and-running-guide.md` |
| PA MCP tools | `create_tm1_process` / `update_tm1_process`, then `execute_tm1_processes_asynchronously`, `get_tm1_server_process_status`, `get_tm1_server_process_execution_error_logs` |
| Chore | Schedule in the Modeling workbench once the process is proven |

After a run, report its status, the logged counts, and the first errors from the
error log. "It ran" is not a result.

## Debugging

| Symptom | Usual cause |
|---|---|
| Runs, does nothing | No data source, so Metadata and Data never ran. Or the source returned no rows: wrong file, query or view |
| "Cell is calculated by a rule" or rejected writes | Writing into a rule-covered cell. Load the input elements instead |
| Element not found in Data | The element was created in Data instead of Metadata, or the dimension wasn't saved. Insert in Metadata |
| Numbers load as 0 | A numeric column typed String, or a thousands separator or currency sign in the text. Fix the variable type, clean the text, then `NUMBR` |
| Values double on re-run | No clear, or `CellIncrementN` (`TI-005`) |
| Works in dev, fails in prod | A hard-coded name or path (`TI-002`), or a file path that doesn't exist on that server |
| ODBC fails on v12 | No ODBC Data Connector, or a wrong connector URL or credentials. See `data-sources.md` |
| Intermittent failures under load | A shared view or subset reused by concurrent runs (`TI-004`) |

## Output

1. The process: parameters (name, type, default), data source, variables, and the
   four procedures in code blocks, ready to paste.
2. One line per procedure saying what it does.
3. The self-check result.
4. How to run it, and what a good run logs.

## Hard constraints

- Never create, update or run a process unless the user explicitly asks.
- Never ask for database or system credentials. Use the server's configured DSN or
  connector, or a named connection.
- Never hard-code server, database, cube, DSN or file names.
- Report actual run results. Never claim a load succeeded without the counts.
