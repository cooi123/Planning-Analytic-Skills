# TurboIntegrator behaviour tested on v12

Observed by running processes against a PA as a Service database, TM1 server
**v12.6.3**, on 2026-10-16. Each item below was run, not read from documentation.
Re-test after a server upgrade; behaviour and message text can change.

The checks were prompted by the Bedrock/Cubewise TI white paper (2011, v9/v10 era).
Where the result differs from that paper, the row says so.

Everything here was run as an inline process through
`ExecuteProcessWithReturn?$expand=ErrorLogFile`, so no process object was left on
the server. Read `ProcessExecuteStatusCode` from the response and the log from
`ErrorLogFiles('<Filename>')/Content`.

## 1. How a process ends

| How it ends | `ProcessExecuteStatusCode` | Code a calling process gets from `ExecuteProcess` | Epilog runs? |
|---|---|---|---|
| Runs to the end | `CompletedSuccessfully` | `0` (`ProcessExitNormal()`) | Yes |
| `ProcessBreak` in Prolog | `CompletedSuccessfully` | not tested | **Yes** |
| `ProcessQuit` | `QuitCalled` | `9` (`ProcessExitByQuit()`) | **No** |
| `ProcessError` | `Aborted` | `12` (`ProcessExitSeriousError()`) | **No** |
| Data error, process carries on (see section 2) | `HasMinorErrors` | not observed (`ProcessExitMinorError()` is 7) | Yes |

What follows from this:

- `ProcessQuit` is **not** an error status. The 2011 paper says it "terminates the
  process with an error status". On v12 it ends as `QuitCalled`, a distinct status
  that is neither success nor `Aborted`. A caller sees code 9, not 0 and not 12.
- Use `ProcessError` when a calling process or chore must treat the stop as a
  failure. Use `ProcessQuit` only when stopping is a normal outcome and a
  caller checking for `Aborted` should not see a failure.
- Whether a chore halts, continues or flags a process that ends `QuitCalled` was
  **not tested**. Don't promise either.
- **Cleanup that must always happen cannot live only in the Epilog.** After
  `ProcessQuit` or `ProcessError` the Epilog does not run. Neither a "restore
  setting" step nor a completion log line in Epilog will execute on a validation
  failure or fatal error.
- A parent whose children had quit and errored itself ended `HasMinorErrors`, not
  `Aborted`. Check each child's returned code if the parent must stop.

## 2. Error text and status by situation

The log is JSON lines; the useful lines have `"level":"error"`.

| Situation | Status | Message |
|---|---|---|
| `CellPutN` to an element that doesn't exist | `HasMinorErrors` | `Invalid key: Dimension Name: '<dim>', Element Name (Key): '<elem>'` |
| `CellPutN` to a consolidated cell | `HasMinorErrors` | `Cell type is consolidated` |
| `CellPutN` to a rule-calculated cell | `HasMinorErrors` | `Rule applies to cell` |
| `CellPutN` to a cube that doesn't exist | `Aborted` | `Cube '<cube>' Not Found` |
| `CellPutN` or `CellGetN` with the wrong number of coordinates | `Aborted` | `Wrong Number of Dimension Elements.` |
| `SubsetElementInsert` with an element not in the dimension | `Aborted` | `Element '<elem>' not found in dimension '<dim>'` |
| `SubsetCreate` on a dimension that doesn't exist | `Aborted` | `Dimension '<dim>' not found` |
| `DimensionCreate` for a name that already exists | `Aborted` | `Dimension creation fails for dimension '<dim>'.` |
| `ExecuteProcess` of a process that doesn't exist | `Aborted` | `No such process name: '<name>'` |
| Expression with nothing after an operator | `Aborted` | `Syntax error on or before: ; invalid operator` |
| Statement missing its closing `;` | `Aborted` | `Syntax error on or before: (end of line) missing semicolon` |
| A function name the server doesn't know | `Aborted` | `Syntax error on or before: ('...',0); equal sign not found` |
| `AttrPutS` on an element inserted earlier in the same Prolog | `HasMinorErrors` | `Element '<elem>' not found in dimension '<dim>'` |

Pattern: **a bad value is a minor error and the run continues; a bad object or a
bad statement aborts.** A minor error is easy to miss, so a process that writes
data must count rejected writes and report them (`TI-006`).

"Equal sign not found" is how v12 reports a function name it doesn't recognise: the
parser reads the unknown name as a variable being assigned. Check the function name
exists on this version before debugging the arguments.

## 3. Dimension structure changes

- An element inserted in a process is **not visible to later statements in the
  same Prolog**. `DimensionElementInsert` then `AttrPutS` on that element, in one
  Prolog, fails for every element. Insert in one pass and put attributes in a
  later pass. This was tested in Prolog only; behaviour across the Metadata and
  Data tabs of one process was not tested.
- **Rebuilding a dimension loses data silently.** Running
  `DimensionDeleteAllElements` and re-inserting only some elements leaves the
  re-inserted ones with their data. The dropped elements are gone, and
  re-adding one afterwards does **not** bring its data back. The process ended
  `CompletedSuccessfully` with no message. The Maps-step "Recreate" option is
  the same idea; that option itself was not run, only the TI function. Use
  "Update" (`TI-010`).
- A failed `SubsetElementInsert` after `SubsetCreate` did **not** leave an empty
  subset behind on v12. The 2011 paper describes one being left. Validating
  inputs before creating anything is still right, but don't rely on cleanup of
  half-built objects either way.

## 4. Loading and writing

- `CellIncrementN` run twice on a cell gave 10 where `CellPutN` run twice gave 5.
  An accumulating load doubles on re-run unless the slice is cleared first
  (`TI-005`).
- **Cube logging can't be switched from TI here.** `CubeSetLogChanges` and
  `CubeGetLogChanges` both fail to compile (see the unknown-function message in
  section 2). The cube also has no `LogChanges` property over REST. The paper's
  "log off, load, log back on" pattern is not available on this version.
  (`TI-011`)
- `AsciiOutput('name.txt', ...)` with a relative name succeeds and writes the file
  to the root of the database's `Files` area. Delete debug files you create. For
  a debug trail, `LogOutput` goes to the process log with no stray file.
- The paper's `pDebug` dry-run idea (0 normal, 1 normal plus debug output, 2 debug
  output and no updates) is a team convention, not a TM1 feature. It works as
  written; nothing in TM1 enforces it.

## 5. Not tested

Chore reaction to `QuitCalled`; `ProcessBreak` inside the Data tab; Metadata-tab
behaviour of inserts and attributes; ODBC and file data sources
(`data-sources.md` covers those); anything on v11.
