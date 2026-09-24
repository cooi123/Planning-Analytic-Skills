# Endpoints by version

The agentic-AI MCP surface was **reorganised at PAW 2.1.22 / 3.1.9** (June 2026).
Config that worked before that release returns `404` after it, and vice versa. This
is the single most common cause of a connection that "used to work".

## Contents
- [The split](#the-split)
- [URL shapes by deployment](#url-shapes-by-deployment)
- [Tenant id rules](#tenant-id-rules)
- [Tool inventory before 2.1.22](#tool-inventory-before-2122)
- [Endpoints that do not exist](#endpoints-that-do-not-exist)
- [Prerequisites](#prerequisites)

## The split

| | Before 2.1.22 / 3.1.9 | 2.1.22 / 3.1.9 and later |
|---|---|---|
| Layout | One endpoint per tool family | One unified endpoint |
| Paths | `…/agentic-ai/cube/mcp`, `…/agentic-ai/analysis/mcp` | `…/agentic-ai/ibm-pa-tools/mcp` |
| Client entries needed | Two | One |
| Old paths after upgrade | — | **Removed.** Return `404` |

IBM's release note is explicit that the cube and analysis endpoints are no longer
available and existing integrations must be repointed at `ibm-pa-tools`. Treat an
upgrade as a breaking change for every MCP client config in the estate.

## URL shapes by deployment

**2.1.22 / 3.1.9 and later**
```
PA as a Service:   https://<PAW_HOST>/api/<PAW_TENANT_ID>/v0/agentic-ai/ibm-pa-tools/mcp
PA on Cloud/local: https://<PAW_HOST>/api/v0/agentic-ai/ibm-pa-tools/mcp
```

**Before 2.1.22 / 3.1.9**
```
PA as a Service:   https://<PAW_HOST>/api/<PAW_TENANT_ID>/v0/agentic-ai/{cube|analysis}/mcp
PA on Cloud/local: https://<PAW_HOST>/api/v0/agentic-ai/{cube|analysis}/mcp
```

The `v0` segment is the agentic-AI API version and is **not** the PAW version. It
stays `v0` across this change. Do not "upgrade" it to `v1` — that is the TM1/content
REST family, a different API, and it will `404`.

## Tenant id rules

- **SaaS: required.** Take it from the browser URL (`?tenantId=…`) or PA
  Administration. Requests to the non-tenant form get rewritten or rejected by the
  gateway.
- **PAoC / local: optional.** *Verified:* on a PAoC instance,
  `/api/v0/agentic-ai/analysis/mcp` and
  `/api/<TENANT>/v0/agentic-ai/analysis/mcp` both returned `200` with identical
  `serverInfo`. A tenant id copied from a SaaS config is harmless here, which is
  worth knowing because it means a tenant id in a failing PAoC URL is not the bug —
  keep looking.

## Tool inventory before 2.1.22

Useful for recognising which endpoint you have reached when a server does not
identify itself clearly. *Verified live against PAoC 1.26.0.*

**`cube/mcp`** — `TM1 Cube Service`, 21 tools. Data and exploration:
`get_data_from_data_explorer`, `get_MDX_for_recommended_view`,
`get_cubes_that_may_answer_query`, `get_available_tm1_servers`,
`get_cube_dimensions`, `get_cube_sample_members`, `execute_mdx_and_get_view`,
`lookup_potential_members`, `list_cubes_with_ai_analysis_metadata`,
`perform_impact_analysis`, `get_impact_analysis_summary`,
`perform_outlier_detection`, `get_outlier_summary`,
`generate_exploration_analysis_report`, `get_tm1_cubes`,
`get_cube_dimensions_with_metadata`, `list_cube_views`, `create_tm1_cube`,
`delete_tm1_cube`, `save_mdx_view`, `get_saved_view`.

**`analysis/mcp`** — `AnalysisServer`, 11 tools. TurboIntegrator process
management: `get_available_tm1_servers`, `get_tm1_processes`,
`get_tm1_process_details`, `create_tm1_process`, `update_tm1_process`,
`delete_tm1_process`, `execute_tm1_processes_asynchronously`,
`get_tm1_server_process_threads`, `get_tm1_server_process_status`,
`cancel_tm1_process_execution`, `get_tm1_server_process_execution_error_logs`.

On 2.1.22+ the unified endpoint exposes the union of these families, so a client
sees one server with the full set rather than two.

## Endpoints that do not exist

- **`…/agentic-ai/server/mcp`** — circulates widely in shared config snippets;
  *verified* `404` on a server where `cube` and `analysis` both returned `200`. The
  TI-process tools people expect here live on `analysis`. If a user's config has
  `server/mcp`, that alone explains the failure.
- **`…/agentic-ai/ibm-pa-tools/mcp` on a pre-2.1.22 server** — `404`, as the unified
  endpoint does not exist yet.
- **`…/v1/agentic-ai/…`** — wrong API version.

Because all three fail identically with `404`, distinguish them by probing the known
paths rather than reasoning about which should exist.

## Prerequisites

- **PA Agent add-on** must be installed. Without it the agentic-AI routes are absent
  entirely and every path returns `404` regardless of credentials. Check this before
  suspecting the URL — it is invisible from the client side and produces the same
  symptom as a typo.
- **OAuth client** creation requires PAW **3.1.8+ / 2.1.21+**.
- 3.1.9 required **Planning Analytics Agent key regeneration** and removed custom
  watsonx Orchestrate agent support. If a wxo integration broke at that upgrade, the
  key is the likely cause.

## Sources

- [2.1.22 — What's new, June 24 2026](https://www.ibm.com/docs/en/planning-analytics/2.1.0?topic=agent-2122-june-24-2026)
- [Connect custom agents with MCP tools](https://www.ibm.com/docs/en/planning-analytics/3.1.0?topic=integrations-connecting-custom-agents-mcp-tools)
- [MCP tools in Planning Analytics](https://www.ibm.com/docs/en/planning-analytics/3.1.0?topic=assistant-mcp-tools)
- [Universal MCP Endpoint announcement](https://community.ibm.com/community/user/blogs/sami-el-cheikh1/2026/06/26/ibm-planning-analytics-agent-just-got-easier-to-co)
