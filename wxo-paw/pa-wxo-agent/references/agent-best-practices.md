# Building a production wxO agent on Planning Analytics

Use this when assembling the agent, its tools and its deployment checks.
Keep endpoint diagnosis in the `pa-mcp-connect` skill, query accuracy in
`pa-agent-query`, dashboard context in `paw-wxo-context`, and UI commands in
`paw-wxo-actions`.

Evidence labels describe the supplied project records, not a fresh platform test.
“Source pattern” means code or a documented convention; “planned” means a plan,
not a confirmed implementation. Preserve those distinctions when adapting this.

These practices come from one internal reference project (a PA FP&A agent built
on wxO, with an approval Flow, chart and PDF tools, and PAW embedding). The
section references in brackets point at its records, which are not shipped with
this skill. They are for maintainers checking provenance. Readers can ignore them.

Source key (paths relative to that project):

| Key | Allowed source |
|---|---|
| Lessons | `wxo/README.md`, “Lessons from the template that change our plans” |
| Plan | `plans/03-agent-and-integration.md`, especially §4, §6 and §10 |
| Architecture | `wxo/docs/from-template/architecture-and-maintenance.md` |
| Approval fix | `wxo/docs/from-template/run-scenario-structural-approval-fix.md` |
| Context | `wxo/docs/from-template/paw-dashboard-context-capability.md` |
| Stress | `wxo/docs/from-template/agent-stress-test-plan.md` |
| Bootstrap | `wxo/docs/from-template/AI_BOOTSTRAP_PROMPT.md` |
| Storage | `wxo/docs/from-template/cloud-object-storage-connection.md` |
| Sandbox | `wxo/docs/from-template/tm1-sandbox-tooling.md` |
| Scripts | `wxo/scripts/deploy_stack.py` and `wxo/scripts/ask_wxo_agent.py` |
| Guide | The workspace's `pa-wxo-custom-agent-guide.md`, §7, §8 and §9.6 |

The Approval fix supersedes Architecture's earlier approval-only design and its
claim that the structural version is still unbuilt. Plan §10 likewise supersedes
the earlier direct-write tool list and `confirm=true` outline. *(documented fixes)*

## 1. Architecture: what goes where

| Component | Put here | Boundary and evidence |
|---|---|---|
| PA MCP toolkit | Reads, model discovery and generic TM1 operations | Expose named operations only; exclude destructive operations from an analyst. *(Plan §3; Lessons)* |
| Custom Python tools | Deterministic analysis, validation, multi-call logic, rendering | Return a result the model narrates without recomputing. *(Architecture §4–§5, §11)* |
| Flows | Approval and execution for anything that writes | Put the write node behind Yes; remove direct agent access. *(Approval fix, confirmed live)* |
| PAW commands | Actions on the user's PAW screen | Follow the `paw-wxo-actions` skill. *(Guide §9.6; Context, confirmed live)* |
| Pre-invoke plugin | Validate and normalise current dashboard context | Follow the `paw-wxo-context` skill. *(Context, confirmed live)* |

Build a custom tool when a repeated analysis needs exact sorting, rate arithmetic,
multiple queries or validation before the model speaks. The reference tools own
those calculations and return preformatted answers. *(Architecture §4–§5)*

Keep MCP available for open-ended exploration outside a custom tool's declared
scope. Do not force a leaf-only ranking tool to answer a consolidation question.
*(Stress §B; source test contract)*

## 2. The agent definition

| Field | Set deliberately |
|---|---|
| `llm` | Select an available model; the plan calls for comparing two candidates. *(Plan §4, planned)* |
| `style` | Examples use `react`; the plan suggests trying it when multi-step chains stall. *(agent YAML structure; Plan §4)* |
| `instructions` | Role, model facts, defaults, ordered workflows and grounding. *(Plan §4.1)* |
| `guidelines` | Conditional routing and specific behaviour, including PAW command templates. *(Architecture §2, §10)* |
| `context_access_enabled`, `context_variables` | Enable access and list `data_context` for PAW context. *(Plan §4)* |
| `tools` | Explicit callable names; qualify MCP names with their toolkit prefix. *(Architecture §4)* |
| `plugins` | Attach the pre-invoke context guard. *(Plan §4)* |
| `starter_prompts` | Offer supported tasks that also make useful smoke tests. *(Plan §4, §6)* |
| `collaborators` | The supplied analyst definition uses an empty list. *(YAML structure)* |

Minimal illustrative definition; replace placeholders and use deployed tool names.
The raw scenario-write tool is deliberately absent. *(Plan §10; Approval fix)*

