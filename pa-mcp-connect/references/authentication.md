# Authentication

Four credential types reach PA MCP endpoints. They are not interchangeable, and a
credential valid for one deployment is useless on another. Pick by what the user
actually holds, not by what seems most modern — OAuth is the most sophisticated
option and the wrong choice for an unattended agent.

## Contents
- [Choosing](#choosing)
- [Basic username and password](#basic-username-and-password)
- [MCSP API key](#mcsp-api-key)
- [OAuth 2.0](#oauth-20)
- [watsonx Orchestrate](#watsonx-orchestrate)
- [Failure signatures](#failure-signatures)
- [Handling secrets](#handling-secrets)

## Choosing

| Deployment | Unattended agent | Interactive user |
|---|---|---|
| SaaS | MCSP API key → bearer | OAuth authorization-code |
| PAoC / on-prem | Basic (native or LDAP) | Basic, or CAM SSO |
| via watsonx Orchestrate | Basic: wxo key + MCP token | same |

The deciding constraint: **OAuth client-credentials is not supported by PA**. Only
the interactive authorization-code grant exists, so a headless agent cannot obtain a
token without a human in the loop. For automation on SaaS, use an MCSP API key.

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

For PAoC, the agentic platform must support manual client configuration (not
discovery-only), explicit scope definition, and interactive authorization-code
flows. A client that only does dynamic registration cannot connect — which is
exactly what happens when an MCP entry has no `Authorization` header: the client
attempts registration, PA rejects it, and the error mentions `/login` or
registration rather than the missing header.

## watsonx Orchestrate

Basic auth with an unusual pairing — the API key goes in the **username** field:

```
username: <watsonx Orchestrate API key>
password: <token generated for the MCP server in watsonx Orchestrate>
Authorization: Basic base64(<apikey>:<token>)
```

PAW 3.1.9 removed custom watsonx Orchestrate agent support and required PA Agent key
regeneration, so a wxo integration that broke at that upgrade most likely needs a
regenerated key rather than a config change.

## Failure signatures

| Symptom | Cause |
|---|---|
| `401` with `WWW-Authenticate` | Credential missing, malformed, or wrong scheme |
| `401` only after an hour | Bearer token expired |
| `403` | Authenticated but not entitled — add-on or user rights |
| `500` on **every** path including invented ones | Server auth tier down, not your credential |
| Error naming `/login` or client registration | No `Authorization` header; client tried OAuth discovery |
| *"Scope not found"* / *"ApiKey is not valid"* | Wrong MCSP token endpoint, not a bad key |
| Works in browser, fails from client | Session cookie auth vs header auth — the UI logging in does not prove header auth works |

A `500` cannot confirm or deny a credential. When one blocks you, report the
credential as **unverified** — claiming it is wrong sends the user to reset a
password that was never the problem.

## Handling secrets

Keep keys, secrets, and tokens in environment variables or a secret store, never in
committed config. When echoing a config back to a user, leave the credential as a
placeholder. If a credential was sent over plain HTTP — common on PAoC and TechZone
— say so plainly, since it crossed the network in the clear and may warrant a
rotation before the same credential is used anywhere real.
