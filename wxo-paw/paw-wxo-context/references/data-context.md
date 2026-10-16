# PAW `data_context` reference

What PAW sends to a custom watsonx Orchestrate agent on every agentic-chat message.
The IBM doc covers only part of it. The rest was observed live by the
WxO-portable-template validation (`docs/paw-dashboard-context-capability.md`).

## Documented by IBM

```json
{
  "timestamp": "2026-03-05T19:06:06Z",
  "openWidgets": [
    {
      "selectedCubeName": "Members Forecast",
      "cubes": [
        {
          "cubeName": "Members Forecast",
          "serverName": "Planning Sample",
          "mdxQuery": { "Mdx": "SELECT ... FROM [SalesCube]", "isMdxTruncated": false },
          "selectedCells": [ { "rowIndex": 0, "colIndex": 0, "formattedValue": "139.58" } ]
        }
      ]
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `timestamp` | When the state was captured (ISO 8601) |
| `openWidgets[]` | Widgets open on the dashboard |
| `selectedCubeName` | The active cube in a widget |
| `cubes[].cubeName`, `serverName` | Cube and TM1 server behind the widget |
| `mdxQuery.Mdx` | The widget's query |
| `mdxQuery.isMdxTruncated` | True when the MDX was cut to fit a size limit |
| `selectedCells[]` | `rowIndex`, `colIndex` (0-based), `formattedValue` |

Source: https://www.ibm.com/docs/en/planning-analytics/2.1.0?topic=integrations-context-available-custom-agents

## Observed live, not documented

| Field | Notes |
|---|---|
| `userInformation.perspective` | `dashboard`, `pa-plan-contribute`, and others. Gates most native commands |
| `userInformation.role` | e.g. `administrator`. Gates user and group admin commands |
| `userInformation.openAssetName` | Name of the open book |
| `browserLanguage` | PAW locale |
| `selectedWidgetID` | ID of the focused widget |
| top-level `selectedCubeName` | Active cube across the dashboard |
| `planContributeContext.tasksToApprove[]` | In plan contribute: `id`, `name`, `approvers[]` (each with `contributors[]`) |
| `selectedCells[].value` | Raw value, sometimes present alongside `formattedValue` |

Shape variations a parser must accept:

- `openWidgets` may be a **single object** (one widget, with `widgetID` or `id`)
  instead of an array, or a map of ID to widget.
- Cubes may be under `cubes` **or** `openCubes`, as an array or a map.
- `mdxQuery` and `selectedCells` may sit on the widget rather than the cube.
- Outside a dashboard there may be no `openWidgets` at all, only
  `userInformation` and the other metadata.

## Behaviour

- Captured fresh for **each message**. Context lasts one run and is not kept across
  turns.
- Indexes are **0-based**: `rowIndex: 2` is the third visible row.
- `formattedValue` is display-rounded (`"79.4M"`), not the TM1 number
  (`79,382,396.00`).
- `selectedCells` keeps **click order** up to about 8 cells. Beyond that PAW sorts
  it by value, descending.
- Column members are often listed literally in the MDX. Row members are usually a
  dynamic set (`DESCENDANTS`, `EXCEPT`, `TM1SUBSETALL`), so **row labels can't be
  read from the MDX text**. Run the query to find them.
- **Chart type** (bar, line, pie) is never included.
- On a dashboard sheet, `openWidgets` holds **one** widget for the whole sheet. Each
  visualisation (tile, table, chart) is a separate entry under `cubes`.
- `selectedWidgetID`, top-level `selectedCubeName` and the plugin's `is_selected_cube`
  were null or false in every capture. **Find the selection by looking for the cube
  entry with non-empty `selectedCells`.** Only one visualisation holds cells at a time.
- Clicking a row or column header is not reported as a selection. It can instead
  change the MDX, e.g. to `DRILLDOWNMEMBER`.
- Prefer the raw `value` over `formattedValue` for checking. Formats vary between
  visualisations (`126.5M`, `11,867.8K`).
- The structure will grow. Ignore unknown fields rather than failing.

For turning a selected cell into dimensions, members, parents and roll-ups, see
`selected-cell-lineage.md`.

## Where the runtime exposes it

| Consumer | Access |
|---|---|
| Agent instructions, guidelines | `{data_context}`, or dotted paths such as `{data_context.userInformation.perspective}` |
| Pre-invoke plugin | `plugin_context.state["context"]["data_context"]` (confirmed live) |
| Python tool | `context: AgentRun` parameter → `context.request_context.get("data_context")` |
| MCP / OpenAPI tools | **No access.** The model must pass values as arguments |

The value may arrive as an object or as a JSON string. Handle both.
