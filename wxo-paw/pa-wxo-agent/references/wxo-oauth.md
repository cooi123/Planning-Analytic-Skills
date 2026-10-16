# OAuth from watsonx Orchestrate to Planning Analytics (production pattern)

Use this when a wxO agent's tools (the PA MCP toolkit, Python tools that call the
TM1 REST API, or tools that build PAW content) must run **as the signed-in user**
with no API key in code.

## What was tested, and where

*Tested 2026-10-16 on PA on Cloud / TechZone: PAW 2.1.23, TM1 11.8.02800.9, wxO
ADK 2.12.0, TM1py 2.4.1.* **Not yet tested on PA SaaS**: the flow is documented
for SaaS, but confirm it on the tenant before promising it.

| Check | Result |
|---|---|
| Import the PA MCP toolkit with the OAuth connection (wxO calls `tools/list`) | pass |
| MCP `get_available_tm1_servers` | pass |
| Raw TM1 REST `GET .../api/v1/ActiveUser` with `Authorization: Bearer` | pass; returns the PA user who signed in |
| TM1py access-token mode | pass, **only after re-adding the header** (see below) |
| Per-user sign-in from the live chat (member credentials) | **not run end to end yet** |
| PAW dashboard API (`idvisualizations`) with the OAuth token | not tested |

One user sign-in gives one token that works for the MCP toolkit **and** for Python
tools calling TM1 REST through PAW. `ActiveUser` is the real user, so TM1 security
applies to them.

## Production rules

1. **No credential in code, ever.** Tool source, toolkit and agent YAML, agent
   instructions and `requirements.txt` hold no API key, client secret, token,
   password, or URL with credentials in it. Placeholders such as `__PA_MCP_URL__`
   are fine; a value substituted into the file at deploy time is still a hardcoded
   credential if it is a secret.
2. **Tools get credentials from the wxO connection.** Declare
   `expected_credentials` on the `@tool` and read with
   `connections.oauth2_auth_code(APP_ID)` (or `connections.basic_auth(APP_ID)` for an
   API-key connection). Don't read secrets from environment variables inside a
   tool: the deployed tool doesn't run where your `.env` is.
3. **Prefer OAuth auth-code with `live` = member.** Each user signs in and every
   call runs under their PA security. Use a team credential (one identity for
   everyone) only for draft testing, toolkit import, or a job that has no user.
4. **HTTPS only in a customer environment.** On plain HTTP the sign-in and the
   token cross the network in the clear.
5. **Least privilege on the toolkit.** List the MCP tools the agent needs
   (`tools: [get_available_tm1_servers, execute_mdx_and_get_view]`) rather than
   `["*"]`, which also hands over `delete_tm1_cube`, `create_tm1_process` and
   process execution. Mark read tools `ToolPermission.READ_ONLY`.
6. **Never return or log the token.** Redact it (and any `Bearer …` string) from
   errors before a tool returns them. Add a test that asserts no token text
   appears in the tool output.
7. **Secrets live in two places only**: the secret store or `.env` the deploy
   script reads, and the wxO connection. The deploy script passes them straight
   to the CLI and redacts them from what it prints.

If OAuth is not possible (an unattended job with no user), the fallback is a PA
API key in a `kind: basic` wxO connection ([`api-key-connection.md`](api-key-connection.md)), read
with `connections.basic_auth`. The key still never appears in tool code.

## How to wire it

### Endpoints

PAW issues and checks the token, so call TM1 **through PAW**, not on a TM1 engine
port.

| Purpose | URL |
|---|---|
| Authorize | `{PAW_HOST}/oauth2/authorize` |
| Token | `{PAW_HOST}/oauth2/token` |
| TM1 REST | `{PAW_HOST}/api/{tenant}/v0/tm1/{database}/api/v1/...` |
| MCP | `{PAW_HOST}/api/{tenant}/v0/agentic-ai/ibm-pa-tools/mcp` |

On PA on Cloud, `{PAW_HOST}` is the host and port the PAW UI runs on.

### Connection

```yaml
spec_version: v1
kind: connection
app_id: pa_oauth
environments:
  draft:
    kind: oauth_auth_code_flow
    type: team          # one person clicks Connect; used for toolkit import and draft chat
    server_url: __PA_BASE_URL__
  live:
    kind: oauth_auth_code_flow
    type: member        # each user signs in; calls run as them
    server_url: __PA_BASE_URL__
```

### Setup order

The order matters, because the toolkit import needs a live token.

1. Create the connection in wxO, then open it **in the wxO UI** and copy its
   callback URL. The ADK docs show the callback only as an API path. The UI shows
   the real URL.
2. In PA Administration > Integrations, create the OAuth client with that callback
   as the redirect URL. It must match character for character.
