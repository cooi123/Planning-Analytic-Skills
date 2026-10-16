---
name: pa-wxo-agent
description: >-
  Build, wire, test and ship a production-ready watsonx Orchestrate agent on IBM
  Planning Analytics: wxO connections (OAuth auth-code per user, or PA API key),
  the PA MCP toolkit, Python tools calling TM1 REST (including TM1py with a Bearer
  token through PAW), writes through approval Flows, agent YAML, instructions and
  guidelines, testing, draft/live deploy, and a pre-production security checklist.
  Use for "build a wxO agent for Planning Analytics", "connect PA to watsonx
  Orchestrate", "OAuth from watsonx Orchestrate to PA", "production-ready PA agent",
  "no hardcoded API key", "orchestrate toolkits import for PA", "Gateway creation
  failed 502", "TM1py access token 401", "agent writes to TM1 safely", "approval
  flow", "agent best practices", or any custom wxO agent that queries or writes
  Planning Analytics data.
user-invocable: true
---

# Build a watsonx Orchestrate agent on Planning Analytics

Build and ship a production wxO agent that queries and writes Planning Analytics
data, with per-user credentials, safe writes through approval Flows, and a
pre-production checklist. This skill covers the full lifecycle: connection setup,
toolkit import, agent definition, testing and deployment.

**What this skill covers:**

- Wiring PA to wxO: OAuth (per-user) or API key (team) connections
- Importing the PA MCP toolkit and Python tools that call TM1 REST
- Agent design: instructions, guidelines, and tool selection
- Safe writes: approval Flows for any TM1 modification
- Testing and deployment: draft to live, with a security review

**Related skills in this group:**

- [`../paw-wxo-context/SKILL.md`](../paw-wxo-context/SKILL.md): Use PAW's
  `data_context` (open cubes, MDX, selected cells) when the agent runs inside PAW
  chat
- [`../paw-wxo-actions/SKILL.md`](../paw-wxo-actions/SKILL.md): Make the agent
  drive the PAW UI (open books, cubes, switch perspective)

**Core skills** (by name, no path): `pa-mcp-connect` for endpoint and auth triage
outside wxO, `pa-agent-query` for correct numbers from cube data.

## Step 0. Establish the facts

Before writing any YAML or importing anything, confirm:

1. **Deployment**: PA as a Service (SaaS), PA on Cloud (PAoC), or local/on-prem.
   This decides the URL structure and whether OAuth is available.
2. **PAW version**. The MCP endpoint changed at 2.1.22 / 3.1.9. Use
   `pa-mcp-connect` to probe if unknown.
3. **PA Agent add-on installed**. The MCP endpoints need it; `pa-mcp-connect` has
   the status codes that tell you it is missing.
4. **User sign-in or unattended**: OAuth auth-code (each user signs in, their PA
   security applies) or API key (one identity for everyone, or a job with no user).
5. **wxO environment**: region, whether you control embedded-chat security (the RSA
   key is set once per instance).

## Step 1. Pick the connection

| Connection type | When to use | Credential flow |
|---|---|---|
| **OAuth auth-code, member** | Production, per-user PA security | Each user signs in; calls run as them |
| **OAuth auth-code, team** | Draft testing, toolkit import | One person signs in; used for all calls |
| **API key, Basic** | Unattended job, or OAuth not available | One PA API key; everyone runs as that identity |
| **wxO-issued MCP token** | A token generated for the MCP server in wxO | wxO API key + MCP token as Basic username:password; see `references/api-key-connection.md` |

**Prefer OAuth auth-code with `live` = member.** Each user's PA identity flows
through to every tool call, so TM1 security applies. Use a team credential only for
draft testing or toolkit import, or an API key for a job that has no user.

Read [`references/wxo-oauth.md`](references/wxo-oauth.md) for the OAuth setup
(endpoints, connection YAML, credentials, tested behaviour, TM1py Bearer-header fix,
and traps). Read [`references/api-key-connection.md`](references/api-key-connection.md)
for the API-key path.

### Setup order (OAuth)

The order matters because toolkit import needs a live token:

1. Create the connection in wxO, copy its callback URL from the UI.
2. Register the OAuth client in PA Administration → Integrations with that callback.
3. Set credentials for `draft` and `live` (`orchestrate connections set-credentials`).
4. In the wxO UI, open the connection's **draft** environment and click **Connect**
   to sign in.
5. Import the toolkit, then tools, then the agent.

See `references/wxo-oauth.md` "Setup order" for the exact commands.

## Step 2. Wire the toolkit and tools

### Least-privilege tool lists

The PA MCP toolkit exposes write and delete operations: `create_tm1_cube`,
`delete_tm1_cube`, `create_tm1_process`, `delete_tm1_process`,
`execute_tm1_processes_asynchronously`. List only the tools the agent needs:

```yaml
kind: mcp
name: pa_tools
tools:
  - get_available_tm1_servers
  - execute_mdx_and_get_view
  - lookup_potential_members
  # NOT "*"
connections: [pa_oauth]
```

Mark read tools `ToolPermission.READ_ONLY` in Python tools.

### Python tools calling TM1 REST

Tools that call the TM1 REST API through PAW (including TM1py) read the credential
from the wxO connection at run time:

