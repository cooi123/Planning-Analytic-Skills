# Writing and running TI processes: a guide

For modellers building a TurboIntegrator (TI) process in Planning Analytics
Workspace. Data sources and external systems are covered in `data-sources.md`. The
design standard is `../../pa-model-design/references/ti-processes.md`.

## 1. What a process is

A TI process loads or maintains data and structure. It has a **data source** and a
**script** in four parts that always run in this order:

| Part | Runs | Typical content |
|---|---|---|
| **Prolog** | Once, before the source is read | Check parameters, build temporary views, clear the target slice |
| **Metadata** | Once per source row | Add elements to dimensions |
| **Data** | Once per source row | Write values to cells |
| **Epilog** | Once, after the last row | Clean up, log counts, call the next process |

Without a data source, only Prolog and Epilog run.

**TI and rules work together.** TI writes the **input** cells, and rules calculate
the rest on read. TI can't write into a cell a rule covers. Feeders fire as TI
writes, just as they do when someone types a value.

## 2. Create a process in PAW

You need the modeler or administrator role.

1. Open a **Modeling workbench** (Data and Models).
2. In the database tree, expand the database, then **Processes**.
3. Create a new process, or open an existing one, from that node. The exact menu
   wording isn't confirmed here; check what your PAW release shows.

## 3. Define the data source

On the process editor's **Data Source** tab, open the **Data source** menu and
choose **File**, **Location**, **Database connection**, **Cube** or **Dimension
set**. Then:

1. Pick or upload the file, enter the query, or choose the cube and view.
2. **Preview** to see the rows.
3. **Set variables**: give each column a meaningful name (letters, numbers,
   underscore; start with a letter) and the right type, **Numeric** or **String**.
4. **Save**.

`data-sources.md` has per-type details: what the File type accepts, Location paths
versus URLs, and the ODBC Data Connector on TM1 v12.

## 4. Write the script

The **Script** tab has links to **Prolog**, **Metadata**, **Data** and **Epilog** so
you can jump between them.

- **Ctrl+Space** auto-completes functions, cubes, dimensions and variables.
- Syntax errors show as an **error symbol next to the line number**. Clear them all
  before saving.

A small load, by part:

```
# Prolog
IF( CubeExists( pCube ) = 0 );
  LogOutput( 'ERROR', 'Cube not found: ' | pCube );
  ProcessError;
ENDIF;

# Metadata
IF( DimensionElementExists( 'Product', vProduct ) = 0 );
  DimensionElementInsert( 'Product', '', vProduct, 'N' );
ENDIF;

# Data
CellPutN( vUnits, pCube, pVersion, vPeriod, vProduct, 'Units' );

# Epilog
LogOutput( 'INFO', 'Load finished for ' | pCube );
```

Good habits:

- **Parameters for anything that changes** (cube, version, year, file, DSN), so the
  same process runs in dev and prod unchanged.
- **Structure in Metadata, values in Data.** Writing a value for an element created
  in the same Data pass fails intermittently.
- **Clear before you load,** and clear only the slice the load owns, so a re-run
  gives the same result.
- **Log the counts** in Epilog: rows read, written and rejected.

## 5. Run and check

1. Run the process from the editor and supply its parameters.
2. Check the result. A success message alone isn't proof: open the target view and
   compare a total with the source.
3. If it reports errors, open the process error log. Each rejected row is listed
   with the reason.

AI assistants on the PA MCP endpoint can do the same:

- `create_tm1_process` / `update_tm1_process` create or change the process.
- `execute_tm1_processes_asynchronously` runs it.
- `get_tm1_server_process_status` and
  `get_tm1_server_process_execution_error_logs` check the run.

The `pa-ti` skill does this only when asked explicitly.

## 6. Schedule it

Once a process is proven, add it to a **chore** in the Modeling workbench to run on
a schedule. Chain related processes (clear, load, transform) in one chore, in
order. A scheduled run uses the chore's account, so give that account only the
rights the load needs.

## 7. Troubleshooting

| You see | Look at |
|---|---|
| Ran, nothing changed | No data source (Metadata and Data skipped), or the source returned no rows |
| Rejected rows: cell not updateable | The target is rule-calculated or consolidated. Load the input elements |
| Numbers arrive as 0 | Variable typed String, or separators or currency signs in the text |
| Totals doubled after a re-run | No clear in Prolog, or `CellIncrementN` used |
| Works in dev, not prod | A hard-coded name or path |
| ODBC errors on PA as a Service | ODBC Data Connector not installed or reachable, or wrong connector URL or credentials |
