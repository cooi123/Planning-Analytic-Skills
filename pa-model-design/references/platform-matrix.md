# Platform matrix, on-prem vs SaaS

Read `{{config.platform.edition}}` from the conventions file and design to that
target. Flag anything in a design that behaves differently across the two.

| Concern | `on-prem` (PA v11 / TM1 Server) | `paas` (PA v12 / SaaS) |
|---|---|---|
| Server log access | Filesystem | REST API only |
| File-based data sources | Local filesystem paths | Restricted, prefer REST or staged uploads |
| Feeder inspection | Architect / Perspectives UI | REST API |
| Connection identity | Basic auth or CAM | Token-based, short-lived |
| Database naming | TM1 server instance | Tenant-scoped database |
| Process scheduling | Chores on the server | Chores, subject to tenant limits |

Design implications:

- A TI process reading a local file path is **not portable to SaaS**. If the project
  may move, parameterise the source and note the dependency in the spec.
- Anything in the design that depends on reading the server log at run time will not
  survive a move to SaaS.
- Never write a region, tenant id, or host name into a design artefact. Those are
  deployment facts and belong in environment variables. See
  `{{config.environments}}`.

## Tested on v12 (TM1 v12.6.3, 2026-10-16)

Behaviour observed by running it, relevant when `edition` is `paas`. Full detail is
in the tested-behaviour files; re-test after a server upgrade.

| Concern | What was observed | Detail |
|---|---|---|
| Cube logging in TI | `CubeSetLogChanges` and `CubeGetLogChanges` do not compile; no `LogChanges` property over REST. Don't design a log-off load window (`TI-011`) | `../../pa-ti/references/v12-tested-behaviour.md` |
| Conditional-feeder setting | `ReevaluateConditionalFeeders` is absent from the active configuration; conditional feeders still fire once (`FED-007`) | `../../pa-rules/references/v12-tested-behaviour.md` |
| Stopping a process | `ProcessQuit` ends `QuitCalled`, `ProcessError` ends `Aborted`; neither runs the Epilog (`TI-009`) | `../../pa-ti/references/v12-tested-behaviour.md` |
| Recursive rules | A 600-step chain resolved, 650 returned `#N/A` silently (`RUL-007`) | `../../pa-rules/references/v12-tested-behaviour.md` |
| Debug and log files | `AsciiOutput` writes to the root of the database `Files` area; process logs are JSON lines read over REST | `../../pa-ti/references/v12-tested-behaviour.md` |

This file lists design-affecting differences only. It is not an API reference.
Connection mechanics belong to the MCP server or your REST tooling, not to a
modelling skill.