```yaml
spec_version: v1
kind: native
name: planning_assistant
display_name: Planning Assistant
description: Explains Planning Analytics results and proposes approved scenarios.
llm: <available-model-id>
style: react
context_access_enabled: true
context_variables:
  - data_context
instructions: |
  Work on {database}. Use the configured reporting defaults.
  Get every figure from tools. Report missing data and failed queries plainly.
  Use scenario_approval for writes; its result says what executed.
guidelines: []  # Add task routing and the supported PAW command guidelines.
tools:
  - <toolkit>:execute_mdx_and_get_view
  - analyze_variance
  - scenario_approval
  - i__get_flow_status_intrinsic_tool__
plugins:
  agent_pre_invoke:
    - plugin_name: paw_data_context_guard
  agent_post_invoke: []
starter_prompts:
  - Explain the current reporting period against budget.
collaborators: []
```

Check the callable list after each change. Keep the Flow and its status intrinsic;
exclude the raw write tool and any generic process executor that could bypass the
approved path. *(Approval fix; Sandbox, schema inspection)*

Maintain a separate read-only analyst agent in the same environment. Test analysis
there before the real agent. An approval-only probe can test controls without
writing; a disposable structural Flow test adds a controlled write path and must
be treated accordingly. *(Lessons; Approval fix §4.2)*

## 3. Instructions and guidelines

Write instructions in this order: role and scope, model facts, defaults, task
workflows, number rules, write rules, external-source rules and response style.
This follows the plan's outline. *(Plan §4.1, planned)*

State the database, valid versions, currency, fiscal calendar, sign conventions
and areas empty by design. Read the reporting period from its control value when
the model supplies one. Do not replace these with remembered assumptions.
*(Plan §4.1; reporting-period workflow planned)*

Use guidelines for “when this request occurs, do this”: choose the right analysis,
resolve an implicit reference, or return the exact PAW command. Review overlapping
triggers and add explicit exclusions to both competing rules. *(Architecture §10)*

Do not make guideline text the approval boundary. The model bypassed increasingly
explicit approval wording through direct requests and changed proposals.
*(Approval fix; failed live 3 times with guideline-only gating)*

Keep diagnostic instructions out of normal business answers. A rule requiring a
context-received preamble, source path and hash leaked into production replies.
Show transport details only when asked for diagnostics. *(Context §3, confirmed live)*

Require a fresh tool result for the current question; say when a query fails or
returns no data. The current agent's instructions explicitly forbid answering
numbers from memory or earlier turns. *(agent YAML instruction pattern)*

For context rules and selected-cell resolution, use the `paw-wxo-context` skill.
Do not copy a reduced version of that procedure into a business workflow.
*(Context §7–§9; repeated live resolution failures)*

## 4. Python tools

Treat the signature and docstring as the model's entire interface. The model does
not read the source. Document accepted arguments, exclusions, units, output states
and exactly what the model may narrate. *(Architecture §4)*

Package one Python file per tool with its own `requirements.txt`; avoid imports
from shared local helper modules. The import packages the file and dependencies.
Fix duplicated helpers in every copy. *(Lessons; Architecture §4)*

| Convention | Apply it | Evidence |
|---|---|---|
| Tables | Start pipe-delimited headers and rows at column 0, without outer pipes | Architecture §11; generic parser failures |
| Markers | Emit “deterministic tool output” and “NOTES FOR THE AGENT” | Lessons; Architecture §7A, §11 |
| Arithmetic ownership | Say “do not recompute / re-rank / invent” | Architecture §11 |
| Rates | Return human percentages already multiplied by 100; document that | Lessons; Architecture §11 |
| Rate differences | Label differences in rates `pp`, not `%` | Architecture §11; live direction bugs |
| TM1 cell types | Apply `_coerce_numeric` / `_is_missing` at every raw-cell extraction | Lessons; Architecture §11 |
| Missing data | Identify incomplete entities and unavailable panels explicitly | Architecture §11; Stress §M, §N |
| Failure states | Return `INPUT ERROR`, `TOOL ERROR`, `PARTIAL` or `FAILED` with narration limits | Architecture §11 |

Require column-zero table detection in pass-through parsers. Indented narrative
can accidentally look like another table. Check known output markers where a
source tool has that contract; do not invent a fingerprint for arbitrary MCP
output. *(Architecture §7A, confirmed parser lesson)*

Set `ToolPermission.READ_ONLY` on read tools. The storage-upload example uses
`ToolPermission.READ_WRITE`; exporting a file has a side effect even when the
financial analysis only reads TM1. *(Storage §3.C; OAuth reference)*

Degrade to useful partial results when one panel or independent upload fails.
Keep successful outputs available and name the missing part; do not fabricate a
complete result. *(Architecture §7, §11; Stress §M8)*

Read credentials from declared connections and never return tokens, including in
errors. Use [the OAuth reference](wxo-oauth.md) for the production implementation
and review checks; do not copy credential handling into every tool recipe.

## 5. Numbers the agent can stand behind

