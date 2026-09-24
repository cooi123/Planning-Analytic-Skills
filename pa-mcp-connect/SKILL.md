---
name: pa-mcp-connect
description: >-
  Connect an MCP client to IBM Planning Analytics agentic-AI endpoints, and diagnose
  connections that fail. Covers the endpoint split at PAW 2.1.22 / 3.1.9 (discrete
  cube + analysis endpoints before, unified ibm-pa-tools after), the three
  authentication paths (OAuth, MCSP API key, basic username/password), and a
  status-code triage tree. Use for "connect to the PA MCP server", "add PA tools to
  Claude/Cursor/watsonx Orchestrate", "my PAoC-server MCP won't connect", "MCP
  returns 401/403/404/500", "which MCP endpoint do I use", "the tools aren't showing
  up", "configure mcpServers for Planning Analytics", "TM1 MCP tools", "agentic-ai
  endpoint", "PA Agent add-on", or whenever an MCP entry pointing at a
  planninganalytics.saas.ibm.com or PAW host misbehaves.
user-invocable: true
---

# PA MCP connect

Get a working MCP connection to Planning Analytics, or find out precisely why one
is broken. The hard part is never the JSON config — it is that four independent
things must all be right at once, and every one of them fails with a different
status code:

| Dimension | Wrong value looks like |
|---|---|
| **Host *and port*** | connection refused, or a login page instead of MCP |
| **Endpoint path** | `404` |
| **Version-correct path** | `404` on a server that used to work |
| **Auth method + credential** | `401`, `403`, or a blanket `500` |

Work the dimensions in that order. Guessing at credentials while the port is wrong
wastes the most time, and it is the most common way this goes wrong.

## Step 0. Establish the facts before editing any config

Ask for, or infer, these four things. Do not start writing `mcpServers` entries
until you have them — a config written against assumptions produces a `500` that
looks like an auth problem and sends you down the wrong path.

1. **Deployment**: PA as a Service (SaaS), PA on Cloud (PAoC), or local/on-prem.
   This decides whether the tenant id belongs in the URL.
2. **PAW version**. The endpoint names changed at **2.1.22 / 3.1.9**. If unknown,
   probing both shapes settles it in one command (Step 2).
3. **Whether the PA Agent add-on is installed.** The agentic-AI routes only exist
   with it. Without it, every path returns `404` no matter how good the credentials.
4. **Which credential the user actually holds**: an OAuth client id+secret, an MCSP
   API key, a watsonx Orchestrate key+token, or a plain username and password.

## Step 1. Build the URL

Read `references/endpoints-by-version.md` for the full matrix, the deprecation
detail, and the tenant-id rules. The short version:

**PAW 2.1.22 / 3.1.9 and later — one unified endpoint:**
```
SaaS:        https://<PAW_HOST>/api/<PAW_TENANT_ID>/v0/agentic-ai/ibm-pa-tools/mcp
PAoC/local:  https://<PAW_HOST>/api/v0/agentic-ai/ibm-pa-tools/mcp
```

**Before 2.1.22 / 3.1.9 — discrete endpoints, one per tool family:**
```
.../v0/agentic-ai/cube/mcp        cube data, MDX, exploration, impact/outlier analysis
.../v0/agentic-ai/analysis/mcp    TurboIntegrator process management
```

There is no `server/mcp`. It appears in circulated config snippets and returns
`404` on every version — if you see it in a user's config, that alone explains the
failure.

On PAoC the tenant segment is **optional**: with and without it resolve to the same
service. On SaaS it is **required** — the gateway will not route without it.

## Step 2. Probe before you configure

`scripts/probe-mcp.sh` performs the MCP `initialize` handshake against every
candidate path and reports which ones answer, with the server name and version. Run
it first. It turns a vague "it doesn't work" into a specific status code in about
ten seconds, and it is safe — `initialize` and `tools/list` are read-only.

```bash
scripts/probe-mcp.sh --host https://paw.example.com --basic 'user:pass'
scripts/probe-mcp.sh --host https://eu.planninganalytics.saas.ibm.com \
                     --tenant ABCD1234 --bearer "$PA_TOKEN"
scripts/probe-mcp.sh --url https://paw.example.com/api/v0/agentic-ai/cube/mcp \
                     --basic 'user:pass' --tools
```

A healthy endpoint returns `200` with an SSE body containing `serverInfo`. Anything
else, go to Step 4.

**Ports deserve their own suspicion.** On PAoC and TechZone instances the MCP
services frequently listen on a *different port* from the PAW web UI. A confirmed
case: PAW UI on `29889`, MCP services on `26929`. The UI port answered every
authenticated request with a blanket `500` because its auth backend was
independently broken, which read exactly like bad credentials — the credentials
were fine, the port was wrong. If the user gives you a port that serves an HTML
login page, treat the MCP port as unknown rather than assumed.

## Step 3. Authenticate

Read `references/authentication.md` before configuring anything beyond basic auth —
it has the token endpoints, scopes, prerequisites, and the failure signature of each
method. Choose by what the user holds:

