# What PAW returns

Observed live on PAoC 2.1.23 (PA MCP: IBM PA Tools 1.27.2) with a custom wxO
agent replying with the bare `user_defined` JSON from `command-templates.md`.
Use this to tell, from the chat panel alone, whether a command worked, which
side refused it, and why.

**Who wrote the message:**

- **PAW's command handler** writes the confirmations and red refusals, often
  with a "click here for documentation" link. They mean the JSON reached PAW.
- **The agent's guideline** writes the plain-text refusals. They mean the JSON was
  never sent.
- **Raw JSON visible in chat** means PAW didn't recognise the payload. Compare it
  field by field with the template.

## Success

| Command | Phrase | PAW's reply in chat | On screen |
|---|---|---|---|
| `select_database` | Work with database IBM_PA_Financial | `Working with database(s) IBM_PA_Financial` | Search context set |
| `switch_to_perspective` | Go to modeling | `Switching to modeling-home` | Data and Models opens (`perspective=modeling-home`) |
| `open_paw_artifact` | Open book Financial Summary | (none captured) | Book opens (`perspective=dashboard`) |
| `open_tm1_artifact` | Open cube Financial Reporting | `Opening cube Financial Reporting` | A new cube view is added to the book |

## Refusals and prompts

| Situation | Reply (red text unless noted) | Written by | Fix |
|---|---|---|---|
| TM1 command before any database is selected | `Sorry, you have not specified a search context. To specify one, follow this example by entering: Work with database 'MyDatabase'` + documentation link | PAW | Run `select_database` first |
| Dashboard command sent from another perspective | `You cannot run the command on this perspective: modeling-home, please switch to a different perspective: dashboard.` + documentation link | PAW, even though the agent ignored its own perspective check | Open a book first |
| Command adds a widget to a book in view mode | `This action can only be performed in edit mode. Do you want to switch to edit mode and continue?` with **Yes** / **No** (normal text) | PAW | Yes switches the book to edit mode. Nothing is saved until the user saves the book |
| Guideline's perspective check fires | `Sorry I cannot perform this action on this perspective` (plain text) | The agent | Open a book first |

## Not yet observed

`list_artifacts`, `lookup_tm1_artifact`, `search_context`, the AI panels
(`chart_insights`, `impact_analysis`, `outlier_analysis`), view changes,
sandboxes, `member_calculation`, admin and plan-task commands. Add each reply
here as it is captured, with the PAW version.