Ground deliverables against verbatim `source_tool_outputs` from every cited call.
A source trace alone is insufficient. Reject unsupported figures and repair the
narrative from the evidence before producing the file. *(Lessons; Stress §L11–§L16)*

For a driver diagnosis, fetch line-item evidence for every compared entity. Check
the direction of each claimed driver against its own values. Compare margin
amount and margin rate independently: their directions can differ.
*(Context §5, §9, confirmed live)*

Use the `pa-agent-query` skill for exact MCP numbers and regression question sets.
The table-producing tool, rather than the model, owns ranking and calculations.
*(Architecture §5; Stress §B–§D)*

## 6. Writes and approvals

Use [Writes through Flows](flows-and-approvals.md) for the graph, confirmation
check and live validation. Only the approved branch may reach the write node;
the agent cannot call the raw write tool. *(Approval fix, confirmed live)*

Approval alone does not establish the right target. In a live incident, a selected
cell implied “this entity”; the model replaced the contextual MDX with a simpler
query and guessed the member. The user approved the resulting proposal, and the
write reached the wrong entity. Resolve the current selection in code, with a
value match, before building the approval prompt. Follow the `paw-wxo-context`
skill for that procedure. *(Context §7–§8, confirmed production incident)*

Do not equate sandbox creation with sandbox-scoped execution. The inspected MCP
`execute_tm1_processes_asynchronously` schema has no sandbox parameter and targets
base data. The supplied implementation exposes lifecycle operations and has the
human edit in PAW. A custom sandbox-write tool remains unbuilt, **untested**.
*(Sandbox §2–§4; schema inspection)*

Treat publishing a sandbox as a production write: it merges into base data and
can delete the sandbox by default. Require approval naming the sandbox and
consequence. *(Sandbox §3)*

## 7. Connections and secrets

Use [OAuth](wxo-oauth.md) for the production rules and
[API-key connections](api-key-connection.md) for the fallback. Use the
`pa-mcp-connect` skill for endpoints and authentication triage.

Set credentials separately for draft and live; rotation updates both. Re-import
Python tools with every required `-a` connection flag on every update.
*(Bootstrap §5–§6; Architecture §4; confirmed import behaviour)*

Keep non-secret placeholders in source and fill them consistently at deployment.
Keep secrets out of configuration and tool code. Do not ask for or accept secrets
in chat; the credential owner runs credential-setting commands in their terminal.
If a secret is pasted, require rotation. *(Bootstrap §2–§5)*

## 8. Charts, files and rendering in chat

In the tested ADK 2.12.0 path, Python tool results support text. Generate bytes,
upload them to COS, and return a markdown image or download link with a presigned
GET URL. Base64 data URIs do not render correctly. *(Architecture §6; Lessons, confirmed live)*

Force `region_name` and `Config(signature_version="s3v4")` in the boto3 client.
The default can silently produce SigV2 links that fail to load. Use HMAC credentials
for this S3 path, not the storage service's IAM key. *(Storage §4, confirmed live)*

Use the demonstrated one-hour expiry (`3600` seconds); regenerate expired links.
Plan's older seven-day report suggestion is not the confirmed template convention.
*(Lessons; Storage §4; Plan §8)*

Widgets, artifact metadata and raw iframes did not provide interactivity in standard
hosted chat. Link downloadable HTML for interactive reports. Native Flow Boolean
controls are a separate mechanism and did render Yes/No buttons.
*(Architecture §6.1–§6.2, confirmed live)*

Do not promise inline images in PAW from standard-chat evidence alone. Rendering
inside the PAW embedded panel remained **untested** in Plan §10; verify it there.
The Guide's older tool `_meta` command route is **[inferred]**, not a proven fallback.

## 9. Testing

Follow the source sequence: offline checks, read-only analyst, real agent, then
PAW-specific verification. Inspect tool arguments and returns as well as prose.
*(Architecture §8–§9; Lessons)*

Offline, mock TM1 helpers for validation, invalid enums, empty inputs, missing
values and zero division. Render generated PDFs to images and inspect layout;
functional success does not catch overlap or clipping. *(Architecture §8)*

Use an “ask agent” script for repeatable live questions: select the active CLI
environment, resolve the agent by name, send the question, save the raw response
and thread ID. Handle expired sessions explicitly. *(Scripts; source pattern)*

| Category | Check | Evidence |
|---|---|---|
| Grounding and defaults | Correct scope; no cross-turn invented values | Stress §A, §N |
| Ranking and variance | Leaf scope, order, sign and baseline | Stress §B–§C |
| Drivers | Complete evidence; line-item directions; amount versus rate | Stress §D; Context §9 |
| Trend | Correct time order and missing-period handling | Stress trend tests; CSV §Q5 |
| Scenarios | Decline, approve, changed value while pending, independent read-back | Approval fix §4.2 |
| Charts | Actual image loads; correct figures and units | Stress §K; Storage §4 |
| Exports | All source tables; grounded narrative; real file layout | Stress §L–§M, §Q |
| Context | Changed and repeated selections, missing context, truncated MDX | Stress §R–§S; Guide §8 |
| PAW commands | Correct command and perspective; no accidental Flow call | Stress §T |

