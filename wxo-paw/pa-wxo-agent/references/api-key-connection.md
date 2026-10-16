# wxO connections with a PA API key or a wxO-issued MCP token

Moved from `pa-mcp-connect` (`references/authentication.md`). For the credential types
themselves and their failure signatures, see that skill.

For production, use an OAuth auth-code connection instead: see
[`wxo-oauth.md`](wxo-oauth.md). The API-key connection below runs every user as the
key's identity. Use it for a job with no user, or for a demo.

### A wxO agent calling PA SaaS through a remote MCP toolkit (API key)

*Verified on the same SaaS instance with ADK `orchestrate`.* Three objects, imported in
this order, because each references the one before:

1. **Connection**, `kind: basic`, defined for both `draft` and `live`:
   ```yaml
   spec_version: v1
   kind: connection
   app_id: planning_analytics
   environments:
     draft: { kind: basic, type: team, server_url: <PA MCP URL> }
     live:  { kind: basic, type: team, server_url: <PA MCP URL> }
   ```
2. **Credentials, per environment.** Set them on `draft` **and** `live`. They don't
   carry over, and rotating a key means setting both again. Re-importing anything
   else is not needed.
   ```bash
   orchestrate connections add -a planning_analytics
   orchestrate connections import -f connection.yaml
   for env in draft live; do
     orchestrate connections set-credentials -a planning_analytics --env "$env" \
       --username apikey --password "$PA_API_KEY"
   done
   ```
3. **Toolkit**, `kind: mcp`, then the agent:
   ```yaml
   spec_version: v1
   kind: mcp
   name: planning_analytics
   transport: streamable_http
   url: <PA MCP URL>
   tools: ["*"]
   connections: [planning_analytics]
   ```
   ```bash
   orchestrate toolkits import -f toolkit.yaml -a planning_analytics
   orchestrate agents import -f agent.yaml
   ```
   The agent calls the tools under the toolkit's prefix, `planning_analytics:`.
   Re-import the agent whenever its YAML changes.

Keep the URL templated in the YAML and substitute it at import time, so the key never
lives in a file. `connections add` fails if the connection exists, so a setup script
should tolerate that error and carry on. Both imports update in place.

`type: team` means every user's TM1 reads run as the one API key's identity. TM1
security for individual users doesn't apply. Use per-member credentials where it
matters.

Importing PA through other routes can leave a second connection pointing at the same
host, with a generated app id. Check `orchestrate connections list` and confirm which
one the toolkit is bound to before rotating keys.

### wxO-issued MCP token

Basic auth with an unusual pairing — the API key goes in the **username** field:

```
username: <watsonx Orchestrate API key>
password: <token generated for the MCP server in watsonx Orchestrate>
Authorization: Basic base64(<apikey>:<token>)
```

PAW 3.1.9 removed custom watsonx Orchestrate agent support and required PA Agent key
regeneration, so a wxo integration that broke at that upgrade most likely needs a
regenerated key rather than a config change.
