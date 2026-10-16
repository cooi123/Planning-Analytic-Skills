# Planning Analytics skills

Twelve skills for working with IBM Planning Analytics (TM1) from an AI assistant
(IBM Bob or Claude Code), in two groups: core PA skills, and the `wxo-paw` group
(watsonx Orchestrate + PAW integration). They cover five jobs:

- **Connect** an AI client to the PA agentic-AI MCP endpoint.
- **Query**: get correct numbers out of a cube through the MCP tools, and test an
  agent that does it.
- **Model**: design, build and review TM1 models, write their business rules, and load their data with TI.
- **Build PAW content from code**: create books, dashboards and widgets through
  the REST APIs.
- **Embed**: run a custom watsonx Orchestrate (wxO) agent inside Planning
  Analytics Workspace (PAW) chat that understands what the user is looking at
  and can drive the PAW screen.

### Core

| Skill | Use it to | Writes to a server |
|---|---|---|
| [`pa-mcp-connect`](pa-mcp-connect/SKILL.md) | Connect an MCP client to PA, or work out why a connection fails | No |
| [`pa-agent-query`](pa-agent-query/SKILL.md) | Answer questions from cube data through the MCP tools without wrong numbers, and build a regression test set for an agent | No |
| [`pa-model-design`](pa-model-design/SKILL.md) | Design a model and emit a design spec | No |
| [`pa-model-build`](pa-model-build/SKILL.md) | Build an approved spec on a server | **Yes**, only when invoked by name |
| [`pa-model-scan`](pa-model-scan/SKILL.md) | Scan a TM1 database read-only to inventory structure and map cube dependencies for health checks and migration analysis | No |
| [`pa-model-review`](pa-model-review/SKILL.md) | Review a model against its spec or on its own, and triage wrong numbers | No |
| [`pa-rules`](pa-rules/SKILL.md) | Write, explain and fix business rules and feeders, and load them through PAW, TI or REST | Only when asked |
| [`pa-ti`](pa-ti/SKILL.md) | Write, debug and run TurboIntegrator processes, including loads from files, databases, SAP and Cognos | Only when asked |
| [`paw-dashboard-api`](paw-dashboard-api/SKILL.md) | Create, clone and delete PAW books, dashboards and widgets (grids, bar/line/column charts, selectors) through the REST APIs, and test them safely on a tenant | **Yes**, only when asked (creates and deletes books and views) |

### wxO and PAW integration (wxo-paw/)

| Skill | Use it to | Writes to a server |
|---|---|---|
| [`wxo-paw/pa-wxo-agent`](wxo-paw/pa-wxo-agent/SKILL.md) | Build, connect, test and ship a production wxO agent on PA | No (wxO only); its Flows may write to TM1 after user approval |
| [`wxo-paw/paw-wxo-context`](wxo-paw/paw-wxo-context/SKILL.md) | Connect PAW to a custom wxO agent and use PAW's `data_context` (open cubes, MDX, selected cells) | No |
| [`wxo-paw/paw-wxo-actions`](wxo-paw/paw-wxo-actions/SKILL.md) | Make the agent drive PAW: open books, cubes and views, switch perspective, run AI panels | No (UI only, as the signed-in user) |

## Quick start

### 1. Install

Copy the skill folders, not this README, into your assistant's skills directory.

```bash
git clone <this repo> pa-skills

# IBM Bob: per workspace
mkdir -p .bob/skills && cp -r pa-skills/pa-* pa-skills/paw-* pa-skills/wxo-paw/pa-wxo-agent pa-skills/wxo-paw/paw-wxo-* .bob/skills/

# Claude Code: per project, or ~/.claude/skills for every project
mkdir -p .claude/skills && cp -r pa-skills/pa-* pa-skills/paw-* pa-skills/wxo-paw/pa-wxo-agent pa-skills/wxo-paw/paw-wxo-* .claude/skills/
```

Keep each skill's `references/`, `patterns/`, `checks/`, `scripts/` and
`assets/` folders. The skills load them at run time by relative path.

### 2. Pick a path

