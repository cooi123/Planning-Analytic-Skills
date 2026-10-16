---
name: paw-dashboard-api
description: >-
  Create, read, clone and delete Planning Analytics Workspace (PAW) books,
  dashboards and widgets from code through the REST APIs on PA as a Service:
  classic books with grid widgets (TM1 Contents API) and rich dashboards with bar,
  line and column charts, selectors and synced cube viewers (idvisualizations
  API). Covers authentication with a PA API key, building the API URL from a PAW
  browser link, choosing a safe database on a shared tenant, probing a cube for
  real data before building, the payload shape of each widget, and cleanup. Use
  for "create a PAW dashboard with the API", "build a book from a script", "add a
  chart widget programmatically", "what widgets can I create through the API",
  "clone a PAW book", "generate dashboards from Python", "idvisualizations",
  "Contents('Applications')", "my API-built chart is empty", "queryState", or
  "test the dashboard API on my tenant".
user-invocable: true
---

# PAW dashboard API

Build PAW books and dashboards from code, and know before you start which parts
are solid and which are guesses. Two of the three APIs involved are
**undocumented and internal**: IBM can change them in any PAW release. Say so
to the user, and prefer cloning a book built by hand in PAW over hand-writing
widget JSON.

Read `references/api-map.md` for endpoints and error meanings. Read
`references/widget-payloads.md` before writing any widget JSON.

## Guardrails

- **Credentials.** Never ask for a key in chat. It comes from an environment
  variable or an env file the user names. Never print it, never put it in a
  command line, and redact it from any output you show.
- **No hardcoded keys in production tools.** The env-var key is for local scripts
  and tests. A tool an agent deploys never holds a key; see "Production tools"
  below.
- **Writes only when asked.** Discovery (steps 1 to 4) is read-only. Creating a
  view, book or dashboard writes to the tenant, so do it only when the user has
  asked for a build or a test.
- **Shared tenant.** A PA tenant holds many people's databases. Before writing,
  list databases with owner and status (`/pakate/v0`) and use one the user
  created or named. Never write to someone else's database, and never run a
  script that deletes-then-recreates objects by name (for example a demo
  builder) until you have read which names it deletes.
- **Throwaway names.** Use a distinct prefix such as `ZZ_API_Test_`, record every
  id you create, and delete exactly those at the end. Dashboards under
  `/shared/` are visible to everyone on the tenant until deleted.
- **Run untrusted code safely.** If you import helper code from a downloaded
  repo, read it first, keep it in its own directory, run Python with `-I`, and
  add the helper directory to `sys.path` explicitly.

## What you can create

Status means what was observed on a real tenant.

| Widget | API | Observed |
|---|---|---|
| Grid on a saved cube view (`GridWidget`) | TM1 Contents | Created and read back |
| Bar chart (`com.ibm.vis.rave2bundlebar`) | idvisualizations | Created and read back |
| Line chart (`com.ibm.vis.rave2line`) | idvisualizations | Created and read back |
| Column chart (`com.ibm.vis.rave2bundlecolumn`) | idvisualizations | Created and read back |
| Selector (`paselector`) | idvisualizations | Created and read back |
| Synced cube viewer (`pacubeviewer`) | idvisualizations | Created and read back |

**"Created and read back" is not "renders correctly".** The server accepts the
JSON. Only a person looking at the book in PAW can confirm the charts draw and
the selectors filter. Ask the user to check, and don't open a browser for them
unless they ask.

Not tested: other visualisation types (pie, scatter, map, KPI and so on), logos,
sections, and Plan application workflows (`pacontent`, `plan-service`). To get
the JSON for a type this skill doesn't cover, have the user build one in PAW,
`GET` it, and copy the widget object.

## Workflow

### 1. Get the connection details

From the user's PAW URL, read the region (the host prefix) and the tenant id
(the `tenantId` query parameter). Then:

- `{PAW_HOST}` = `https://{region}.planninganalytics.saas.ibm.com`
- `{API}` = `{PAW_HOST}/api/{tenantId}/v0`

The API key is a **PA API key**. A shorter IBM Cloud style key returned `401`
on every endpoint, so if you get `401` first check which kind of key it is.

### 2. Authenticate (read-only)

`GET {API}/rolemgmt/v1/users/me` with HTTP Basic, username `apikey`, password
the key. `200` returns the signed-in user and sets a `paSession` cookie. Fix any
`401` before going further; see the triage table in `references/api-map.md`.

