# Platform matrix, on-prem vs SaaS

Read `{{config.platform.edition}}` from the conventions file and design to that
target. Flag anything in a design that behaves differently across the two.

| Concern | `on-prem` (PA v11 / TM1 Server) | `paas` (PA v12 / SaaS) |
|---|---|---|
| Server log access | Filesystem | REST API only |
| File-based data sources | Local filesystem paths | Restricted, prefer REST or staged uploads |
| Feeder inspection | Architect / Perspectives UI | REST API |
| Connection identity | Basic auth or CAM | Token-based, short-lived |
| Database naming | TM1 server instance | Tenant-scoped database |
| Process scheduling | Chores on the server | Chores, subject to tenant limits |

Design implications:

- A TI process reading a local file path is **not portable to SaaS**. If the project
  may move, parameterise the source and note the dependency in the spec.
- Anything in the design that depends on reading the server log at run time will not
  survive a move to SaaS.
- Never write a region, tenant id, or host name into a design artefact. Those are
  deployment facts and belong in environment variables. See
  `{{config.environments}}`.

This file lists design-affecting differences only. It is not an API reference.
Connection mechanics belong to the MCP server or your REST tooling, not to a
modelling skill.
