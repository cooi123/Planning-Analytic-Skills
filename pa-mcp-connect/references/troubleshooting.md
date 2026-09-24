# Troubleshooting

A failing PA MCP connection gives you one signal: a status code. The codes are not
intuitive — `500` usually means the server is broken rather than that you sent
something bad, and `404` is far more often a version mismatch than a typo. Work from
the code rather than from a hypothesis.

## Contents
- [Decision tree](#decision-tree)
- [The control test](#the-control-test)
- [Code by code](#code-by-code)
- [Worked example](#worked-example)
- [Ruling things out cleanly](#ruling-things-out-cleanly)

## Decision tree

```
Send: POST <url>  initialize  (with credentials)
│
├─ 200 + serverInfo ............ working. Run tools/list to confirm tools appear.
│
├─ 401 ......................... credential missing/invalid.
│                                Read WWW-Authenticate for accepted schemes.
│                                No header at all? Client tried OAuth discovery.
│
├─ 403 ......................... authenticated, not entitled.
│                                PA Agent add-on missing, or user lacks rights.
│
├─ 404 ......................... path wrong. Auth is FINE — you got past it.
│                                Probe both version shapes (cube/analysis vs
│                                ibm-pa-tools). Check for server/mcp, which
│                                never exists. Confirm the add-on is installed.
│
├─ 500 ......................... run THE CONTROL TEST before touching credentials.
│                                Blanket 500 => server auth tier is down.
│                                500 on one path only => that service is unhealthy.
│
├─ 000 / refused / timeout ..... wrong port, or service not running.
│                                Try other ports. Check the reservation is up.
│
└─ HTML login page ............. you hit the PAW web tier, not the MCP service.
                                 The MCP port is usually different.
```

## The control test

The highest-value diagnostic here, because it separates two situations that look
identical from the client: your credential is wrong, versus the server cannot
evaluate credentials at all.

```bash
H=https://your-host:port
printf "real creds, real path : "; curl -s -o /dev/null -w "%{http_code}\n" \
  -u 'real:creds' -X POST -H 'Content-Type: application/json' -d '{}' \
  "$H/api/v0/agentic-ai/cube/mcp"
printf "WRONG creds, real path: "; curl -s -o /dev/null -w "%{http_code}\n" \
  -u 'bogus:bogus' -X POST -H 'Content-Type: application/json' -d '{}' \
  "$H/api/v0/agentic-ai/cube/mcp"
printf "real creds, FAKE path : "; curl -s -o /dev/null -w "%{http_code}\n" \
  -u 'real:creds' -X POST -H 'Content-Type: application/json' -d '{}' \
  "$H/api/v0/totally/made/up/path"
printf "no auth at all        : "; curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST -H 'Content-Type: application/json' -d '{}' \
  "$H/api/v0/agentic-ai/cube/mcp"
```

Interpretation:

| Pattern | Conclusion |
|---|---|
| Wrong creds → `401`, fake path → `404` | Server is discriminating properly. Your codes are meaningful. |
| **All three identical (`500`)** | Server evaluates neither credentials nor routes. Auth tier is down. Escalate; stop editing config. |
| No-auth → `401` but authenticated → `500` | Gateway challenges correctly, then the backend fails. Still server-side. |

That third row is the giveaway. A server that returns the same `500` for a
deliberately invented path as for a real one is not reading the path, which means it
never reached credential checking either.

## Code by code

### 401
Read `WWW-Authenticate` — it lists accepted schemes verbatim. Confirm the deployment
matches the credential type (a SaaS bearer will not work on PAoC). For basic auth,
decode the base64 and check it is the password you think. If the header is absent
entirely, the client fell back to OAuth discovery, which PA rejects.

### 403
You are authenticated. Either the PA Agent add-on is not installed, or the account
lacks rights to the agentic-AI surface. Neither is fixable from the client.

### 404
**Auth succeeded** — a `404` is proof the credential passed. Do not touch it. Causes,
in likelihood order: version mismatch (`cube`/`analysis` on a 2.1.22+ server, or
`ibm-pa-tools` on an older one); `server/mcp`, which exists on no version; the PA
Agent add-on not installed; missing tenant segment on SaaS; `v1` instead of `v0`.

### 500
Almost always server-side. Run the control test first. If only one path `500`s while
others answer `200`, that single service is unhealthy — report the specific service
rather than a general outage.

### 000 / connection refused
The port is wrong or nothing is listening. On PAoC and TechZone, MCP services
commonly run on a different port from the PAW UI. Intermittent `000` mixed with
`500` suggests a backend crashing and restarting under load.

## Worked example

*Verified on a PAoC TechZone instance — a realistic full sequence.*

Reported: "the MCP endpoints don't work."

1. Unauthenticated `POST` to `:29889/api/v0/agentic-ai/cube/mcp` → `401` with
   `Bearer` / `Basic realm="Harmony LDAP"` / `CAMNamespace`. Host is up and
   challenging. So far consistent with a simple missing credential.
2. With Basic credentials → `500`. Looks like a bad password.
3. **Control test** → wrong credentials `500`, invented path `500`, form login `500`
   with *"An unexpected authentication failure has occurred"*. Identical for a
   made-up user. The server is not evaluating anything; its auth tier is down. The
   credentials are neither confirmed nor refuted.
4. Retrying different passwords, base64 vs `-u`, and tenant vs non-tenant paths all
   returned `500` — as they must, since none of those dimensions were being read.
5. The user supplied a different **port**, `26929`. Same path, same credentials →
   `200`, `Server: uvicorn`, `serverInfo: TM1 Cube Service 1.26.0`, 21 tools.

The port was the only wrong dimension. `:29889` was the PAW web tier, whose auth
backend was independently broken; `:26929` ran the MCP services. Steps 2–4 looked
like an authentication problem throughout and were not.

Two lessons worth carrying: the control test correctly ruled out the credentials
several steps before the real cause surfaced, which stopped a password hunt; and no
amount of client-side variation can fix a wrong port, so when every variation
produces one identical code, question the connection target rather than the
payload.

## Ruling things out cleanly

Probing is cheap and `initialize` is read-only, so vary one dimension at a time and
record the code for each. Say what you verified and what you could not:

> Verified: host reachable, port 26929 serves MCP, `cube` and `analysis` return 200,
> `server/mcp` returns 404. Not verified: whether the credential is valid on
> :29889, because that port returns 500 for all input including invented paths.

That phrasing lets the user act. "It doesn't work, try a different password" does
not, and is wrong here.
