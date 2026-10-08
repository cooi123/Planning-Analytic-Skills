# Planning Analytics skills

Eight skills for working with IBM Planning Analytics (TM1) from an AI assistant
(IBM Bob or Claude Code). They cover three jobs:

- **Connect** an AI client to the PA agentic-AI MCP endpoint.
- **Model**: design, build and review TM1 models, write their business rules, and load their data with TI.
- **Embed**: run a custom watsonx Orchestrate (wxO) agent inside Planning
  Analytics Workspace (PAW) chat that understands what the user is looking at
  and can drive the PAW screen.

| Skill | Use it to | Writes to a server |
|---|---|---|
| [`pa-mcp-connect`](pa-mcp-connect/SKILL.md) | Connect an MCP client to PA, or work out why a connection fails | No |
| [`pa-model-design`](pa-model-design/SKILL.md) | Design a model and emit a design spec | No |
| [`pa-model-build`](pa-model-build/SKILL.md) | Build an approved spec on a server | **Yes**, only when invoked by name |
| [`pa-model-review`](pa-model-review/SKILL.md) | Review a model against its spec or on its own, and triage wrong numbers | No |
| [`pa-rules`](pa-rules/SKILL.md) | Write, explain and fix business rules and feeders, and load them through PAW, TI or REST | Only when asked |
| [`pa-ti`](pa-ti/SKILL.md) | Write, debug and run TurboIntegrator processes, including loads from files, databases, SAP and Cognos | Only when asked |
| [`paw-wxo-context`](paw-wxo-context/SKILL.md) | Connect PAW to a custom wxO agent and use PAW's `data_context` (open cubes, MDX, selected cells) | No |
| [`paw-wxo-actions`](paw-wxo-actions/SKILL.md) | Make the agent drive PAW: open books, cubes and views, switch perspective, run AI panels | No (UI only, as the signed-in user) |

## Quick start

### 1. Install

Copy the skill folders, not this README, into your assistant's skills directory.

```bash
git clone <this repo> pa-skills

# IBM Bob: per workspace
mkdir -p .bob/skills && cp -r pa-skills/pa-* pa-skills/paw-* .bob/skills/

# Claude Code: per project, or ~/.claude/skills for every project
mkdir -p .claude/skills && cp -r pa-skills/pa-* pa-skills/paw-* .claude/skills/
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

Work through `paw-wxo-context` first, then `paw-wxo-actions`:

```
Connect PAW agentic chat to my wxO agent.
Make my agent explain the cell I've selected in PAW.
Make the agent open a cube when I ask.
The agent returns JSON but nothing happens in PAW.
```

## How each skill is designed

All eight share three rules:

- They never ask for or store credentials.
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

### `pa-model-design` → `pa-model-build` → `pa-model-review`: the modelling lifecycle

```
pa-model-design  ──spec──▶  pa-model-build  ──▶  pa-model-review
      ▲                                                │
      └──────────────── findings ──────────────────────┘
```

- **Conventions are config.** All three read `pa-conventions.yaml`. Nothing
  project-specific is written into a skill.
- **The standard is data.** `pa-model-review/checks/checks.yaml` holds 35 checks
  (dimensions, cubes, rules, feeders, TI, security, naming). Review uses them to
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
- `references/rule-examples.md`: eight worked rule and feeder pairs.
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
cd paw-wxo-context/assets/resolve_selected_cell  && python -m unittest test_resolve_selected_cell.py
cd ../paw_data_context_guard                     && python -m unittest test_paw_data_context_guard.py
cd ../cell_lineage                               && python -m unittest test_cell_lineage.py
```

**Live-tested on PA on Cloud 2.1.23** (PA MCP 1.27.2, ADK 2.10.0):

- The MCP connection and probe.
- The PAW custom-instance setup.
- `select_database`, `open_paw_artifact`, `open_tm1_artifact` and
  `switch_to_perspective`.
- Selected-cell context and resolution against a live view.

The connection and PAW skills mark which parts are verified and which aren't.
The modelling skills, `pa-rules` and `pa-ti` haven't been run end to end against a server yet.

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
| A PAW command | Capture the payload from the default PA agent (DevTools → Network) and add it to `paw-wxo-actions/references/command-templates.md` with the PAW version |
| A PAW reply | A row in `paw-wxo-actions/references/paw-responses.md` |
| A lifecycle stage | A new skill folder |
