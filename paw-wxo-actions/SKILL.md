---
name: paw-wxo-actions
description: >-
  Build watsonx Orchestrate agent actions that drive the Planning Analytics
  Workspace (PAW) interface from agentic chat: opening books, cubes and views,
  switching perspective, Chart Insights, impact and outlier analysis, slicing,
  swapping, sorting, sandboxes, member calculations, user and group admin, and
  plan task approval. Covers the user_defined command payloads PAW recognises,
  how to deliver them from a native agent, and how to test them. Use for "make
  the agent open a cube", "custom intent for PAW", "PAW native command",
  "open_tm1_artifact", "user_defined response", "trigger chart insights from
  chat", "restore the default PA agent actions", "which commands does PAW
  support", "agent returns JSON but nothing happens in PAW", or any custom wxO
  agent that should act on the PAW screen.
user-invocable: true
---

# PAW actions from watsonx Orchestrate

A custom wxO agent cannot call PAW. It can only **reply**. When the reply contains
a `user_defined` payload with a `command` PAW recognises, PAW's own front end
carries out the action in the user's browser, as the signed-in user. So every
action comes down to one question: **does the reply contain the exact JSON that
PAW expects?**

```
user: "open the revenue cube"
  -> agent replies with ONLY:
     {"user_defined": {"command": "open_tm1_artifact",
                       "artifact_name": ["Revenue"],
                       "tm1_artifact_type": "cube"},
      "response_type": "user_defined"}
  -> PAW's chat host intercepts the reply and opens the cube
```

Two consequences shape everything below:

- **You cannot invent commands.** `{"command": "open_view"}` does nothing because
  PAW has no handler for it. Name your Actions, tools and guidelines however you
  like, but the payload must use PAW's names and fields.
- **Commands only work inside PAW.** In the wxO test chat, the API, Slack or Teams,
  the same reply is inert JSON. Test in PAW.

Writing data to TM1 (cube writes, TI processes) is a separate path through the PA
MCP toolkit. Commands only change what the user sees.

## Step 0. Confirm the prerequisites

1. PAW is connected to the custom agent: Administration → Integrations → IBM
   watsonx Orchestrate → Custom instance, with `orchestrationID`, `hostURL`,
   `agentId`, `agentEnvironmentId`, `perspectives`, `purchaseID` and `authKey`,
   all at the top level, plus the watsonx.ai configuration on PAoC. The
   `paw-wxo-context` skill, Step 0, has the exact JSON. If chat doesn't load in
   PAW at all, fix this first. Actions can't be tested without it.
2. The perspectives where you want actions are listed in `perspectives`. Any
   perspective you leave out keeps the default PA agent. Plans and Apps can't be
   switched yet.
3. The agent has `context_access_enabled: true` and `data_context` in
   `context_variables`. Most commands are gated on
   `data_context.userInformation.perspective` or `.role`. See the `paw-wxo-context`
   skill.

## Step 1. Pick the command

Read `references/command-templates.md` for the verbatim condition, parameters and
JSON of every command. **Never write a payload from memory.** The field names are
irregular (`artifact_name` is an array for some commands and a string for others,
and some templates use `type` where others use `response_type`), and a near-miss
fails silently.

Summary of what exists:

| Group | Commands | Gate |
|---|---|---|
| Navigation | `open_paw_artifact`, `switch_to_perspective` | any perspective |
| Discovery | `open_tm1_artifact`, `list_artifacts`, `lookup_tm1_artifact`, `select_database`, `search_context` | dashboard |
| AI panels | `chart_insights`, `impact_analysis`, `outlier_analysis`, `view_recommender`, `annotation_summary` | dashboard |
| View changes | `switch_context` (slice), `swap`, `move_dimension`, `switch_set`, `expand_member`, `collapse_member`, `hide`, `keep`, `unhide_all`, `suppress_zeroes`, `display_zeroes`, `sort`, `chart_view` | dashboard |
| Calculations | `member_calculation`, `summarize` | dashboard |
| Book | `copy`, `refresh`, `undo`, `redo` (`cancel` is a text reply) | dashboard |
| Sandboxes | `create_sandbox`, `switch_sandbox` | dashboard |
| Admin | `list_users`, `list_groups`, `list_users_for_groups`, `list_groups_of_user`, `create_user`, `delete_user`, `create_group`, `delete_group` | role = administrator |
| Plan tasks | submit, approve, reject, take or release ownership, revert submission or approval (multi-step, starting with `select_task_agentic`) | pa-plan-contribute |

Allowed values that come up most:

- `tm1_artifact_type` (open and lookup): `cube`, `view`, `dimension`, `hierarchy`,
  `set`. `list_artifacts` uses capitalised forms.
- `paw_artifact_type`: `dashboard` (book, sheet, report), `workbench`, `plan`,
  `application`.
- `perspective_name`: `pa-home`, `modeling-home`, `pa-plan`, `pa-reports`,
  `pa-administration`.
- `chart_type`: `Bar`, `Line`, `Area`, `Pie`, `Cube view`, `exploration`.
- `calculation_type`: Sum, Average, Minimum, Maximum, Median, Aggregate, Rank,
  Absolute Value, Percent Total, Percent Parent, Percent Of, Percent Change,
  Subtraction, Multiplication, Division.

Commands with no parameters (`chart_insights`, `impact_analysis`, `swap`, `copy`
and so on) act on whatever is selected in PAW at that moment.

Preconditions PAW enforces itself (verified on PAoC 2.1.23):

- **A selected database.** `open_tm1_artifact` fails with "you have not
  specified a search context" until `select_database` has run ("Work with
  database X"). Always ship `select_database` alongside the TM1 commands.
