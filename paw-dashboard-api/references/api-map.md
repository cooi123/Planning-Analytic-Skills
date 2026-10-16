# API map

`{API}` = `https://{region}.planninganalytics.saas.ibm.com/api/{tenantId}/v0`
`{PAW_HOST}` = `https://{region}.planninganalytics.saas.ibm.com`
`{DB}` = the URL-encoded database name (a space becomes `%20`).

**Two kinds of authentication, observed 2026-10-16:**

- Paths under `{API}` (TM1 REST, `rolemgmt`, `pakate`) accept HTTP Basic: username
  `apikey`, password the PA API key. A successful call also sets a `paSession` cookie.
- Paths at the `{PAW_HOST}` root (`idvisualizations`) **reject the API key**: Basic
  alone returns `401 AUTH_REQUIRED` with a `/login` redirect. They need the
  `paSession` cookie, which also tells them the tenant. So call
  `GET {API}/rolemgmt/v1/users/me` with Basic first, then reuse the same session
  (cookie jar) for the dashboard calls.

Send
`Accept: application/json`; send `Content-Type: application/json` on bodies.

Rows marked **verified** returned the stated status against a real tenant. Rows
marked **from the builder repo** are used by the open-source demo builder but
were not run when this skill was written.

## Identity and discovery

| Call | Purpose | Status |
|---|---|---|
| `GET {API}/rolemgmt/v1/users/me` | Confirm the key; returns id, name, role | verified `200` |
| `GET {API}/tm1/Servers` | Database names | verified `200` |
| `GET {API}/pakate/v0` | Databases with `server_status`, `createdBy`, version, size | verified `200` |
| `GET {API}/tm1/{DB}/api/v1/Cubes?$select=Name&$expand=Dimensions($select=Name)&$filter=not startswith(Name,'}')` | Cubes with dimensions in storage order | verified `200` |
| `GET .../Cubes('{cube}')?$select=Name,LastDataUpdate,LastSchemaUpdate` | If the two timestamps are equal, the cube was probably never loaded | verified `200` |
| `POST .../ExecuteMDX?$expand=Axes($expand=Tuples($expand=Members($select=Name))),Cells($select=Value;$top=40)` body `{"MDX": "..."}` | Probe a slice for data | verified `201` |

Note the `$filter` above needs the literal `}`; in a Python f-string write `}}`.

## Views

| Call | Purpose | Status |
|---|---|---|
| `POST .../Cubes('{cube}')/Views` body `{"@odata.type":"#ibm.tm1.api.v1.MDXView","Name":"...","MDX":"..."}` | Create a view for grid widgets to bind to | verified `201` |
| `POST .../Cubes('{cube}')/Views('{view}')/tm1.Execute?$expand=Cells($select=Value)` | Run a view | verified `201` (not `200`) |
| `DELETE .../Cubes('{cube}')/Views('{view}')` | Remove it | verified `204` |

## Classic books (TM1 Contents API)

Base: `{API}/tm1/{DB}/api/v1/Contents('Applications')/Contents`

| Call | Purpose | Status |
|---|---|---|
| `GET {base}?$select=Name` | List books | verified `200` |
| `GET {base}('{book}')` | Read a book; sheets and widgets come back inline | verified `200` |
| `POST {base}` body `{"@odata.type":"#ibm.tm1.api.v1.Document","Name":"..."}` | Create an empty book | verified `201` |
| `PATCH {base}('{book}')` body `DocumentReference` with `Sheets` and `Public` | Set sheets and widgets | verified `200` |
| `DELETE {base}('{book}')` | Remove | verified `204` |

Do not use `$expand=Sheets`, `$expand=Sheets($expand=Widgets)` or a
`/tm1.Document` cast on a read. They return `400`.

## Dashboards (idvisualizations)

Base: `{PAW_HOST}/idvisualizations/r/v2/content/{path}/` where `{path}` is
URL-encoded segments such as `shared/MyBook`. Keep the trailing slash.

| Call | Purpose | Status |
|---|---|---|
| `GET {base}` | Read an asset. Keys: `path, kind, name, id, state, type, version, content, custom_properties` | verified `200` |
| `PUT {base}` body `{"type":"dashboard","name":"...","content":{},"custom_properties":{}}` | Create the asset (returns its `id`) | verified `201` |
| `PUT {base}` body `{"type":"dashboard","content":{...},"custom_properties":{}}` | Replace the content | verified `201` |
| `DELETE {base}` | Remove; a later `GET` is `404` | verified `200` |
| `GET .../content/shared/` | A folder returns `type: folder` and `content: null` | verified `200`, no child listing |
| `GET {PAW_HOST}/idvisualizations/r/v2/info/shared/` | Folder metadata | verified `200`, no child listing |

There is no verified call that lists a folder's children. A `?children=true`
query is accepted but ignored.

Other endpoints in the builder repo, not run here: `pacontent/v1/Assets`
(section folders), `plan-service/api/v1` (Plan applications and workflows).

## Status triage

| Code and body | Meaning |
|---|---|
| `401`, `WWW-Authenticate: Bearer realm="Service", error="invalid_request"` | The key was rejected, or it is for another tenant or region |
| `401`, `AUTH_REQUIRED` with a `/login` redirect | Called a UI path with no API prefix |
| `400`, `Sheets is not a property of DocumentReference` | Used `$expand=Sheets` on a read |
| `400`, `Entry ... is not a 'ibm.tm1.api.v1.Document'` | Cast a `DocumentReference` to `Document` |
| `404` after a `PUT` | Wrong host root; the dashboard API is not under `/api/{tenantId}/v0` |
| `401` `AUTH_REQUIRED` with a `/login` location on a dashboard call | No `paSession` cookie. Log in at `{API}/rolemgmt/v1/users/me` with the key first, in the same session |
| `405` | Wrong verb for that path |
| `201` on a read or run | Normal for `ExecuteMDX` and `tm1.Execute` |