Add organic follow-ups beyond scripted prompts. They exposed chart-type
misrouting, false “no breakdown” claims and stale-cell reuse. *(Context §5, §8)*

Flows are only provable live: compile/import success cannot prove button rendering,
Boolean coercion or pending-approval collisions. Test in real PAW chat as well as
the wxO preview. CLI chat has no PAW dashboard context. *(Architecture §8; Bootstrap §10)*

## 10. Deploying: draft and live

Import in dependency order: connections → credentials in both environments →
MCP toolkit → Python tools and plugin → Flows → agent → deploy.
This combines the plan's ordering with the Flow dependency on registered tools.
*(Plan §3, §10; Bootstrap §5–§9; Flow source pattern)*

`orchestrate tools import` updates draft. `orchestrate agents deploy --name
<agent>` promotes the current draft to live. Re-import the agent whenever its
YAML changes; tool-only changes do not require agent YAML import.
*(Architecture §4; documented draft/live mechanics)*

Import Flows with `orchestrate tools import --kind flow --file flows/<name>.py
--save-flow-json /tmp/<name>.json`. Include the Flow and
`i__get_flow_status_intrinsic_tool__` in the agent definition. *(Architecture §9)*

Follow the deploy script's pattern: check the active environment, run explicit
subprocess argument lists, stop on unexpected failures, redact secret output,
and make temporary copies for substitutions and tool renames. *(Scripts)*

Do not assume that script deploys live or imports Flows: its current stack omits
Flows and ends after agent import. Add the required Flow import and live promotion
for a write-capable deployment. *(Scripts; current source limitation)*

## 11. Known platform issues

| Symptom or boundary | Workaround and evidence |
|---|---|
| Second Flow approval in one chat returns 401 surfaced as 424 | Start a fresh chat per scenario; no write occurred. Auth-refresh cause is **[inferred]**. *(Approval fix §7, reproduced twice)* |
| Flow imports but Yes always declines | Use the nested field's `.output.value` path and test Yes explicitly. *(Approval fix §4.1, confirmed live)* |
| Decline branch fails at runtime | Route conditions' default through a `script()` node before END. *(Approval fix §4.1, confirmed live)* |
| Raw `flow_output` card precedes narration | `suppress_agent_summarization=False`; recheck narrated figures. *(Approval fix §5, confirmed live)* |
| Broken image despite successful signing | Force SigV4 plus region; regenerate old links. *(Storage §4, confirmed live)* |
| Widget metadata disappears in hosted chat | Use a file link or a supported Flow control. *(Architecture §6.1–§6.2, confirmed live)* |
| PAW native command reports a missing service | Compare with the stock agent; check PAW service health. *(Context §6; Stress §T5, confirmed live)* |
| Chart type cannot be identified from context | Say it is absent; do not guess or silently fire Chart Insights. *(Context §5, confirmed live)* |
| Large SSO/OBO JWT causes HTTP 500 / underlying 431 | Keep JWT small; source records an 8 KB header limit. *(Guide §7, documented)* |
| Exported agent YAML contains mojibake | Repair targeted strings and parse with `yaml.safe_load`. *(Architecture §9, observed export issue)* |

## 12. Pre-production checklist

Apply these checks using the evidence and procedures above.

- [ ] Verify the model exists and matches the tool contracts before importing tools.
- [ ] Complete the [OAuth tool review checklist](wxo-oauth.md#review-checklist-for-a-tool-before-it-ships).
- [ ] Set credentials on both environments and verify every tool's bindings.
- [ ] Fill non-secret placeholders consistently; leave no secrets in source or chat.
- [ ] Restrict MCP operations; keep raw write tools out of the agent's callable list.
- [ ] Inspect Flow edges and prove decline and approve by independent TM1 read-back.
- [ ] Test changed values while approval is pending; never accept a plain-chat substitute.
- [ ] Resolve selected targets afresh before proposing a write; follow `paw-wxo-context`.
- [ ] Check numeric coercion, percentages, pp gaps, missing data and partial outputs.
- [ ] Verify deliverable figures against every cited source tool output.
- [ ] Pass offline checks and live analysis tests on the read-only analyst first.
- [ ] Load charts and files, inspect export layout, and test rendering in real PAW.
- [ ] Run stress categories and organic follow-ups; inspect actual tool traces.
- [ ] Re-import changed agent YAML, deploy live, and verify the live environment.
- [ ] Record the second-approval issue and use fresh chats until it is resolved.
