# wxO and PAW integration (wxo-paw)

Three skills for building and running a custom watsonx Orchestrate (wxO) agent inside
Planning Analytics Workspace (PAW) chat: an agent that reads PA data, understands
what the user is looking at in PAW, and can drive the PAW screen.

## Skills in this group

| Skill | Use it to |
|---|---|
| [`pa-wxo-agent`](pa-wxo-agent/SKILL.md) | Build, connect, test and ship a production wxO agent on PA: OAuth or API key connections, the PA MCP toolkit, Python tools calling TM1 REST, writes through approval Flows, and a pre-production checklist |
| [`paw-wxo-context`](paw-wxo-context/SKILL.md) | Use PAW's `data_context` (open cubes, MDX, selected cells) when the agent runs inside PAW chat, with a pre-invoke plugin and cell resolution in code |
| [`paw-wxo-actions`](paw-wxo-actions/SKILL.md) | Make the agent drive the PAW UI: open books, cubes and views, switch perspective, run AI panels (Chart Insights, impact analysis), and manage plan tasks |

## Order to use them

1. **`pa-wxo-agent`**: Set up the connection, import the toolkit, build the agent.
2. **`paw-wxo-context`**: Add PAW context awareness (if the agent runs inside PAW
   chat).
3. **`paw-wxo-actions`**: Add UI commands (if the agent should drive the PAW
   screen).

## Prerequisites

- PAW **2.1.22+** (SaaS / PA on Cloud) or **3.1.9+** (local) with the PA Agent
  add-on.
- PAW admin rights (Administration → Integrations).
- A wxO environment where you control embedded-chat security (the RSA key is set
  once per instance).
- On PA on Cloud: a watsonx.ai project with a Runtime service, plus an IBM Cloud
  API key.
- The ADK CLI (`orchestrate`).

## Install

Skill loaders find skills one folder deep, so copy the three skill folders **flat**
next to the core skills:

```bash
# IBM Bob
cp -r pa-skills/wxo-paw/pa-wxo-agent pa-skills/wxo-paw/paw-wxo-* .bob/skills/

# Claude Code
cp -r pa-skills/wxo-paw/pa-wxo-agent pa-skills/wxo-paw/paw-wxo-* .claude/skills/
```

Keep each skill's `references/`, `assets/` and `scripts/` folders.
