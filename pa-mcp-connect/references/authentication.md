# Authentication

Five credential types reach PA MCP endpoints. They are not interchangeable, and a
credential valid for one deployment is useless on another. Pick by what the user
actually holds, not by what seems most modern — OAuth is the most sophisticated
option and the wrong choice for an unattended agent.

## Contents
- [Choosing](#choosing)
- [Basic username and password](#basic-username-and-password)
- [PA API key as Basic](#pa-api-key-as-basic)
- [MCSP API key](#mcsp-api-key)
- [OAuth 2.0](#oauth-20)
- [watsonx Orchestrate](#watsonx-orchestrate) (moved to `pa-wxo-agent`)
- [Failure signatures](#failure-signatures)
- [Handling secrets](#handling-secrets)

## Choosing

| Deployment | Unattended agent | Interactive user |
|---|---|---|
| SaaS | PA API key as Basic `apikey:<key>`, or MCSP API key → bearer | OAuth authorization-code |
| PAoC / on-prem | Basic (native or LDAP) | Basic, or CAM SSO |
| wxO agent, production (tools run as the user) | — | OAuth auth-code connection, `live` = member. See `pa-wxo-agent` → `references/wxo-oauth.md` |
| wxO agent calling PA SaaS as a remote MCP toolkit | Basic `apikey:<PA API key>` in a wxO connection (one identity for everyone) | prefer OAuth |
| via watsonx Orchestrate, wxO-issued MCP token | Basic: wxo key + MCP token | same |

The deciding constraint: **OAuth client-credentials is not supported by PA**. Only
the interactive authorization-code grant exists, so a headless agent cannot obtain a
token without a human in the loop. For automation on SaaS, use an MCSP API key.

A wxO agent with users is not headless: each user signs in once from the chat. That
makes OAuth the production choice for agents, because calls run under each user's PA
security and no key sits in a tool. Tested on PA on Cloud; see
`pa-wxo-agent` → `references/wxo-oauth.md`.

## Basic username and password

The default on PAoC, on-prem, and TechZone instances.

```bash
printf 'user:password' | base64      # -> dXNlcjpwYXNzd29yZA==
curl -H "Authorization: Basic dXNlcjpwYXNzd29yZA=="  …
```

`curl -u user:pass` sends exactly this header, so if `-u` fails the base64 form
fails identically — re-encoding is never the fix. When a user offers a
pre-encoded string, decode it and confirm it matches the credential they think they
are sending; a wrong password hidden inside base64 is a common and invisible error.

```bash
printf 'cG06SUJNRGVtMHM=' | base64 -d     # -> pm:IBMDem0s
```

The `WWW-Authenticate` header on a `401` names what the server accepts, for example:

```
WWW-Authenticate: Bearer realm="Service"
WWW-Authenticate: Basic realm="Harmony LDAP", charset="UTF-8"
WWW-Authenticate: CAMNamespace
```

That is a definitive statement from the server about the accepted schemes — read it
rather than guessing. `CAMNamespace` indicates Cognos-backed auth, which may also
need a namespace.

TM1 `IntegratedSecurityMode` determines what is valid: `1` native/basic, `2`/`3`
CAM SSO, `5` IAM.

## PA API key as Basic

*Verified August 2026 on PA as a Service, TM1 12.6.3, tenant URL
`/api/<tenant>/v0/agentic-ai/ibm-pa-tools/mcp`.*

When the endpoint answers an unauthenticated request with

```
WWW-Authenticate: Basic realm="apikey"
```

it wants Basic auth with the **literal username `apikey`** and the PA API key as the
password:

```bash
curl -u "apikey:$PA_API_KEY" -X POST -H 'Content-Type: application/json' …
```

Two variants that look reasonable both failed against the same endpoint:

- `Authorization: Bearer <raw PA API key>`.
- Exchanging the key at IBM Cloud IAM (`iam.cloud.ibm.com`) for a bearer token. It
  returns no token, because a PA API key is not an IBM Cloud IAM key.

So read the realm before reaching for a token exchange. `realm="apikey"` means the
key goes straight into Basic, no exchange.

## MCSP API key

The practical choice for unattended SaaS access. Exchange the key for a JWT:

```bash
curl -s -X POST https://account-iam.platform.saas.ibm.com/api/2.0/apikeys/token \
  -H "Content-Type: application/json" \
  -d '{"apikey":"<MCSP_API_KEY>"}'
# -> {"token":"eyJ…"}   JWT, ~1 hour
```

Use as `Authorization: Bearer <token>` with the tenant path.

The token endpoint has **no account id in the path**. Two plausible-looking variants
both fail with misleading messages: `…/accounts/<acct>/apikeys/token` returns
*"Scope not found"*, and `iam.platform.saas.ibm.com/siusermgr/…` returns *"ApiKey is
not valid"* — which reads as a bad key when the key is fine and the URL is wrong.

Tokens expire in about an hour, so refresh rather than pasting one into a config
file. A config that works for an hour then fails is this.

## OAuth 2.0

Documented for interactive PAW/TM1 REST access; scope **`v0userContext`**. Other
scopes and grant types, **including client-credentials, are not supported**.

1. An Environments/Subscription admin creates an OAuth client in PA Administration →
   **Integrations**. One client at a time; redirect URLs must be allowlisted.
2. Authorization-code flow against `…/oauth2/authorize`, then exchange the code at
   `…/oauth2/token`.
3. Call with `Authorization: Bearer <access_token>`, refreshing as needed.

Prerequisite: PAW **3.1.8+ / 2.1.21+**.

*Tested 2026-10-16 on PA on Cloud (PAW 2.1.23, TM1 11.8) from watsonx Orchestrate:*
one access token worked for the PA MCP toolkit **and** for TM1 REST through PAW
(`{PAW_HOST}/api/{tenant}/v0/tm1/{database}/api/v1/...`). `ActiveUser` returned the
signed-in user. The token is opaque (not a JWT). TM1py needs the Bearer header
re-added after login. The recipe, the TM1py fix and the traps are in
`pa-wxo-agent` → `references/wxo-oauth.md`.

For PAoC, the agentic platform must support manual client configuration (not
discovery-only), explicit scope definition, and interactive authorization-code
flows. A client that only does dynamic registration cannot connect — which is
exactly what happens when an MCP entry has no `Authorization` header: the client
attempts registration, PA rejects it, and the error mentions `/login` or
registration rather than the missing header.

## watsonx Orchestrate

Wiring PA into a wxO agent (OAuth or API-key connections, the MCP toolkit, Python
tools, the wxO-issued MCP token) lives in the **`pa-wxo-agent`** skill, in the
`wxo-paw` group: `references/wxo-oauth.md` and `references/api-key-connection.md`.

## Failure signatures

| Symptom | Cause |
|---|---|
| `401` with `WWW-Authenticate` | Credential missing, malformed, or wrong scheme |
| `401` only after an hour | Bearer token expired |
| `401` with `Basic realm="apikey"` | Send Basic `apikey:<PA API key>`. Bearer and IAM exchange both fail here |
| Works in the wxO test chat, fails once deployed | Credentials set on `draft` only. Set them on `live` too |
| `403` | Authenticated but not entitled — add-on or user rights |
| `500` on **every** path including invented ones | Server auth tier down, not your credential |
| Error naming `/login` or client registration | No `Authorization` header; client tried OAuth discovery |
| *"Scope not found"* / *"ApiKey is not valid"* | Wrong MCSP token endpoint, not a bad key |
| Works in browser, fails from client | Session cookie auth vs header auth — the UI logging in does not prove header auth works |
| wxO toolkit import: `Gateway creation failed: 502 ... 401` | OAuth connection has no stored token. Set draft to team, click Connect, then import |
| TM1py with a Bearer token through PAW: first call works, later calls `401` | TM1py drops the `Authorization` header after login. Re-add it; see `pa-wxo-agent` → `references/wxo-oauth.md` |

A `500` cannot confirm or deny a credential. When one blocks you, report the
credential as **unverified** — claiming it is wrong sends the user to reset a
password that was never the problem.

## Handling secrets

Keep keys, secrets, and tokens in environment variables or a secret store, never in
committed config. **A deployed tool (wxO Python tool, chart or dashboard tool) never
contains a credential**: it reads one from its platform connection at run time
(`connections.oauth2_auth_code(...)` or `connections.basic_auth(...)` in wxO).
Environment variables are for local scripts and deploy scripts, not for tool code. When echoing a config back to a user, leave the credential as a
placeholder. If a credential was sent over plain HTTP — common on PAoC and TechZone
— say so plainly, since it crossed the network in the clear and may warrant a
rotation before the same credential is used anywhere real.
