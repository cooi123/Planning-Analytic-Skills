# Migration from TM1 v11 to PA v12

Guide for assessing and preparing a TM1 v11 model for migration to Planning Analytics
v12 (PA as a Service). Based on behaviour tested on TM1 v12.6.3, 2026-10-16.

## Purpose

This reference documents TI functions and patterns that behave differently or fail on
v12, and provides tested replacements. Use it to run a migration analysis: scan the
model with `pa-model-scan`, run the MIG-* checks from `pa-model-review`, and report
readiness.

## How to run a migration analysis

1. **Scan the model** with `pa-model-scan` to inventory processes, rules and chores.
2. **Run MIG-* checks** from `pa-model-review` against the inventory.
3. **Verify each finding** against the actual model code.
4. **Write the report** using `../pa-model-review/references/health-check-report.md`,
   section 7 (Migration readiness).

The verdict is one of:

- **Ready:** No blocking issues, model can migrate as-is.
- **Ready with changes:** Warnings or info findings that need attention but don't
  block migration.
- **Blocked:** One or more critical findings must be fixed before migration.

## Tested facts: what fails or changes on v12

Tested on TM1 v12.6.3, PA as a Service, 2026-10-16. Each item was run, not read from
documentation.

### Functions removed in v12

These TI functions **do not compile** on v12.6.3. A process containing any of them
fails with `Syntax error ... equal sign not found` or `Variable '...' is undefined`,
and the entire process aborts.

| Function | Result on v12.6.3 | Action |
|---|---|---|
| `ExecuteCommand` | Does not compile | Remove or redesign the logic that uses it |
| `CubeSetLogChanges` | Does not compile | Remove or redesign the logic that uses it |
| `CubeGetLogChanges` | Does not compile | Remove or redesign the logic that uses it |
| `SaveDataAll` | Does not compile | Remove or redesign the logic that uses it |
| `CubeSaveData` | Does not compile | Remove or redesign the logic that uses it |
| `SetODBCUnicodeInterface` | Does not compile | Remove or redesign the logic that uses it |
| `ServerShutdown` | Does not compile | Remove or redesign the logic that uses it |
| `ExecuteJavaN` | Does not compile | Remove or redesign the logic that uses it |
| `CubeDataReservationAcquire` | Does not compile | Remove or redesign the logic that uses it |
| `SetChoreVerboseMessages` | Does not compile | Remove or redesign the logic that uses it |

**Impact:** A process containing any of these functions will not run on v12.

**Fix:** Remove the function call and any code that depends on it. For cube logging
(the most common case), remove the log-off, load, log-on pattern and plan load
windows without it. See `../../pa-ti/references/v12-tested-behaviour.md` for detail.

### File system access

On v11, TI processes can read and write files on the server's local file system using
absolute paths (`C:\data\file.csv`) or UNC paths (`\\server\share\file.csv`) (v11 behaviour, not tested here).

On v12, file access is restricted:

- **Relative paths work** and resolve to the database's `Files` area (tested on v12.6.3).
- **Absolute and UNC paths were not tested** on v12. Treat them as a migration risk and test before relying on them.

**Impact:** Processes that read from or write to local file paths may fail on v12.

**Fix:** Move files to the database's `Files` area and reference them by relative
name. Absolute and UNC paths were not tested on v12; test before relying on them.
See `../../pa-ti/references/data-sources.md`.

### ODBC data sources

ODBC functions (`ODBCOpen`, `ODBCOutput`) and ODBC data sources compile on v12. Run-time use requires the **ODBC Data Connector** to be configured per `../../pa-ti/references/data-sources.md`. Run-time behaviour was not tested here.

**Impact:** Processes using ODBC functions or data sources need the connector configured.

**Fix:** Verify the ODBC Data Connector is set up for the target environment. See
`../../pa-ti/references/data-sources.md` for connector configuration.

### Debug and output files

On v11, `ASCIIOutput` and `TextOutput` with a relative file name write to the TM1
data directory (v11 behaviour, not tested here).

On v12, relative file names write to the **root of the database's `Files` area** (tested on v12.6.3).

**Impact:** Debug files land in a different location.

**Fix:** Use relative names for debug files, and clean them up after use. For
diagnostic output, prefer `LogOutput` which writes to the process log with no file.

### Process termination and Epilog

On v12.6.3, `ProcessQuit` and `ProcessError` **do not run the Epilog**.

**Impact:** Cleanup code in the Epilog (destroying temporary views, logging counts)
will not run if the process calls `ProcessQuit` or `ProcessError`.

**Fix:** Put must-run cleanup before the termination call, or in the calling process.
See `../../pa-ti/references/v12-tested-behaviour.md` for detail on process
termination.


## Not tested here

The following were **not tested** and require verification against IBM documentation
before advising:

- **TM1 Web and Perspectives/Excel assets:** Compatibility of saved views, reports
  and Excel add-in workbooks.
- **CAM/LDAP security mapping:** How security groups and users migrate.
- **`}` control cubes:** Differences in control cube structure and behaviour.
- **Chore scheduling limits:** Tenant-level limits on concurrent chores or process
  execution.
- **Java extensions:** Whether any exist on v12, and how they run.
- **REST API differences:** Endpoint changes, authentication, and response formats
  between v11 and v12.

Verify each of these against IBM Planning Analytics documentation for the target v12
version before including them in a migration plan.

## What was tested

All compile tests and behaviour observations were run against a PA as a Service
database, TM1 server v12.6.3, on 2026-10-16. Another database on the same tenant reported v12.6.1, so results can differ by version. Processes were executed through
`ExecuteProcessWithReturn?$expand=ErrorLogFile` over REST.

Compile tests prove only that a function name is recognised by the parser. They do
not prove the function works correctly or that its behaviour matches v11.

See `../../pa-ti/references/v12-tested-behaviour.md` for full test detail.