```python
from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType
from ibm_watsonx_orchestrate.agent_builder.tools import ToolPermission, tool
from ibm_watsonx_orchestrate.run import connections

APP_ID = "pa_oauth"

@tool(permission=ToolPermission.READ_ONLY,
      expected_credentials=[{"app_id": APP_ID, "type": ConnectionType.OAUTH2_AUTH_CODE}])
def my_tool(database: str) -> str:
    token = connections.oauth2_auth_code(APP_ID).access_token
    # Use token in Authorization: Bearer header
```

For TM1py, re-add the Bearer header after creating the service (see
`references/wxo-oauth.md` "Traps"). No credential goes in the tool code.

## Step 3. Design the agent

Read [`references/agent-best-practices.md`](references/agent-best-practices.md) for:

- **§1. Architecture: what goes where**: which logic lives in the agent, which in
  tools, which in Flows.
- **§2. The agent definition**: YAML structure, LLM choice, style.
- **§3. Instructions and guidelines**: what goes in each, why guidelines are not a
  safety gate, keeping diagnostics out of business answers.
- **§4. Python tools**: structure, error handling, credential access.
- **§5. Numbers the agent can stand behind**: grounding deliverables against tool
  outputs, evidence for driver claims, and `pa-agent-query` for MCP accuracy.
- **§8. Charts, files and rendering in chat**: tools return text, so images and
  files go out as presigned COS links.

Key points:

- Use `context_access_enabled: true` and `context_variables: [data_context]` if the
  agent runs inside PAW chat.
- Gate guidelines on `{data_context.userInformation.perspective}` or `.role` where
  needed.
- Never ask the user for credentials in chat. Tools read them from the connection.

## Step 4. Make writes safe

**Every write to TM1 goes through an approval Flow.** The agent's own `tools:` list
never includes raw write tools. Instead:

1. The agent calls a Flow that shows Yes/No buttons.
2. The write-capable step lives inside that Flow's graph.
3. The user approves or rejects.

Read [`references/agent-best-practices.md`](references/agent-best-practices.md) §6
and [`references/flows-and-approvals.md`](references/flows-and-approvals.md) for:

- Why guidelines are not a safety gate
- The approval Flow pattern
- Flow gotchas (decline branch to END, `.output.value` paths, `map_output` defaults)
- Validating a Flow before it ships
- Known open issue

**Hard rule:** Never ship an agent that writes to TM1 without an approval step. Test
the Flow with a live write before claiming it works.

## Step 5. Test

Read [`references/agent-best-practices.md`](references/agent-best-practices.md) §9
for the test plan. Key tests:

| Test | Expect |
|---|---|
| Single-cell retrieval | Correct number, member names confirmed |
| Variance question | Right sign, right members, computed in MDX |
| "No data" question | Clear "nothing there", not a wrong number |
| Write attempt | Approval Flow shows, write only after Yes |
| Wrong credential | Clear error, no token leak |

Use `pa-agent-query` to build a regression test set. Test in the wxO draft chat
first, then in PAW chat if the agent uses `data_context`.

## Step 6. Deploy and ship

Read [`references/agent-best-practices.md`](references/agent-best-practices.md)
§10–§12 for:

- **§10. Deploying: draft and live**: import order, `orchestrate agents deploy`,
  importing Flows.
- **§11. Known platform issues**: what to watch for, workarounds.
- **§12. Pre-production checklist**: the gate before a customer sees it.

Run the review checklist in `references/wxo-oauth.md` before shipping:

```bash
# No credential-shaped literals in tool code or YAML
grep -rnEi "apikey|api_key|client_secret|password|Bearer [A-Za-z0-9]|Basic [A-Za-z0-9+/=]{12,}" wxo/tools wxo/toolkits wxo/agents
```

- [ ] Tools read credentials from `connections.*`; no key, secret or token in code
- [ ] Draft is team for import; live is member (unless the job has no user)
- [ ] URLs are HTTPS
- [ ] Toolkit lists named tools, not `"*"`; read tools are `READ_ONLY`
- [ ] Tool output and errors are redacted; no token text leaks
- [ ] TM1py tools re-add the Bearer header, disable reconnect, log out in `finally`
- [ ] Credentials set on both `draft` and `live`; rotation updates both
- [ ] Every write goes through an approval Flow; the Flow was tested live
- [ ] Test set passes (use `pa-agent-query` patterns)

## Files in this skill

| File | Purpose |
|---|---|
| `SKILL.md` | This file |
| `references/wxo-oauth.md` | OAuth auth-code setup, tested behaviour, TM1py fix, traps, review checklist |
| `references/api-key-connection.md` | API key connection (team credential, unattended job) |
| `references/agent-best-practices.md` | Architecture, agent definition, instructions, tools, numbers, writes, connections, charts, testing, deploy, issues,  checklist |
| `references/flows-and-approvals.md` | Approval Flow pattern, gotchas, validation, known issue |

## Hard constraints

- **No credential in code, YAML, instructions or substituted values.** Tools read
  from the wxO connection at run time.
- **Never ask for secrets in chat.** The user never types a key, token or password.
- **Writes only through an approval Flow.** The agent's `tools:` list never includes
  raw write tools.
- **Mark untested items.** OAuth not yet tested on SaaS; member sign-in from live
  chat not run end to end; Bearer on the PAW dashboard API untested (stated in
  `wxo-oauth.md`).
- **Never claim a Flow works without a live test.** A Flow that passes import is not
  a working Flow.
- **Redact tokens from errors.** No `Bearer ...` or `Basic ...` string in tool
  output.
- **State what was verified.** Distinguish tested from inferred, working from
  configured.