**A. Connect an assistant to PA** (start here if PA tools aren't showing up)

You need the PAW host and port, the PAW version, the PA Agent add-on, and a
credential (username/password, MCSP API key or OAuth client).

```
Connect Claude to my PA MCP server at https://<host>. It's PA on Cloud, version 2.1.23.
My MCP server returns 401, what's wrong?
Which store had the worst sales variance to budget in FY2025?
The data explorer gave me a number that looks wrong. Check it.
Build a test question set for my PA agent.
```

**B. Design, build and review a model**

Create `pa-conventions.yaml` in your workspace root first (naming, dimension
order policy, PA version, environments, thresholds). Without it, the modelling
skills fall back to documented defaults and say so each time.

```
Design a driver-based revenue model: price x volume by product and region, monthly, Budget and Forecast.
Build the model from design/revenue.spec.yaml in dev.        <- explicit, writes to the server
Review the Revenue cube against design/revenue.spec.yaml.
Consolidation shows zero but the leaves have data. Why?
Write a rule for Revenue = Units x Price in the Sales cube, with its feeder.
Write a TI process that loads sales.csv into the Sales cube for a given version.
How do I load these rules into PAW?
```

**C. Put a custom agent in PAW chat**

You need all of the following:

- PAW 2.1.22+ (SaaS / PA on Cloud) or 3.1.9+ (local) with the PA Agent add-on.
- PAW admin rights.
- A wxO environment where **you** control embedded-chat security. The key is set
  once per instance, so don't replace a key other chats depend on.
- On PA on Cloud: a watsonx.ai project and API key.
- The ADK CLI (`orchestrate`).

Work through `pa-wxo-agent` first, then `paw-wxo-context`, then `paw-wxo-actions`:

```
Build a wxO agent for Planning Analytics with OAuth per-user credentials.
Connect PAW agentic chat to my wxO agent.
Make my agent explain the cell I've selected in PAW.
Make the agent open a cube when I ask.
The agent returns JSON but nothing happens in PAW.
```

## How each skill is designed

All of them share four rules:

- They never ask for or store credentials.
- Code they produce for production (agent tools, chart and dashboard tools) never
  holds a credential. It reads one from the platform connection at run time,
  preferably a per-user OAuth connection. See
  [`wxo-paw/pa-wxo-agent/references/wxo-oauth.md`](wxo-paw/pa-wxo-agent/references/wxo-oauth.md).
- They separate what was verified from what was inferred.
- Project-specific facts live in config or data files, not in skill prose.

### `pa-mcp-connect`: connect, or diagnose why not

A PA MCP connection depends on four things at once, and each fails with its own
status code:

| Wrong value | Looks like |
|---|---|
| Host or port | Connection refused, or a login page |
| Endpoint path | `404` |
| Version-correct path | `404` |
| Auth | `401`, `403` or a blanket `500` |

The skill works them in that order:

1. Establish four facts: deployment, PAW version, add-on, credential.
2. Build the URL. PAW 2.1.22 / 3.1.9 replaced the separate `cube` and
   `analysis` endpoints with one `ibm-pa-tools` endpoint.
3. Probe with `scripts/probe-mcp.sh`. It's read-only: `initialize` and
   `tools/list` only.
4. Choose the auth method.
5. Triage by status code, using a control request to tell "wrong password" from
   "server broken".
6. Write the client config.

The deep material is in `references/` (endpoints by version, authentication,
troubleshooting). It warns that a connected agent gets the endpoint's write and
delete tools.

### `pa-agent-query`: right numbers, or a clear "no data"

Getting connected is the easy part. In testing on PA as a Service the
natural-language data explorer answered none of three phrasings of a variance
question, and on a plain single-cell lookup it returned real, consistent numbers for
a department leaf instead of the store total that was asked for. Zeros get noticed.
That kind of answer doesn't. The skill works in this order:

1. Write down the facts about the cube that its member names don't show: sign
   convention, fiscal calendar, which periods hold Actual, data scope, known-broken
   hierarchies.
2. Pick the tool. MDX through `execute_mdx_and_get_view` for any number you will
   quote. The data explorer for exploring only, with its member choices read back.
3. Confirm every member with `lookup_potential_members`, level as well as name.
4. Compute variance and rankings as `WITH MEMBER` and `ORDER`, with `ABS()` on the
   base and ratios at the highest `SOLVE_ORDER`.
5. Read raw values. `get_saved_view` renders cost-line variance % with the sign
   flipped.
6. Turn codes into names from the attribute cube, and say which "worst" you used.

It ships with three references:

- `references/data-explorer-limits.md`: the worked test, attempt by attempt.
- `references/mdx-patterns.md`: tested MDX for variance, prior year, ranking,
  view-local totals and name columns, with the `SOLVE_ORDER` and `NONEMPTY` traps.
- `references/agent-test-set.md`: a five-tier regression set, from single-cell
  retrieval to trap questions where the right answer is "nothing there".

### `pa-model-design` → `pa-model-build` → `pa-model-review`: the modelling lifecycle

```
pa-model-design  ──spec──▶  pa-model-build  ──▶  pa-model-review
      ▲                                                │
      └──────────────── findings ──────────────────────┘
```

- **Conventions are config.** All three read `pa-conventions.yaml`. Nothing
  project-specific is written into a skill.
- **The standard is data.** `pa-model-review/checks/checks.yaml` holds 47 checks
  (dimensions, cubes, rules, feeders, TI, MDX views, security, naming). Review uses them to
  verify. Design runs the same checks against itself before it emits a spec, so
  design and review can't drift apart. Org-specific checks go in
  `checks.local.yaml`, merged by `id`.
- **Patterns are a directory.** Design lists `pa-model-design/patterns/` and reads
  whatever matches the problem. It ships with three patterns: driver rate ×
  quantity, allocation and time phasing. Adding one means adding a file; see
  `patterns/README.md`.
- **The spec is a contract.** Design writes `design/<module>.spec.yaml`. Build
  implements only that file, and review checks the build against it.
- **Build is fenced.** It runs only when invoked by name. It refuses any
  environment marked `writable: false`, and confirms each destructive change
  before making it.
- **Views are part of the design.** `references/views-and-calculated-members.md`
  covers where variance lives (dimension members with rules, or MDX in views, and who
  loses access to each, AI agents included), sign convention from weights,
  `SOLVE_ORDER`, string columns, subsets and an agent-readiness list.
- **Inherited dimensions get checked before loading.** Mixed-level consolidations,
  YTD members with an opening-balance child, broken rolling hierarchies, mis-parented
  members and overlapping account families each have a check.
- **Review has three modes:** conformance (against a spec), intrinsic (no spec;
  "structurally sound, intent not assessed") and triage (symptom to cause).

### `pa-rules`: write one rule file well

Design decides *which* calculations are rules. `pa-rules` writes and fixes the
statements themselves:

1. Read the cube's dimension order, real element names and existing rule file. A
   save replaces the whole file, so it never writes blind.
2. Write each statement with a scope, safe division and correct precedence.
3. Write its feeder in the same step.
4. Merge into the existing file and self-check against the same `RUL-*` and
   `FED-*` checks that review uses.
5. Validate, and deploy only when asked.

It ships with four references:

- `references/rules-syntax.md`: syntax, including the often-forgotten operators
  (`\` versus `/`, `@=`, `%` for OR, `~`).
- `references/rules-functions.md`: every function category in PAW's Function
  list, and when to use the hierarchy-aware `Element…` functions over the legacy
  ones.
- `references/rule-examples.md`: eleven worked rule and feeder pairs, several
  adapted from IBM's TM1 Rules guide (time series, allocation, stocks and flows).
- `references/writing-and-deploying-guide.md`: a step-by-step human guide,
  including loading rules through the PAW Modeling workbench,
  `RuleLoadFromFile` and the TM1 REST API. The PA MCP endpoint has no rules
  tool, so an MCP-only assistant drafts rules but can't save them.

### `pa-ti`: load and maintain data with TurboIntegrator

Rules calculate on read. TI writes the inputs. `pa-ti` writes, debugs and runs
processes:

1. Confirm the TM1 version (v11 or v12 changes how files and ODBC work), the
   target cube's dimension order, and the real source columns.
2. Pick the data source.
3. Write Prolog, Metadata, Data and Epilog with strict tab discipline, parameters,
   a slice-only clear and logged counts.
4. Self-check against the `TI-*` checks.
5. Create and run only when asked, through PAW or the PA MCP process tools.

It ships with two references:

- `references/data-sources.md`: the five PAW source types (File, Location,
  Database connection, Cube, Dimension set), the TM1 v12 ODBC Data Connector,
  re-runnable load templates, and **external systems**: the IBM Planning
  Analytics Connector for SAP, Cognos (go to the database behind it), ETL tools
  pushing through REST, and REST or OData URLs on v12.
- `references/writing-and-running-guide.md`: a human guide to the PAW process
  editor, running, scheduling with chores, and troubleshooting.

### `pa-wxo-agent`: build and ship a production wxO agent on PA

The foundation skill for the wxO-PAW group. It covers the full agent lifecycle:

- **Connection choice:** OAuth auth-code (per-user, member credentials) versus API
  key (team, one identity). OAuth is preferred for production.
- **Setup order:** connection → credentials → toolkit import. The toolkit import
  needs a live token, so sign in to draft first.
- **Least-privilege toolkits:** list named MCP tools, not `"*"`. Write tools never
  go in the agent's own `tools:` list.
- **Safe writes:** every TM1 modification goes through an approval Flow with Yes/No
  buttons. The write-capable step lives inside the Flow.
- **Python tools calling TM1 REST:** read credentials from the wxO connection at run
  time with `connections.oauth2_auth_code(APP_ID).access_token`. For TM1py, re-add
  the Bearer header after creating the service.
- **Pre-production checklist:** no credential in code, HTTPS only, redacted errors,
  tested Flows, and a grep for hardcoded secrets before shipping.

The skill points to `references/agent-best-practices.md` (architecture, agent
definition, instructions, tools, numbers, writes, connections, charts, testing,
deploy, issues, checklist) and `references/flows-and-approvals.md` (approval
pattern, gotchas, validation).

### `paw-wxo-context`: the agent knows what's on the user's screen

PAW sends a `data_context` variable with every chat message: open widgets, cubes,
MDX, selected cells, perspective and role. The skill covers four pieces:

1. **Connect PAW to the agent.** RSA key pair, live deployment, and the Custom
   instance JSON with its fields at the top level.
2. **Let the agent read it.** `context_access_enabled` and `context_variables`.
3. **Show it to the model reliably.** Optionally use
   `assets/paw_data_context_guard/`, a pre-invoke plugin. It validates and trims
   the context and labels it `VALID`, `ABSENT`, `METADATA_ONLY`, `TOO_LARGE`, and
   so on, so the model can tell "no context" from "bad context".
4. **Resolve selected cells in code, not by the model.** PAW gives a selected cell
   only as a row/column position plus a display value. The agent runs the view's
   MDX unchanged, then `assets/resolve_selected_cell/` maps the position to member
   names and checks the value it finds against the displayed one, returning
   `MATCH` or `MISMATCH`. `assets/cell_lineage/` then builds the cell's full
   coordinate and MDX for parents, children and roll-ups.

Every asset is a wxO Python tool with unit tests.

### `paw-wxo-actions`: the agent drives the PAW screen

A wxO agent can't call PAW. It can only reply. When the reply is exactly a
`user_defined` JSON payload that PAW recognises, PAW's front end carries out the
action as the signed-in user. So:

- **Payloads are never written from memory.** `references/command-templates.md`
  holds all 49 command guidelines verbatim, copied unchanged into the agent's
  `guidelines:`. Field names are irregular, and a near-miss fails silently.
- **A routing rule** tells the model to return the bare JSON and make no tool
  call.
- **Preconditions PAW enforces itself:** a selected database for TM1 commands,
  edit mode for anything that adds a widget, and the dashboard perspective for
  most commands.
- **`references/paw-responses.md`** lists what PAW replies, so you can tell from
  the chat which side refused a command and why.
- **Test inside PAW.** In the wxO test chat the same reply is inert text.

## Testing

The Python assets have unit tests. Run them with the Python that has the wxO ADK
installed:

```bash
cd wxo-paw/paw-wxo-context/assets/resolve_selected_cell  && python -m unittest test_resolve_selected_cell.py
cd ../paw_data_context_guard                     && python -m unittest test_paw_data_context_guard.py
cd ../cell_lineage                               && python -m unittest test_cell_lineage.py
```

**Live-tested on PA on Cloud 2.1.23** (PA MCP 1.27.2, ADK 2.10.0):

- The MCP connection and probe.
- The PAW custom-instance setup.
- `select_database`, `open_paw_artifact`, `open_tm1_artifact` and
  `switch_to_perspective`.
- Selected-cell context and resolution against a live view.

**Live-tested on PA as a Service, TM1 12.6.3** (August 2026), building and querying
a seven-dimension retail P&L cube from a wxO agent:

- Basic `apikey:<PA API key>` auth, and the wxO connection → toolkit → agent import.
- Data explorer versus MDX retrieval, and the `get_saved_view` sign inversion.
- The MDX patterns in `pa-agent-query/references/mdx-patterns.md`.
- The dimension defects behind checks DIM-007 to DIM-011, CUB-006, VW-001 to
  VW-004, NAM-003 and NAM-004, and the load practices in `pa-model-build`.

The connection and PAW skills mark which parts are verified and which aren't.
`pa-model-build` as a skill, `pa-rules` and `pa-ti` haven't been run end to end against a server yet.

## Security

- No credentials are stored here. Keep keys and tokens in environment variables
  or a secret store, never in config you commit.
- Keep the embed private key (`pa-embed.key`) outside the repo and out of any
  assistant's context.
- An agent connected to the PA MCP endpoint can create and delete cubes,
  dimensions, views, sandboxes and processes. Use a least-privilege account
  beyond a sandbox.
- A wxO connection of type `team` makes every user's TM1 reads run as one
  account. Use per-user credentials where TM1 security matters.
- Many PA on Cloud and TechZone instances use plain HTTP, so Basic credentials
  travel unencrypted.

## Extending

| To add | Do this |
|---|---|
| A modelling pattern | A file in `pa-model-design/patterns/`, per its README |
| A review check | An entry in `pa-model-review/checks/checks.yaml`, or `checks.local.yaml` for org-only checks |
| A PAW command | Capture the payload from the default PA agent (DevTools → Network) and add it to `wxo-paw/paw-wxo-actions/references/command-templates.md` with the PAW version |
| A PAW reply | A row in `wxo-paw/paw-wxo-actions/references/paw-responses.md` |
| A lifecycle stage | A new skill folder |