3. Set the credentials from the secret store, for `draft` and `live`:
   ```bash
   orchestrate connections set-credentials -a pa_oauth --env draft \
     --client-id "$PA_CLIENT_ID" --client-secret "$PA_CLIENT_SECRET" \
     --auth-url "$PAW_HOST/oauth2/authorize" --token-url "$PAW_HOST/oauth2/token" \
     --scope v0userContext
   ```
   The installed ADK takes `--auth-url`. Some docs show `--authorization-url`,
   which it rejects.
4. In the wxO UI, open the connection's **draft** environment, click **Connect**
   and sign in to PA.
5. Import the toolkit, then the tools, then the agent.

### Python tool calling TM1 REST

```python
import requests
from TM1py import TM1Service
from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType
from ibm_watsonx_orchestrate.agent_builder.tools import ToolPermission, tool
from ibm_watsonx_orchestrate.run import connections

APP_ID = "pa_oauth"

@tool(permission=ToolPermission.READ_ONLY,
      expected_credentials=[{"app_id": APP_ID, "type": ConnectionType.OAUTH2_AUTH_CODE}])
def who_am_i(database: str) -> str:
    """..."""
    token = connections.oauth2_auth_code(APP_ID).access_token
    root = f"{PA_BASE}/api/{TENANT}/v0/tm1/{database}"   # no credential in this URL

    # Raw OData: nothing special
    r = requests.get(f"{root}/api/v1/ActiveUser",
                     headers={"Authorization": f"Bearer {token}"}, timeout=30)

    # TM1py: one service per tool call, header re-added
    tm1 = TM1Service(base_url=root, access_token=token, ssl=True,
                     re_connect_on_session_timeout=False)
    tm1._tm1_rest.add_http_header("Authorization", f"Bearer {token}")
    try:
        ...
    finally:
        tm1.logout()
```

`PA_BASE` and `TENANT` are deploy-time placeholders, not secrets. The ADK also
documents `creds.url` (the connection's `server_url`) as a way to avoid even those,
but that wasn't used in the PA test.

## Traps

| Symptom | Cause | Fix |
|---|---|---|
| `orchestrate toolkits import` fails: `Gateway creation failed: 502 ... 401 Unauthorized` | wxO calls `tools/list` during import and no token is stored | Set draft to team, click Connect, then import. Switch to member afterwards if needed |
| Toolkit stops working after the draft environment is deleted | Deleting it deletes the stored token | Re-run the connection and credentials steps and click Connect. The toolkit, tools and agent need no redeploy |
| TM1py: `tm1.version` works, every later call returns `401` | TM1py 2.4.1 removes the `Authorization` header after login (`RestService._start_session`, `finally` block) and relies on the `TM1SessionId` cookie. The PAW gateway wants the Bearer on every request | Re-add the header after creating the service. `_tm1_rest` is private: recheck on every TM1py upgrade, and keep a test that fails without the line |
| TM1py: works, then a single `401` breaks every call after it | On a `401` TM1py calls `connect()`, which strips the header again, so the retry and every later call go out without it | Pass `re_connect_on_session_timeout=False` so the `401` surfaces, and create a fresh `TM1Service` (with a fresh token from the connection) per tool call |
| Can't read the user, issuer or expiry from the token | The access token is opaque, not a JWT | Ask TM1: `GET .../api/v1/ActiveUser` |
| Every PAW path answers `401 WWW-Authenticate: Bearer realm="Service"`, even invented ones | That's the unauthenticated answer for any path | An unauthenticated probe can't prove the MCP path is right. Test it once a token is in place |
| Endpoint check before anyone signs in | | `GET /oauth2/authorize` without a client id returns a PA page with `invalid_request: Missing parameter: client_id`; `POST /oauth2/token` without credentials returns `invalid_client`. Both mean you have the right endpoints |
| Everyone in draft chat runs as one user | Draft is `type: team`, so calls use the token of whoever clicked Connect | Expected. Use live with member for per-user security |

## Review checklist for a tool before it ships

```bash
# No credential-shaped literals in tool code or YAML
grep -rnEi "apikey|api_key|client_secret|password|Bearer [A-Za-z0-9]|Basic [A-Za-z0-9+/=]{12,}" wxo/tools wxo/toolkits wxo/agents
# Every tool that calls PA declares the connection it uses
grep -rn "expected_credentials" wxo/tools
```

- [ ] The tool reads its credential from `connections.*`; no key, secret or token in code or YAML
- [ ] Draft is team for import; live is member, unless the job has no user
- [ ] The URLs are HTTPS
- [ ] The toolkit lists named tools, not `"*"`; read tools are `READ_ONLY`
- [ ] Tool output and errors are redacted; a test proves no token text leaks
- [ ] TM1py tools re-add the Bearer header, disable reconnect, and log out in `finally`
- [ ] Credentials are set on both `draft` and `live`; rotation updates both