| Credential in hand | Method | Header |
|---|---|---|
| Username + password (PAoC, on-prem, native/LDAP) | Basic | `Authorization: Basic base64(user:pass)` |
| MCSP API key (SaaS) | Exchange for a JWT, ~1h TTL | `Authorization: Bearer <token>` |
| OAuth client id + secret | Authorization-code flow, scope `v0userContext` | `Authorization: Bearer <access_token>` |
| watsonx Orchestrate key + MCP token | Basic, key as **username**, token as **password** | `Authorization: Basic base64(apikey:token)` |

Two traps worth stating plainly, because both produce confident-looking configs
that cannot work:

- **A SaaS bearer token will not authenticate against a PAoC or on-prem host.** They
  are separate identity systems. Tokens are not portable between deployments.
- **OAuth client-credentials is not supported.** IBM documents only the interactive
  authorization-code grant. An unattended agent needs a human to complete the flow
  once, then refreshes. If a user wants headless SaaS access, steer them to an MCSP
  API key instead of trying to make client-credentials work.

## Step 4. Triage a failing connection

`references/troubleshooting.md` has the full tree with worked examples. The
status code tells you which dimension is wrong — this mapping is the highest-value
thing in the skill, because the codes are not intuitive:

| Code | Means | Next move |
|---|---|---|
| **200** + `serverInfo` | Working | Configure it |
| **401** | Reached the server, no/invalid credential | Check the `WWW-Authenticate` header — it names the accepted schemes |
| **403** | Authenticated, not entitled | PA Agent add-on missing, or the user lacks rights |
| **404** | Auth fine, **path** wrong | Wrong endpoint name, or version mismatch — re-probe both shapes |
| **500 on every path** | Server-side auth tier is broken | Not your config — verify with the control test below |
| **000 / refused** | Wrong port, or service down | Probe other ports; check the reservation is running |

**The control test that saves the most time.** When everything returns `500`, send
a request with *deliberately wrong* credentials and to a *made-up* path:

```bash
scripts/probe-mcp.sh --host https://<host> --basic 'real:creds' --control
```

which is the scripted form of:

```bash
curl -s -o /dev/null -w "%{http_code}\n" -u 'bogus:bogus' \
  -X POST -H 'Content-Type: application/json' -d '{}' \
  https://<host>/api/v0/totally/made/up/path
```

A healthy server answers `401` or `404`. If it returns the same `500` as your real
request, the server cannot evaluate credentials or routes at all — the auth backend
is down. Stop tuning the config and tell the user to restart or re-provision the
environment. Without this test you cannot distinguish "wrong password" from "server
broken", and the two look identical from the client. Reporting a server fault as a
credential problem sends the user on a long and fruitless hunt.

## Step 5. Write the config

```json
{
  "mcpServers": {
    "ibm-pa-tools": {
      "type": "streamable-http",
      "url": "https://<PAW_HOST>/api/<TENANT>/v0/agentic-ai/ibm-pa-tools/mcp",
      "headers": { "Authorization": "Basic <base64>" }
    }
  }
}
```

Points that cause silent failures:

- `type` must be `streamable-http` (some clients spell it `http`). The endpoints
  respond over SSE and are **stateless** — no `Mcp-Session-Id` is issued, so do not
  add session handling.
- When `headers.Authorization` is set, most clients **disable OAuth discovery**. A
  wrong static header therefore fails outright rather than falling back.
- With **no** `Authorization` header the client attempts OAuth dynamic client
  registration, which PA rejects. The resulting error mentions registration or
  `/login` and reads like an OAuth problem when the real fix is "add the header".
- Check `disabled` is not `true` — a correct entry that never loads is easy to miss.
- On pre-2.1.22 servers, register **two** entries (cube and analysis); one endpoint
  cannot serve both tool families.

After editing, restart the client and confirm the tools actually appear. A config
that loads without error but exposes no tools is still a failure — verify with
`--tools` rather than trusting a clean startup.

## Step 6. Report honestly

State which dimension was wrong and how you know, and distinguish what you verified
from what you inferred. If a blanket `500` prevented credential validation, say the
credentials remain **unverified** rather than implying they are good. Where a probe
returned `404`, say the route does not exist on that server rather than that the
feature is unavailable.

## Security

These endpoints expose **write and delete** operations against the TM1 model —
`create_tm1_cube`, `delete_tm1_cube`, `create_tm1_process`, `delete_tm1_process`,
`execute_tm1_processes_asynchronously`. Connecting an agent grants all of them.
Flag this when wiring up anything beyond a sandbox, and prefer a
least-privilege service account.

Many PAoC and TechZone instances run **plain HTTP**, so Basic credentials cross the
network unencrypted. Acceptable for a demo box; say so explicitly before anyone
points it at a customer environment.

Keep API keys, client secrets, and tokens in environment variables or a secret
store. Tokens expire — refresh rather than hardcode. When you must echo a config
back to a user, leave the credential as a placeholder.