**Keep that session.** The dashboard API at the host root does not accept the API
key; it only accepts the `paSession` cookie from this login. Use one HTTP session
(`requests.Session()`, or Postman's cookie jar) for the login and every dashboard
call. A dashboard call made without that cookie returns `401 AUTH_REQUIRED`.

### 3. Pick a database

`GET {API}/pakate/v0` lists databases with `server_name`, `server_status` and
`createdBy`. Choose a running one the user owns or named. If unsure, ask.

### 4. Inspect the cube and probe for data

List cubes with their dimensions in order, then run a small MDX query for the
slice the widgets will use. **Do this before building.** An MDX query that omits
dimensions falls back to each dimension's default member, which is often empty
in a sparse cube, and the widgets then look blank. Take real member names from
the cube or from the user's existing scripts and views, not from guesses.
Confirm there are non-null values.

### 5. Build

1. Create an MDX view the grid widgets can bind to.
2. Classic book: `POST` a stub, then `PATCH` its sheets with `GridWidget`
   entries. Both steps are needed.
3. Dashboard: `PUT` a stub, then `PUT` the full content. Both steps are needed.
4. `GET` each one back and check it returns `200` with content.

`scripts/smoke_test.py` runs steps 1 to 4 end to end from a config file. It
needs the helper functions from a clone of the `create_paw_demo.py` builder; see
the script header.

### 6. Hand over for a visual check

List what was created and where. Say plainly that rendering is unconfirmed.
Ask the user to open each one and report anything that is blank, errors, or
doesn't filter. Fix and rebuild from what they report.

### 7. Clean up

Delete only what you recorded: dashboards, then classic books, then views
(books bind to views). Report the status of each delete.

## Common failures

| Symptom | Cause | Fix |
|---|---|---|
| `401` everywhere | Wrong tenant or region, or not a PA API key | Re-derive from the PAW URL; generate a PA key in PAW |
| Charts and grids blank, no error | Slice has no data, or default members used | Probe the slice (step 4); use real member names |
| `400` reading a classic book with `$expand=Sheets` | `Sheets` is not a navigation property | Plain `GET` of the book returns sheets inline |
| `404` on the dashboard API | Used `{API}` instead of `{PAW_HOST}` | `idvisualizations` is at the host root |
| `PUT` content returns `201` but PAW shows an empty tab | Content built for the wrong version or malformed `queryState` | Clone a hand-built book instead (see payloads) |
| Selector shows nothing | Root member does not exist in that hierarchy | Use a member that exists; check spelling and case |

## Production tools

When this skill's code becomes a tool an agent runs (a wxO Python tool that
builds a chart or book):

- **The credential comes from the platform connection, never from the code.**
  With OAuth, `connections.oauth2_auth_code(APP_ID).access_token`. With an API
  key, put it in a `kind: basic` wxO connection and read
  `connections.basic_auth(APP_ID)`. Declare `expected_credentials` on the tool.
- **Prefer OAuth with member credentials**, so the book is created as the user
  and their PA security applies. The recipe and its traps are in
  `references/wxo-oauth.md` in the `pa-wxo-agent` skill (`wxo-paw` group).
- **What is tested, and what isn't.**
  - Bearer OAuth tokens on TM1 REST through PAW (`{API}/tm1/...`): tested on PA
    on Cloud. That covers classic books, views and cube probes.
  - Bearer tokens on the dashboard API (`{PAW_HOST}/idvisualizations`): **not
    tested**. On SaaS, that API rejects the API key and accepts only the
    `paSession` cookie. Before shipping a chart tool, run one read
    (`GET /idvisualizations/r/v2/content/shared/`) with the user's token. If it
    returns `401`, call `{API}/rolemgmt/v1/users/me` with the token first, in the
    same session, and reuse the cookie.
- **Create, don't replace.** A tool must not delete-then-recreate by name. Give
  it the narrowest action it needs, and return ids, never credentials.
- Run the review checklist in `pa-wxo-agent/references/wxo-oauth.md` before it ships.

## Reuse the Postman collection

The `PAW books & dashboards (undocumented API)` folder in the PA SaaS Postman
collection mirrors steps 2 to 7 with the requests that were verified. It can
clone a book but cannot author chart widgets, because `queryState` is a
compressed blob; use `scripts/smoke_test.py` for that.