- **Edit mode for anything that adds a widget.** Opening a cube in a book makes
  PAW ask "switch to edit mode and continue?" The change stays in the session
  until someone saves the book.
- **The perspective.** PAW refuses a dashboard command sent from another
  perspective ("You cannot run the command on this perspective"), even when the
  model ignores the guideline's own perspective check. The guideline check only
  produces a friendlier message.

**Provenance.** IBM documents only `open_tm1_artifact`. The rest come from a working
reference agent (WxO-portable-template) whose templates mirror the default PA
agent. Live-tested on PAoC 2.1.23 with a custom agent: `open_paw_artifact`,
`open_tm1_artifact`, `switch_to_perspective` and `select_database` (its
`"type"` key works). wxO's import flags `open_paw_artifact` and
`open_tm1_artifact` as conflicting, because both list a bare "Open" phrase.
Live-tested in the reference agent: `chart_insights`, `impact_analysis`, `outlier_analysis`,
`create_sandbox`, plus navigation and view changes. The admin commands, plan
workflow, `member_calculation`, `summarize` and `annotation_summary` have no recorded
test. Verify any of these in your PAW before relying on it (Step 4).

## Step 2. Choose how to deliver it

**Recommended: one guideline per command, with the agent replying in bare JSON.**
This is what the reference agent runs in production. Add the command's guideline to
the agent's `guidelines:` list exactly as it appears in the reference:

```yaml
guidelines:
  - display_name: open_tm1_artifact
    condition: |
      If {data_context.userInformation.perspective} is not equal to dashboard, respond
      "Sorry I cannot perform this action on this perspective"
      The user wants to open an object from a database (cube, view, dimension,
      hierarchy, or set). Common phrasings include: "Open cube X", "Open view Y" ...
    action: |
      Parameters: artifact_name (required) ... tm1_artifact_type (required): one of
      cube, view, dimension, hierarchy, or set.
      JSON template, return this exact structure, replacing only the placeholders:
      {"user_defined": {"command": "open_tm1_artifact",
                        "artifact_name": ["<artifact_name_provided_by_user>"],
                        "tm1_artifact_type": "<tm1_artifact_type_provided_by_user>"},
       "response_type": "user_defined"}
      Rules: exact format, no extra fields; collect all required parameters first;
      preserve the user's spelling and casing; return the JSON with no other text,
      commentary or markdown wrapping.
```

Then add this routing rule to `instructions:`. Without it, models tend to "deliver"
the JSON through a tool, and the turn fails or hangs:

```text
For an explicit PAW interface operation, follow the matching command guideline and
return only its bare user_defined JSON. Make NO tool call of any kind. PAW renders
the result itself by intercepting the JSON. Never pass command JSON to a tool,
including any approval or UI-rendering tool.
```

**Option B: wxO Actions** (Build → agent → Actions → New action, with example
phrases, and the JSON pasted into the step's JSON editor as
`{"generic":[{"response_type":"user_defined","user_defined":{...}}]}`). This is the
route IBM documents. Use it for fixed phrase-to-command mappings. To restore the
default PA agent's actions in one go, upload IBM's actions JSON in Actions → Global
settings → Upload/Download. Download your existing actions first: upload may replace
rather than merge. The file must be UTF-8 without a BOM and contain no tabs or
newlines.

**Not recommended: a Python tool returning the payload in `_meta`.** Tool-returned
`user_defined` widgets go through a different event path, and PAW's handling of it
is unverified. Use the guideline route unless you've tested this in your PAW.

## Step 3. Wrap commands for your own use cases

You can't add commands, but you can combine your logic with PAW's commands:

- **Analysis, then show.** The agent answers a variance question with MCP tools,
  then the user asks "open it", which emits `open_tm1_artifact` with the cube or
  view the analysis used.
- **Context-filled parameters.** Fill `artifact_name` from `data_context`, e.g.
  `selectedCubeName`, so "open this in a new view" needs no typing.
- **Agent-built objects.** Create a view with MCP `save_mdx_view`, then open it with
  `open_tm1_artifact` and `"tm1_artifact_type": "view"`.
- **Your own guideline names and phrasings.** A guideline called "Open budget
  pack", triggered by "show me the budget pack", can emit
  `open_paw_artifact` / `dashboard` / `Budget Pack`. Only the payload is fixed.

Return one command per reply, with nothing else in it. Every reference template
requires the bare JSON alone. Several commands in one reply, or JSON mixed with
prose, are untested.

## Step 4. Test in PAW

1. Open PAW in the perspective the command is gated on, with chat on the custom
   agent.
2. Send the trigger phrase. Expect PAW to act, with no visible JSON in the chat.
   `references/paw-responses.md` lists the confirmations and refusals PAW
   returns, and how to tell PAW's messages from the agent's.
3. If the raw JSON shows up in chat, PAW didn't recognise it: compare against the
   template field by field, including `type` vs `response_type` and array vs
   string.
4. If nothing happens and no JSON shows, check the reasoning trace for a tool call.
   The model probably wrapped the command in a tool (Step 2 routing rule).
5. If PAW shows a server error such as `...CommandService not found`, run the same
   phrase with the default PA agent. If it fails there too, it's a PAW server
   problem, not your agent.
6. To capture an undocumented or changed payload, point a perspective at the
   default agent, open DevTools → Network, trigger the feature, and read the
   `user_defined` body in the chat response. Record what you find in
   `references/command-templates.md` along with the PAW version.

## Step 5. Report honestly

When you build or change actions, say which commands you verified in PAW and which
you only configured. State the PAW version. Never describe an untested command as
working because the template exists.
