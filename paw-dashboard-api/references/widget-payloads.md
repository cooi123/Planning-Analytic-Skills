# Widget payloads

Read this before writing widget JSON. Two ways to get it right, in order of
preference:

1. **Clone.** Build the widget by hand in PAW, `GET` the dashboard, copy the
   widget object, change the cube, members and `queryState`. This always
   matches what the installed PAW version expects.
2. **Generate.** Build it from the structure below. The structure comes from the
   open-source builder `filiplou/Planning-analytics-bob` (`create_paw_demo.py`),
   which the server accepted when run against a real tenant.

The values `version: 3208` and `flag_bits = 2056` below are copied from that
builder. The server accepted them, but it was not tested whether other values
fail, so treat them as inherited and re-check them after a PAW upgrade.

## Classic grid widget

```json
{
  "@odata.type": "#ibm.tm1.api.v1.GridWidget",
  "Name": "Test grid",
  "View@odata.bind": "Cubes('{cube}')/Views('{view}')",
  "Top": 0, "Left": 0, "Width": 900, "Height": 450
}
```

Sheets wrap widgets:
`{"@odata.type":"#ibm.tm1.api.v1.Sheet","Name":"Sheet1","Order":0,"Widgets":[...]}`.
The view must exist first. This API takes no chart widgets.

## Dashboard content envelope

```
content
  layout  { type: "tab", pageSize: {width: 1280, height: 720},
            selectedTabId, items: [ tab, ... ] }
  name, theme ("carbonGrey10"), version (3208), sync, properties,
  pageContext: [], mdvConditionalFormatDefinitions: []
```

A **tab** is `{type: "container", id, title, items: [ page ]}`. The page is
`{type: "genericPage", css: "templateBox aspectRatio_default", items: [
templateIndicator, widget, widget, ... ]}`. Widgets are positioned with
percentage `style` values (`top`, `left`, `width`, `height`).

IDs are generated: `content{uuid}` for widgets, `model{hex time}_{8 hex}` for
tabs, pages and data models.

## queryState

Every chart and cube viewer carries a `queryState`: an `ICCFMemento` JSON
object, deflate-zipped and base64-encoded. It appears in both
`PAProperties.tm1.queryState` and `mdvGridState.queryState`.

- Zip entry name `query.json`, `ZIP_DEFLATED`, `ZipInfo.flag_bits = 2056`,
  `create_system = 0`, then base64 of the zip bytes.
- Contents: `cubeID`, a `rowState` and `columnState` (one dimension each, a
  `HierarchyMemberSet` with `isDynamic: true` and a `FULL` drill), and a
  `pageEdgeStates` array with one entry per other dimension, each holding a
  `MemberSelection` of one member.
- Hierarchy ids look like `[Dim].[Dim]`; member ids like `[Dim].[Dim].[Member]`.
- Every dimension of the cube must be on rows, columns, or a page edge.

Because the builder loads a row or column dimension with all its members (a
`FULL` drill), put a **small** dimension on each axis. A dimension with thousands
of members on the category axis will probably give a heavy, unreadable chart;
this was not tested.

You cannot write this blob by hand in Postman. Use a script, or clone.

## Chart widgets

Types: `com.ibm.vis.rave2bundlebar`, `com.ibm.vis.rave2line`,
`com.ibm.vis.rave2bundlecolumn`. A chart widget is an outer `type: "live"`
model plus an inner `tm1mdv` cube viewer that holds the `queryState`.

- Category axis: the row dimension, as a data item with the hierarchy id and a
  label such as `Year: Selection`.
- Values: one data item per column-dimension **member to plot**, e.g.
  `[Version].[Version].[Actual]`. The column dimension therefore decides the
  series.
- Slot mapping: `categories`, `values`, and a third slot named `color` (bar,
  column) or `series` (line) bound to `_multiMeasuresSeries_data`.
- `visTypeLocked: true`, `widgettype: "CubeViewer"`.

Verified combination: rows = a small time dimension (Year) or a period
dimension, columns = Version with two members plotted.

## Selector and synced grid

- Selector: `visId: "paselector"`, inner `tm1mdvSyncTile` with `hierarchyID`,
  `memberSet`, `memberID` (`{hierarchy}.[RootMember]`), `syncType: 2`,
  `showAsList: true`. The root member must exist in that hierarchy.
- Synced grid: `visId: "pacubeviewer"`, inner `tm1mdv` bound to a saved view,
  with `SynchedHierarchies` listing every hierarchy that a selector on the same
  tab drives. Page layout used: selector in the left 22%, grid in the right 76%
  of each row.

A selector filters a grid only if its hierarchy is in the grid's
`SynchedHierarchies`. This wiring was accepted by the server but not confirmed
visually; if a selector does nothing, look there first.

## What can go wrong without an error

The server stores content without rendering it, so a `201` proves syntax, not
correctness. Blank widgets usually mean an empty data slice or a member id that
doesn't exist. Probe the data first (see `SKILL.md` step 4).
