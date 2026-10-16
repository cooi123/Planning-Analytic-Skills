# PAW native command templates

Extracted verbatim from `agents/Airline_FP_A_Agent.yaml` in the WxO-portable-template, whose validation notes say they are kept byte-identical to the default Planning Analytics agent. IBM does not publish these. Treat them as internal to PAW: correct for the PAW release they were captured against, subject to change.

Each entry gives the guideline's **condition** (when it fires) and **action** (parameters, JSON template, response rules) exactly as deployed. Copy them into an agent's `guidelines:` list unchanged. In particular, keep each template's `type` or `response_type` key as written.

## Navigation and discovery

### `open_paw_artifact`

**Condition**

```text
The user wants to open an asset like a book, workbench plan or application. Common phrasings include where [artifact_name] is the asset to open:
•	"Open book  [artifact_name]"
•	"Open workbench  [artifact_name]"
•	"Open plan  [artifact_name]"
•	"Open application  [artifact_name]"
•	"Open PAW artifact [artifact_name]"
•	"Open workspace artifact [artifact_name]"
•  "Open"
```

**Action**

```text
Parameters:
•	artifact_name (required): The PAW artifact name.
•	paw_artifact_type (required): The type of PAW artifact.

**IMPORTANT: paw_artifact_type Normalization**

The paw_artifact_type parameter must be one of these exact values: "dashboard", "workbench", "plan", or "application"

If the user provides any of these variations, normalize them to the correct type:

• "dashboard" ← book, sheet, report, books, sheets, reports
• "workbench" ← workbench, modeling workbench, modeling, modelling
• "plan" ← pa plan, plans, planning, plan
• "application" ← app, application, apps, applications

Always convert user input to the exact predefined type before including it in the JSON.

JSON template — return this exact structure, replacing only the placeholder values:
json
{
	"user_defined": {
	"command": "open_paw_artifact",
	"artifact_name": "<artifact_name_provided_by_user>",
	"paw_artifact_type": "<paw_artifact_type_provided_by_user>"
},
	"response_type": "user_defined"
}
Rules for generating the response:
1	Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2	Collect all required parameters from the user before generating the response.
3	Preserve the user's exact spelling and casing for any names or identifiers.
4	The "response_type" field must match the template exactly — do not change it.
5	Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `open_tm1_artifact`

**Condition**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

The user wants to open an object from a database (cube, view, dimension, hierarchy, or set). Common phrasings includes:
  • "Open cube X"
  • "Open view Y"
  • "Open"
  • "Show dimension X"
  • "Show the Y set"
  • "Edit the Y hierarchy"
```

**Action**

```text
{data_context.userInformation.perspective} must be equal to dashboard. Do not perform the action if this condition is not met.

Parameters:
• artifact_name (required): The TM1 artifact name. When a user types "I'm not sure", or "I don't know", or another expression of confusion for artifact names, tell them "If you're unsure, you can list the available artifact names by saying 'list {artifact type}'."
• tm1_artifact_type (required): Must be one of: cube, view, dimension, hierarchy, or set.
JSON template — return this exact structure, replacing only the placeholder values:
{
	"user_defined": {
	"command": "open_tm1_artifact",
	"artifact_name": ["<artifact_name_provided_by_user>"],
	"tm1_artifact_type": "<tm1_artifact_type_provided_by_user>"
},
	"response_type": "user_defined"
}
Rules for generating the response:
1 Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2 Collect all required parameters from the user before generating the response.
3 Preserve the user's exact spelling and casing for any names or identifiers.
4 The "response_type" field must match the template exactly — do not change it.
5 Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `switch_to_perspective`

**Condition**

```text
The user wants to switch to a specific perspective. Common phrasings include:
  • "Switch to perspective modeling"
  • "Switch to perspective administration"
  • "Go to home"
  • "Go to plans and apps"
  • "Can you go to modeling page"
  • "Go to reports page"
  • "Switch to reports and analysis"
  When NOT to trigger this action:
  • The user wants to open a paw artifact
  • The user wants to switch sandbox or switch context, those commands are different.
```

**Action**

```text
Parameters:
• perspective_name (required): The name of the perspective or page the user wants to switch to. Note that the only valid perspective_names are: pa-home, modeling-home, pa-plan, pa-reports and pa-administration. The user may type modeling or data models but it means modeling-home. The user may type plans and apps or plans but it means pa-plan. The user may type admin or administration but it means pa-administration, the user may type home or first page but it means pa-home. The user may type reports or analysis, or reports and analysis but it means pa-reports.
JSON template — return this exact structure, replacing only the placeholder values:
{
	"user_defined": {
	"command": "switch_to_perspective",
	"perspective_name": "<perspective_name>"
},
	"response_type": "user_defined"
}
Rules for generating the response:
1 Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2 Collect all required parameters from the user before generating the response.
3 Preserve the user's exact spelling and casing for any names or identifiers.
4 The "response_type" field must match the template exactly — do not change it.
5 Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `list_artifacts`

**Condition**

```text
This value  "{data_context.userInformation.perspective}" must be equal to "dashboard", and  The user wants to list TM1 artifacts of a specific type, retrieve a list of objects (Cubes, dimensions, views or sets) on a database, but does not want to search or open them. Common phrasings include:
•	"List cubes"
•	"Show dimensions"
•	"List all views"
•	"Show me the sets"
•	"List"
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
•	tm1_artifact_type (required): Must be one of: Dimension, Set, View, Cube, or Hierarchy.
JSON template — return this exact structure, replacing only the placeholder values:
json
{
	"user_defined": {
	"command": "list_artifacts",
	"tm1_artifact_type": "<artifact_type_provided_by_user>"
},
	"type": "user_defined"
}
Rules for generating the response:
1	Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2	Collect all required parameters from the user before generating the response.
3	Preserve the user's exact spelling and casing for any names or identifiers.
4	The "type" field must match the template exactly — do not change it.
5	Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `lookup_tm1_artifact`

**Condition**

```text
{data_context.userInformation.perspective} must be equal to dashboard. Do not perform the action if this condition is not met.

The user wants to search or find a specific TM1 artifact but are unsure which database or cube it resides in.

Common phrasings include:
•	"Search for X"
•	"Find Y"
•	"Find cube named X"
•	"Search database 1, database 2, database 3 for X"
•	"Search database 1, database 2, database 3 for dimension X"
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
• artifact_name (required): The TM1 artifact name.
• tm1_artifact_type (optional): Must be one of: cube, view, dimension, hierarchy, or set.
• databases (optional): An array of 1 to 4 database names exactly as provided by the user. Do not infer or guess database names the user did not explicitly state.
- It is important that if a user simply types 'Search' or 'Search for cube', they are not referring to the search context action but this action instead.
JSON template — return this exact structure, replacing only the placeholder values:
json
{
  "user_defined": {
    "command": "lookup_tm1_artifact",
    "artifact_name": ["<artifact_name_provided_by_user>"],
    "tm1_artifact_type": "<artifact_type_provided_by_user>",
    "databases": ["<database_name_provided_by_user>", "<another_database_name_provided_by_user>", ...]
  },
  "type": "user_defined"
}
Rules for generating the response:
1	Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2	Collect all required parameters from the user before generating the response.
3	Preserve the user's exact spelling and casing for any names or identifiers.
4	The "type" field must match the template exactly — do not change it.
5	Return the JSON with no additional text, commentary, or markdown wrapping.
6	After returning the JSON, this action is considered done, stop gathering parameters , clear the context and reset this flow.
```

### `select_database`

**Condition**

```text
This value  "{data_context.userInformation.perspective}" must be equal to "dashboard", and the user wants to select, choose, open, switch to, connect to, or work with one or more databases (also called "data sources" or "connections"). Common phrasings include where [database_name] is the name of the database to select:
• "Select database"
• "Select database [database_name]"
• "Work with database [database_name]"
• "Switch to database [database_name]"
• "Open database [database_name]"
• "Connect to [database_name]"
• "Work with [database_name]"
• "Use database [database_name]  and [database_name]"
• "Change database to [database_name]"
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective", respond  "Sorry I cannot perform this action on this perspective:  {data_context.userInformation.perspective} " , stop gathering parameters , clear the cache and reset this flow.

Parameters:
  • databases (required): An array of 1 to 4 database names exactly as provided by the user. Do not infer or guess database names the user did not explicitly state. If the user does not provide any database name, ask them which database they want to select before returning JSON.
  JSON template — return this exact structure, replacing only the placeholder values:
  {
    "user_defined": {
    "command": "select_database",
    "databases": ["<database_name_provided_by_user>", "<another_database_name_provided_by_user>", ...]
  },
    "type": "user_defined"
  }
  Rules for generating the response:
  1 Return the JSON in the exact format specified — do not add extra fields or modify the structure.
  2 Collect all required parameters from the user before generating the response.
  3 Preserve the user's exact spelling and casing for any names or identifiers.
  4 The "type" field must match the template exactly — do not change it.
  5 Return the JSON with no additional text, commentary, or markdown wrapping.
  6 After returning the JSON, this action is considered done, stop gathering parameters , clear the context and stop this flow.
```

### `search_context`

**Condition**

```text
This value  "{data_context.userInformation.perspective}" must be equal to "dashboard", and the user wants see what databases are in the  search context within the current context, but is not searching objects or trying to list artifacts. Common phrasings include:
  • "Search context"
  • "What is my search context"
  • "What databases am I using?"
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
• No additional parameters required. This command searches within the current context.
JSON template — return this exact structure, replacing only the placeholder values:
{
	"user_defined": {
	"command": "search_context"
},
	"response_type": "user_defined"
}
Rules for generating the response:
1 Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2 Collect all required parameters from the user before generating the response.
3 Preserve the user's exact spelling and casing for any names or identifiers.
4 The "response_type" field must match the template exactly — do not change it.
5 Return the JSON with no additional text, commentary, or markdown wrapping.
```

## AI features

### `chart_insights`

**Condition**

```text
{data_context.userInformation.perspective} must be set to dashboard. Do not perform the action if this condition is not met.

The user wants to get insights or analyze a chart from a chart or visualization but does not want to produce or switch to a chart.

Common phrasings include:
•	"Chart insights"
•	"Show insights"
•	"Analyze this chart"
•	"What does this chart show"
•	"Explain visualization"
When NOT to trigger this action:
•	The user wants to create a chart — that is a switch to chart command.
•	The user wants outlier analysis — that is a different command.
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
•	No additional parameters required. This command analyzes the current chart view.
JSON template — return this exact structure, replacing only the placeholder values:
json
{
	"user_defined": {
	"command": "chart_insights"
},
	"type": "user_defined"
}
Rules for generating the response:
1	Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2	Collect all required parameters from the user before generating the response.
3	Preserve the user's exact spelling and casing for any names or identifiers.
4	The "type" field must match the template exactly — do not change it.
5	Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `impact_analysis`

**Condition**

```text
{data_context.userInformation.perspective} must be equal to dashboard. Do not perform the action if this condition is not met.

The user wants to perform impact analysis on the current data, has a question on how data impacts or affects an specific view or if there are relations in the data or how the data is related. but the questions is not likely found on tabular data or is asking for oddities or outliers.

Common phrasings include:
•	"Impact analysis"
•	"Show impact"
•	"Analyze impact"
•	"What is the impact"
•	"Analyze"
•	"Analyze view"
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
•	No additional parameters required. This command analyzes the current view.
JSON template — return this exact structure, replacing only the placeholder values:
json
{
	"user_defined": {
	"command": "impact_analysis"
},
	"type": "user_defined"
}
Rules for generating the response:
1	Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2	Collect all required parameters from the user before generating the response.
3	Preserve the user's exact spelling and casing for any names or identifiers.
4	The "type" field must match the template exactly — do not change it.
5	Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `outlier_analysis`

**Condition**

```text
{data_context.userInformation.perspective} must be equal to dashboard. Do not perform the action if this condition is not met.

The user wants to detect outliers in the data, look for anomalies or oddities in the data. but is not looking for impact or relations within the data.

Common phrasings include:
•	"Outlier analysis"
•	"Find outliers"
•	"Detect anomalies"
•	"outliers"
•	"Detect anomalies"
•	"Show outliers"
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
•	No additional parameters required. This command analyzes the current view for outliers.
JSON template — return this exact structure, replacing only the placeholder values:
json
{
	"user_defined": {
	"command": "outlier_analysis"
},
	"type": "user_defined"
}
Rules for generating the response:
1	Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2	Collect all required parameters from the user before generating the response.
3	Preserve the user's exact spelling and casing for any names or identifiers.
4	The "type" field must match the template exactly — do not change it.
5	Return the JSON with no additional text, commentary, or markdown wrapping.
6	After returning the JSON, this action is considered done, stop gathering parameters , clear the context and reset this flow.
```

### `view_recommender`

**Condition**

```text
{data_context.userInformation.perspective} must be equal to dashboard

The user wants to explore data or get view recommendations when the user is asking a question that can be answered with a table, the question is typically related to tabular data. but the user is not simply asking to switch or show an exploration

Common phrasings include:
•	"Explore data"
•	"Show budget in year"
•	"What are the top products in revenue "
•	"Show profit margin in year"
•	"Show me sales data"
•	"Find revenue by region"
•	"Data explorer"
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
•	customerQuery (required): The user's data exploration query. Must be data-specific, not generic like "explore my data".
•	databases (optional): Up to 4 database names. If not provided, do not ask for it.
- The customerQuery is an open string that the user can input. Ensure the entire entered query is captured.
- The databases portion is not essential to run this action. If a user does not provide any database name, do not ask for it explicitly.
- Do not collect entries such as 'explore my data' as the query, a query should be more data specific such as 'show me phones in specific countries'.
JSON template — return this exact structure, replacing only the placeholder values:
json
{
	"user_defined": {
	"command": "view_recommender",
	"databases": ["<database_name_provided_by_user>", "<another_database_name_provided_by_user>"],
	"customerQuery": "<query_provided_by_user>"
},
	"response_type": "user_defined"
}
Rules for generating the response:
1	Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2	Collect all required parameters from the user before generating the response.
3	Preserve the user's exact spelling and casing for any names or identifiers.
4	The "response_type" field must match the template exactly — do not change it.
5	Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `annotation_summary`

**Condition**

```text
This value "{data_context.userInformation.perspective}" must be equal to "dashboard", and the user wants to get a summary of all the annotations contained on a given cube view. Common phrasings include:
  • "Summarize my annotations"
  • "Give me my annotations"
  • "Execute annotation summary"
  • "Give me a summary of the annotations"
  • "Summarize my annotations on the first X annotations"
  • "Summarize my annotations by skipping the first X and only using Y"
  • "Give me a summary of my annotations created from Date"
  • "Give me a summary of my annotations created from Date and created to Date"
  When NOT to trigger this action:
  • The user wants to summarize only — that is the summarize command.
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
All options are optional, if a user doesn't supply any, do not fill in or ask for additional info.
• top (optional): Must be a valid whole number.
• skip (optional): Must be a valid whole number.
• created_to (optional): The date for upper bound of created annotations. If a user specifically asks for annotation summary for a specific date without an end date (e.g. 2005, January 2003, etc), assume the start and end date are within those bounds.
• created_from (optional): The date for lower bound of created annotations. If a user specifically asks for annotation summary for a specific date without an end date (e.g. 2005, January 2003, etc), assume the start and end date are within those bounds.
JSON template — return this exact structure, replacing only the placeholder values:
{
	"user_defined": {
	"command": "annotation_summary",
	"top": "<top_provided_by_user>",
	"skip": "<skip_provided_by_user>",
	"created_to": "<created_to_provided_by_user>",
  "created_from": "<created_from_provided_by_user>"
},
	"response_type": "user_defined"
}
Rules for generating the response:
1 Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2 Collect all required parameters from the user before generating the response.
3 Preserve the user's exact spelling and casing for any names or identifiers.
4 The "response_type" field must match the template exactly — do not change it.
5 Return the JSON with no additional text, commentary, or markdown wrapping.
```

## View manipulation

### `switch_context`

**Condition**

```text
This value  "{data_context.userInformation.perspective}" must be equal to "dashboard", and The user wants to switch the context member, filter a table on an specific value. Common phrasings include where [filter] is the value to filter:

  • "Switch context to [filter] "
  • "Change context to [filter] "
  • "Filter on [filter] "
  • "Set context to [filter] "
  • "Slice on [filter]
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"
Parameters:
• artifact_name (required): The context member name to switch to.
JSON template — return this exact structure, replacing only the placeholder values:
{
	"user_defined": {
	"target": "context",
	"command": "switch_context",
	"artifact_name": ["<context_member_name_provided_by_user>"]
},
	"type": "user_defined"
}
Rules for generating the response:
1 Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2 Collect all required parameters from the user before generating the response.
3 Preserve the user's exact spelling and casing for any names or identifiers.
4 The "type" field must match the template exactly — do not change it.
5 Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `swap`

**Condition**

```text
This value  "{data_context.userInformation.perspective}" must be equal to "dashboard", and the user wants to swap or exchange rows and columns in the current view. Common phrasings include:
  • "Swap rows and columns"
  • "Switch rows and columns"
  • "Transpose the view"
  • "Flip rows and columns"
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
• No additional parameters required. This command executes immediately.
JSON template — return this exact structure, replacing only the placeholder values:
{
	"user_defined": {
	"command": "swap"
},
	"type": "user_defined"
}
Rules for generating the response:
1 Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2 Collect all required parameters from the user before generating the response.
3 Preserve the user's exact spelling and casing for any names or identifiers.
4 The "type" field must match the template exactly — do not change it.
5 Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `move_dimension`

**Condition**

```text
This value  "{data_context.userInformation.perspective}" must be equal to "dashboard", and the user wants to move a dimension to rows, columns, context, or bench. Common phrasings include:
•	"Move dimension X to rows"
•	"Put X in columns"
•	"Move X to context"
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective".

Parameters:
•	target (required): Must be "rows", "columns", "context", or "bench".
•	artifact_name (required): The dimension name to move.
JSON template — return this exact structure, replacing only the placeholder values:
json
{
	"user_defined": {
	"command": "move_dimension",
	"target": "<target_provided_by_user>",
	"artifact_name": "<artifact_name_provided_by_user>"
},
	"type": "user_defined"
}
Rules for generating the response:
1	Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2	Collect all required parameters from the user before generating the response.
3	Preserve the user's exact spelling and casing for any names or identifiers.
4	The "type" field must match the template exactly — do not change it.
5	Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `switch_set`

**Condition**

```text
This value  "{data_context.userInformation.perspective}" must be equal to "dashboard", and the user wants to switch to a different set. Common phrasings include:
  • "Switch to set X"
  • "Use set X"
  • "Change to set X"
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
• artifact_name (required): The set name to switch to.
JSON template — return this exact structure, replacing only the placeholder values:
{
	"user_defined": {
	"command": "switch_set",
	"artifact_name": ["<set_name_provided_by_user>"]
},
	"type": "user_defined"
}
Rules for generating the response:
1 Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2 Collect all required parameters from the user before generating the response.
3 Preserve the user's exact spelling and casing for any names or identifiers.
4 The "type" field must match the template exactly — do not change it.
5 Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `expand_member`

**Condition**

```text
This value  "{data_context.userInformation.perspective}" must be equal to "dashboard", and the user wants to expand a node to show its children. Common phrasings include:
•	"Expand member X"
•	"Expand X"
•	"Unfold X"
•	"Show children of X"
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
•	artifact_name (required): The member name to expand.
JSON template — return this exact structure, replacing only the placeholder values:
json
{
	"user_defined": {
	"command": "expand_member",
	"artifact_name": ["<artifact_name_provided_by_user>"]
},
	"type": "user_defined"
}
Rules for generating the response:
1	Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2	Collect all required parameters from the user before generating the response.
3	Preserve the user's exact spelling and casing for any names or identifiers.
4	The "type" field must match the template exactly — do not change it.
5	Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `collapse_member`

**Condition**

```text
This value  "{data_context.userInformation.perspective}" must be equal to "dashboard", and the user wants to collapse or fold  a member. Common phrasings include:
•	"Collapse member X"
•	"Collapse X"
•	"fold X"
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
•	artifact_name (required): The member name to collapse.
JSON template — return this exact structure, replacing only the placeholder values:
json
{
	"user_defined": {
	"command": "collapse_member",
	"artifact_name": ["<artifact_name_provided_by_user>"]
},
	"type": "user_defined"
}
Rules for generating the response:
1	Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2	Collect all required parameters from the user before generating the response.
3	Preserve the user's exact spelling and casing for any names or identifiers.
4	The "type" field must match the template exactly — do not change it.
5	Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `hide`

**Condition**

```text
This value  "{data_context.userInformation.perspective}" must be equal to "dashboard", and. the user wants to hide specific items, or remove them from the view. Common phrasings include:
•	"Hide member X"
•	"Hide X"
•	"Hide X, Y, Z"
•	"Hide members X and Y"
•	"Remove X from view"
•	"Remove X, Y, and Z from view"
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
•	artifact_name (required): An array of member names to hide. Can be a single member or multiple members.
JSON template — return this exact structure, replacing only the placeholder values:
json
{
	"user_defined": {
	"command": "hide",
	"artifact_name": ["<member_name_1>", "<member_name_2>", "<member_name_N>"]
},
	"type": "user_defined"
}
Rules for generating the response:
1	Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2	Collect all required parameters from the user before generating the response.
3	Preserve the user's exact spelling and casing for any names or identifiers.
4	The "type" field must match the template exactly — do not change it.
5	Return the JSON with no additional text, commentary, or markdown wrapping.
6	The artifact_name field must always be an array, even if only one member is provided (e.g., ["X"]).
7	Extract all member names from the user's input and include them in the array (e.g., "Hide X, Y, Z" → ["X", "Y", "Z"]).
```

### `keep`

**Condition**

```text
This value  "{data_context.userInformation.perspective}" must be equal to "dashboard", and the user wants to keep only specific members and hide all others, retaining only the desired items. Common phrasings include:
•	"Keep member X"
•	"Keep X"
•	"Keep only X"
•	"Show only X"
•	"Keep X and Y"
•	"Keep X, Y, Z"
•	"retain X, Y, Z"
•	"Keep members X, Y, and Z"
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
•	artifact_name (required): An array of member names to keep. Can be a single member or multiple members. All other members will be hidden.
JSON template — return this exact structure, replacing only the placeholder values:
json
{
	"user_defined": {
	"command": "keep",
	"artifact_name": ["<member_name_1>", "<member_name_2>", "<member_name_N>"]
},
	"response_type": "user_defined"
}
Rules for generating the response:
1	Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2	Collect all required parameters from the user before generating the response.
3	Preserve the user's exact spelling and casing for any names or identifiers.
4	The "response_type" field must match the template exactly — do not change it.
5	Return the JSON with no additional text, commentary, or markdown wrapping.
6	The artifact_name field must always be an array, even if only one member is provided (e.g., ["X"]).
7	Extract all member names from the user's input and include them in the array (e.g., "Keep X, Y, Z" → ["X", "Y", "Z"]).
```

### `unhide_all`

**Condition**

```text
{data_context.userInformation.perspective} must be equal to dashboard. Do not perform the action if this condition is not met.

The user wants to unhide all hidden members displaying all data in the view. Common phrasings include:
  • "Unhide all"
  • "Unhide"
  • "Show all"
  • "Display all"
  • "Unhide everything"
  • "Show all rows/columns"
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
• target (required): Specify "rows", "columns", or "rows and columns". If user says "unhide all" without specifying, assume "rows and columns". If a user only says "unhide", ensure you're asking for the input.
- If a user simply types 'unhide all', assume they want to unhide rows and columns.
JSON template — return this exact structure, replacing only the placeholder values:
{
	"user_defined": {
	"command": "unhide_all",
	"target": "<target_provided_by_user>"
},
	"type": "user_defined"
}
Rules for generating the response:
1 Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2 Collect all required parameters from the user before generating the response.
3 Preserve the user's exact spelling and casing for any names or identifiers.
4 The "type" field must match the template exactly — do not change it.
5 Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `suppress_zeroes`

**Condition**

```text
This value  "{data_context.userInformation.perspective}" must be equal to "dashboard", and the user wants to hide, suppress or remove  rows/columns with zero values. Common phrasings include:
  • "Suppress zeroes"
  • "Hide zeroes"
  • "Remove zero rows"
  • "Suppress zero values"
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
• target (required): Specify "rows", "columns", or "rows and columns". If user says "suppress all zeroes" without specifying, assume "rows and columns".
- If a user types 'suppress all zeroes', assume they want to unhide rows and columns. Otherwise, ask for input if not specified prior.
JSON template — return this exact structure, replacing only the placeholder values:
{
	"user_defined": {
	"command": "suppress_zeroes",
	"target": "<target_provided_by_user>"
},
	"type": "user_defined"
}
Rules for generating the response:
1 Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2 Collect all required parameters from the user before generating the response.
3 Preserve the user's exact spelling and casing for any names or identifiers.
4 The "type" field must match the template exactly — do not change it.
5 Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `display_zeroes`

**Condition**

```text
This value  "{data_context.userInformation.perspective}" must be equal to "dashboard", and the user wants to show or display rows/columns with zero values. Common phrasings include:
•	"Display zeroes"
•	"Show zeroes"
•	"Show zero rows"
•	"Display zero values"
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
•	target (required): Specify "rows", "columns", or "rows and columns". If user says "display all zeroes" without specifying, assume "rows and columns".
- If a user types 'display all zeroes', assume they want to unhide rows and columns. Otherwise, ask for input if not specified prior.
JSON template — return this exact structure, replacing only the placeholder values:
json
{
	"user_defined": {
	"command": "display_zeroes",
	"target": "<target_provided_by_user>"
},
	"type": "user_defined"
}
Rules for generating the response:
1	Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2	Collect all required parameters from the user before generating the response.
3	Preserve the user's exact spelling and casing for any names or identifiers.
4	The "type" field must match the template exactly — do not change it.
5	Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `sort`

**Condition**

```text
This value  "{data_context.userInformation.perspective}" must be equal to "dashboard", and the user wants to sort rows or columns in a view. Common phrasings include:
  • "Sort by X"
  • "Sort ascending"
  • "Sort descending"
  • "Order by X"
  When NOT to trigger this action:
  • The user wants to move a dimension — that is a move dimension command.
  • The user wants to filter — that is a different command.
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
• target (required): Must be "rows" or "columns".
• order (required): Must be "ascending" or "descending".
• artifact_name (required): The member name to sort by.
JSON template — return this exact structure, replacing only the placeholder values:
{
	"user_defined": {
	"command": "sort",
	"order": "<order_provided_by_user>",
	"target": "<target_provided_by_user>",
	"artifact_name": ["<artifact_name_provided_by_user>"]
},
	"response_type": "user_defined"
}
Rules for generating the response:
1 Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2 Collect all required parameters from the user before generating the response.
3 Preserve the user's exact spelling and casing for any names or identifiers.
4 The "response_type" field must match the template exactly — do not change it.
5 Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `chart_view`

**Condition**

```text
This value  "{data_context.userInformation.perspective}" must be equal to "dashboard". Do not perform the action if this condition is not met.

The user wants to switch to a chart view, ask for a visualization, but do not ask for analysis or explanation of the chart  . Common phrasings include:
  • "Switch to chart"
  • "Show as bar chart"
  • "Show area chart"
  • "Display as line chart"
  • "View as pie chart"
  • "Switch to exploration"
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
• chart_type (required): Must be one of: Bar, Line, Cube view, exploration, Area, or Pie.
• artifact_name (optional): The artifact name. If not provided, do not ask for it.
- The Cube view chart type can also be called by the user as Exploration. Return cube view in such cases as well.
- The artifact_name portion is not essential to run this action. If a user does not provide an artifact_name, do not ask for it explicitly.
- Types of supported charts: Bar, Line, cube view, Area, and Pie.
JSON template — return this exact structure, replacing only the placeholder values:
{
	"user_defined": {
	"command": "chart_view",
	"chart_type": "<chart_type_provided_by_user>",
	"artifact_name": "<artifact_name_provided_by_user>"
},
	"type": "user_defined"
}
Rules for generating the response:
1 Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2 Collect all required parameters from the user before generating the response.
3 Preserve the user's exact spelling and casing for any names or identifiers.
4 The "type" field must match the template exactly — do not change it.
5 Return the JSON with no additional text, commentary, or markdown wrapping.
```

## Calculations

### `member_calculation`

**Condition**

```text
{data_context.userInformation.perspective} must be equal to dashboard. Do not perform the action if this condition is not met.

The user wants to create a calculation for one or more members  but do not want to calculate on all rows or columns.
Common phrasings include (where [member1],  [member2], [memberX] are the members)to calculate:
•	"Calculate average of X and Y"
•	"Sum X and Y"
•	"Create calculation"
When NOT to trigger this action:
•	The user wants to summarize — that is a summarize command.
•	The user includes 'row', 'rows', 'column', 'columns', or any variation of such in the query — that is a summarize command.
•	The user is asking for a value — that is not a calculation creation.
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
•	artifact_name_supplemental_1 (required): The name for the calculation.
•	artifact_name (required): Array of member names to use in calculation.
•	calculation_type (required): Must be one of: Average, Minimum, Maximum, Median, Aggregate, Rank, Absolute Value, Percent Total, Percent Parent, Percent Of, Percent Change, Subtraction, Sum, Multiplication, or Division.
•	Supported calculation types are only of the following:
- Average
- Minimum
- Maximum
- Median
- Aggregate
- Rank
- Absolute Value
- Percent Total
- Percent Parent
- Percent Of
- Percent Change
- Subtraction
- Sum
- Multiplication
- Division
JSON template — return this exact structure, replacing only the placeholder values:
json
{
	"user_defined": {
	"command": "member_calculation",
	"artifact_name_supplemental_1": ["<name_of_calculation_prodvided_by_user>"],
	"artifact_name": ["<artifact_name_provided_by_user>", "<another_artifact_provided_by_user>"],
	"calculation_type": "<calculation_type_provided_by_user>"
},
	"response_type": "user_defined"
}
Rules for generating the response:
1	Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2	Collect all required parameters from the user before generating the response.
3	Preserve the user's exact spelling and casing for any names or identifiers.
4	The "response_type" field must match the template exactly — do not change it.
5	Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `summarize`

**Condition**

```text
{data_context.userInformation.perspective} must be equal to dashboard. Do not perform the action if this condition is not met.

The user wants to summarize rows or columns, or want to perform calculations on rows or columns. Common phrasings include:
  • "Calculate maximum on rows as name"
  • "Summarize rows"
  • "Sum all columns"
  • "Average the rows"
  When NOT to trigger this action:
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
• target (required): Must be "rows" or "columns".
• artifact_name (required): The name for the summarization.
• summary_type (required): Must be one of: Average, Minimum, Maximum, Median, Aggregate, or Sum.
• Supported summarization types are only of the following:
- Average
- Minimum
- Maximum
- Median
- Aggregate
- Sum
JSON template — return this exact structure, replacing only the placeholder values:
{
	"user_defined": {
	"command": "summarize",
	"target": "<target_prodvided_by_user>",
	"artifact_name": ["<summarization_name_provided_by_user>"],
	"summary_type": "<summarize_type_provided_by_user>"
},
	"response_type": "user_defined"
}
Rules for generating the response:
1 Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2 Collect all required parameters from the user before generating the response.
3 Preserve the user's exact spelling and casing for any names or identifiers.
4 The "response_type" field must match the template exactly — do not change it.
5 Return the JSON with no additional text, commentary, or markdown wrapping.
```

## Book operations

### `copy`

**Condition**

```text
{data_context.userInformation.perspective} must be equal to dashboard. Do not perform the action if this condition is not met.

The user wants to copy or duplicate the currently selected cube or view. Common phrasings include:
•	"Copy"
•	"Duplicate"
•	"Copy this"
•	"Copy selection"
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters: none

JSON template — return this exact structure, replacing only the placeholder values:
json
{
	"user_defined": {
	"command": "copy"
},
	"type": "user_defined"
}

Rules for generating the response:
1	Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2	Collect all required parameters from the user before generating the response.
3	Preserve the user's exact spelling and casing for any names or identifiers.
4	The "type" field must match the template exactly — do not change it.
5	Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `refresh`

**Condition**

```text
This value  "{data_context.userInformation.perspective}" must be equal to "dashboard", and the user wants to refresh or reload the current view or data. Common phrasings include:
•	"Refresh"
•	"Reload"
•	"Update the data"
•	"Get latest data"
When NOT to trigger this action:
•	The user wants to open a different view — that is an open command.
•	The user wants to change the database — that is a select database command.
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
•	No additional parameters required. This command executes immediately.
JSON template — return this exact structure, replacing only the placeholder values:
json
{
	"user_defined": {
	"command": "refresh"
},
	"type": "user_defined"
}
Rules for generating the response:
1	Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2	Collect all required parameters from the user before generating the response.
3	Preserve the user's exact spelling and casing for any names or identifiers.
4	The "type" field must match the template exactly — do not change it.
5	Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `undo`

**Condition**

```text
This value  "{data_context.userInformation.perspective}" must be equal to "dashboard", and  The user wants to undo the last action. Common phrasings include:
  • "Undo"
  • "Undo that"
  • "Undo last action"
  • "Revert"
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
• No additional parameters required. This command undoes the last action.
JSON template — return this exact structure, replacing only the placeholder values:
{
	"user_defined": {
	"command": "undo"
},
	"type": "user_defined"
}
Rules for generating the response:
1 Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2 Collect all required parameters from the user before generating the response.
3 Preserve the user's exact spelling and casing for any names or identifiers.
4 The "type" field must match the template exactly — do not change it.
5 Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `redo`

**Condition**

```text
This value  "{data_context.userInformation.perspective}" must be equal to "dashboard", and The user wants to redo the last undone action. Common phrasings include:
•	"Redo"
•	"Redo that"
•	"Redo last action"

If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
•	No additional parameters required. This command redoes the last undone action.
JSON template — return this exact structure, replacing only the placeholder values:
json
{
	"user_defined": {
	"command": "redo"
},
	"type": "user_defined"
}
Rules for generating the response:
1	Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2	Collect all required parameters from the user before generating the response.
3	Preserve the user's exact spelling and casing for any names or identifiers.
4	The "type" field must match the template exactly — do not change it.
5	Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `cancel`

**Condition**

```text
Anytime the user types "cancel"
```

**Action**

```text
Stop gathering the parameters and reset the flow. and reply "Canceling the action"
```

## Sandboxes

### `create_sandbox`

**Condition**

```text
{data_context.userInformation.perspective} must be equal to dashboard. Do not perform the action if this condition is not met.

The user wants to create a new sandbox. Common phrasings include where [sandbox] is the name of the sandbox to create:
•	"Create sandbox X"
•	"New sandbox X"
•	"Make a sandbox called X"
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
•	artifact_name (required): The name for the new sandbox.
JSON template — return this exact structure, replacing only the placeholder values:
json
{
	"user_defined": {
	"command": "create_sandbox",
	"artifact_name": ["<sandbox_name_provided_by_user>"]
},
	"type": "user_defined"
}
Rules for generating the response:
1	Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2	Collect all required parameters from the user before generating the response.
3	Preserve the user's exact spelling and casing for any names or identifiers.
4	The "type" field must match the template exactly — do not change it.
5	Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `switch_sandbox`

**Condition**

```text
This value  "{data_context.userInformation.perspective}" must be equal to "dashboard", and The user wants to switch to a different sandbox but not to create a new one. Common phrasings include:
  • "Switch to sandbox X"
  • "Use sandbox X"
  • "Change to sandbox X"
  • "Switch to X sandbox"
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to dashboard, respond "Sorry I cannot perform this action on this perspective"

Parameters:
• artifact_name (required): The sandbox name to switch to.
JSON template — return this exact structure, replacing only the placeholder values:
{
	"user_defined": {
	"command": "switch_sandbox",
	"artifact_name": ["<sandbox_name_provided_by_user>"]
},
	"type": "user_defined"
}
Rules for generating the response:
1 Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2 Collect all required parameters from the user before generating the response.
3 Preserve the user's exact spelling and casing for any names or identifiers.
4 The "type" field must match the template exactly — do not change it.
5 Return the JSON with no additional text, commentary, or markdown wrapping.
```

## Administration (role = administrator)

### `list_users`

**Condition**

```text
This value "{data_context.userInformation.role}" must be equal to "administrator", and the user wants to list all users in the system. Common phrasings include:
  • "List all users"
  • "Show me all users"
  • "What users are there?"
  • "Display all users"
  • "Get all users"
  When NOT to trigger this action:
  • The user wants to list users for a specific group — that is a list_users_for_groups command.
  • The user wants to create a user — that is a create_user command.
  • The user wants to list groups of a user — that is a list_groups_of_user command.
```

**Action**

```text
If {data_context.userInformation.role} is not equal to administrator, respond "Sorry you do not have permissions to run this action"

Parameters:
• No parameters required.
JSON template — return this exact structure:
{
	"user_defined": {
	"command": "list_users"
},
	"response_type": "user_defined"
}
Rules for generating the response:
1 Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2 The "response_type" field must match the template exactly — do not change it.
3 Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `list_groups`

**Condition**

```text
This value "{data_context.userInformation.role}" must be equal to "administrator", and the user wants to list all groups. Common phrasings include:
  • "List all groups"
  • "Show me all groups"
  • "What groups are available?"
  • "Display groups"
  When NOT to trigger this action:
  • The user wants to create a group — that is a create_group command.
  • The user wants to open a specific group — that is a different command.
```

**Action**

```text
If {data_context.userInformation.role} is not equal to administrator, respond "Sorry you do not have permissions to run this action"

Parameters:
• No parameters required.
JSON template — return this exact structure:
{
	"user_defined": {
	"command": "list_groups"
},
	"response_type": "user_defined"
}
Rules for generating the response:
1	Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2	Collect all required parameters from the user before generating the response.
3	Preserve the user's exact spelling and casing for any names or identifiers.
4	The "response_type" field must match the template exactly — do not change it.
5	Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `list_users_for_groups`

**Condition**

```text
This value "{data_context.userInformation.role}" must be equal to "administrator", and the user wants to list all users for a specific group. Common phrasings include:
  • "List users for group X"
  • "Show me users in group X"
  • "What users are in group X?"
  • "Display users for group X"
  • "Who is in group X?"
  When NOT to trigger this action:
  • The user wants to list all groups — that is a list_groups command.
  • The user wants to create a group — that is a create_group command.
  • The user wants to add users to a group — that is a different command.
```

**Action**

```text
If {data_context.userInformation.role} is not equal to administrator, respond "Sorry you do not have permissions to run this action"

Parameters:
• group_name (required): The name of the group to list users for.
JSON template — return this exact structure, replacing only the placeholder values:
{
	"user_defined": {
	"command": "list_users_for_groups",
	"group_name": "<group_name>"
},
	"response_type": "user_defined"
}
Rules for generating the response:
1 Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2 Collect all required parameters from the user before generating the response.
3 Preserve the user's exact spelling and casing for any names or identifiers.
4 The "response_type" field must match the template exactly — do not change it.
5 Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `list_groups_of_user`

**Condition**

```text
This value "{data_context.userInformation.role}" must be equal to "administrator", and the user wants to list all groups that a specific user belongs to. Common phrasings include:
  • "List groups for user X"
  • "Show me groups of user X"
  • "What groups is user X in?"
  • "Display groups for user X"
  • "Which groups does user X belong to?"
  When NOT to trigger this action:
  • The user wants to list all groups — that is a list_groups command.
  • The user wants to list users for a group — that is a list_users_for_groups command.
  • The user wants to list all users — that is a list_users command.
```

**Action**

```text
If {data_context.userInformation.role} is not equal to administrator, respond "Sorry you do not have permissions to run this action"

Parameters:
• username (required): The username of the user to list groups for.
Confirmation:
• After collecting the username, confirm with user if they are sure of performing this action with a yes or no button.
JSON template — return this exact structure, replacing only the placeholder values:
{
	"user_defined": {
	"command": "list_groups_of_user",
	"username": "<username>"
},
	"response_type": "user_defined"
}
Rules for generating the response:
1 Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2 Collect all required parameters from the user before generating the response.
3 Preserve the user's exact spelling and casing for any names or identifiers.
4 The "response_type" field must match the template exactly — do not change it.
5 Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `create_user`

**Condition**

```text
This value "{data_context.userInformation.role}" must be equal to "administrator", and the user wants to create a new user in the system.

Common phrasings include:
  • "Create"
  • "Create a user"
  • "Add a new user"
  • "Create user with email X"
  • "Add user with name Y"
  • "Register a new user"
  When NOT to trigger this action:
  • The user wants to list users — that is a list_users command.
  • The user wants to list users for a group — that is a list_users_for_groups command.
  • The user wants to add users to a group — that is a different command.
```

**Action**

```text
If {data_context.userInformation.role} is not equal to administrator, respond "Sorry you do not have permissions to run this action".

Parameters:
• loginId (required): The login ID for the user.
• email (required): The email address for the user.
• displayName (required): The display name for the user.
• firstName (required): The first name of the user.
• lastName (required): The last name of the user.
• role (required): The role assigned to the user.
JSON template — return this exact structure, replacing only the placeholder values:
{
	"user_defined": {
	"command": "create_user",
	"loginId": "<email>",
	"email": "<email>",
	"displayName": "<displayName>",
	"firstName": "<firstName>",
	"lastName": "<lastName>",
	"role": "<role>"
},
	"response_type": "user_defined"
}
Rules for generating the response:
1 Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2 Ensure that you are collecting all required parameters from the user before generating the response.
3 Preserve the user's exact spelling and casing for any names or identifiers.
4 The "response_type" field must match the template exactly — do not change it.
5 Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `delete_user`

**Condition**

```text
This value "{data_context.userInformation.role}" must be equal to "administrator", and the user wants to delete a specific user.

Common phrasings include:
  • "Delete"
  • "Delete user X"
  • "Remove user X"
  • "Delete the user X"
  • "Remove the user named X"
  • "Can you delete user X?"
  When NOT to trigger this action:
  • The user wants to list users — that is a list_users command.
  • The user wants to delete a group — that is a delete_group command.
  • The user wants to list groups — that is a list_groups command.
```

**Action**

```text
If {data_context.userInformation.role} is not equal to administrator, respond "Sorry you do not have permissions to run this action"

Parameters:
• username (required): The username of the user to delete.
Confirmation:
• After collecting the username, confirm with user if they are sure of performing this action with a yes or no button.
JSON template — return this exact structure, replacing only the placeholder values:
{
	"user_defined": {
	"command": "delete_user",
	"username": "<username>"
},
	"response_type": "user_defined"
}
Rules for generating the response:
1 Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2 Collect all required parameters from the user before generating the response.
3 Preserve the user's exact spelling and casing for any names or identifiers.
4 The "response_type" field must match the template exactly — do not change it.
5 Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `create_group`

**Condition**

```text
This value "{data_context.userInformation.role}" must be equal to "administrator", and the user wants to create a new group.
Common phrasings include:
  • "Create"
  • "Create group X"
  • "New group X"
  • "Make a group called X"
  When NOT to trigger this action:
  • The user wants to create a sandbox — that is a create sandbox command.
  • The user wants to open a group — that is a different command.
```

**Action**

```text
If {data_context.userInformation.role} is not equal to administrator, respond "Sorry you do not have permissions to run this action"

Parameters:
• group_name (required): The name for the new group.
• description (optional): User can provide a group description. If not provided, do not ask for it.
JSON template — return this exact structure, replacing only the placeholder values:
{
	"user_defined": {
	"command": "create_group",
	"group_name": "<group_name>",
	"description": "<group_description>"
},
	"response_type": "user_defined"
}
Rules for generating the response:
1 Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2 Collect all required parameters from the user before generating the response.
3 Preserve the user's exact spelling and casing for any names or identifiers.
4 The "response_type" field must match the template exactly — do not change it.
5 Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `delete_group`

**Condition**

```text
This value "{data_context.userInformation.role}" must be equal to "administrator", and the user wants to delete a specific group.

Common phrasings include:
  • "Delete"
  • "Delete group X"
  • "Remove group X"
  • "Delete the group X"
  • "Remove the group named X"
  • "Can you delete group X?"
  When NOT to trigger this action:
  • The user wants to list groups — that is a list_groups command.
  • The user wants to delete a user — that is a delete_user command.
  • The user wants to list users — that is a list_users command.
```

**Action**

```text
If {data_context.userInformation.role} is not equal to administrator, respond "Sorry you do not have permissions to run this action"

Parameters:
• group_name (required): The name of the group to delete.
JSON template — return this exact structure, replacing only the placeholder values:
{
	"user_defined": {
	"command": "delete_group",
	"group_name": "<group_name>"
},
	"response_type": "user_defined"
}
Rules for generating the response:
1 Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2 Collect all required parameters from the user before generating the response.
3 Preserve the user's exact spelling and casing for any names or identifiers.
4 The "response_type" field must match the template exactly — do not change it.
5 Return the JSON with no additional text, commentary, or markdown wrapping.
```

## Plan contribution workflow (perspective = pa-plan-contribute)

### `submit_task`

**Condition**

```text
This value "{data_context.userInformation.perspective}" must be equal to "pa-plan-contribute", and the user wants to submit a task. Common phrasings include:
  • "Submit task"
  • "Submit the task"
  • "I want to submit a task"
  • "Submit task [task_name]"
  • "Submit [task_name] to [group]"
  When NOT to trigger this action:
  • The user wants to create a task — that is a different command.
  • The user wants to update a task — that is a different command.
  • The user is in a different perspective.
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to "pa-plan-contribute", respond "Sorry I cannot perform this action on this perspective"

If {data_context.planContributeContext.watsonTaskInfo.submitCompleteTask.tasksToSubmitComplete} is empty or does not exist, respond "There are no tasks available to submit." and stop.

You MUST collect all parameters one at a time. Never auto-select. Never combine steps. Wait for each reply before proceeding.

Pre-fill rules — apply these BEFORE sending any selector JSON:
• If the user already provided a task name in their initial message:
  - Try to fuzzy-match it against the "name" field in tasksToSubmitComplete.
  - No match → send the select_task_agentic JSON (STEP 1) and wait.
  - Match found → skip STEP 1, use that task's "id" and "isDimensionalTask", proceed to STEP 2.
• If the task is a normal task (isDimensionalTask = false) and the user already provided a group name in their initial message:
  - Fuzzy-match against "name" in the task's "groupsToSubmitComplete".
  - No match → send the select_group_agentic JSON (STEP 2) and wait.
  - Match found → skip STEP 2, use that group's "name", proceed to STEP 3.
• If the task is a DA task (isDimensionalTask = true) and the user already provided a member name in their initial message:
  - Use it directly — skip STEP 2 and proceed to STEP 3.

STEP 1 — Task selection:
ALWAYS return this exact JSON — no text before or after it:
{
  "user_defined": {
    "command": "select_task_agentic",
    "parent_command": "submit_task"
  },
  "response_type": "user_defined"
}
Wait for the user to pick a task from the UI dropdown. The user's reply will contain the chosen task name. Fuzzy-match the reply against {data_context.planContributeContext.watsonTaskInfo.submitCompleteTask.tasksToSubmitComplete} using the "name" field to get the task "id" and check its "isDimensionalTask" field, then proceed to STEP 2.

STEP 2 (isDimensionalTask = false): ALWAYS return this exact JSON — no text before or after it:
{
  "user_defined": {
    "command": "select_group_agentic",
    "parent_command": "submit_task",
    "task_id": "<chosen task id>",
    "group_role": "contributor",
    "groups": <chosen task's "groupsToSubmitComplete" array mapped to [{ "id": ..., "name": ... }]>
  },
  "response_type": "user_defined"
}
Wait for the user to pick a group from the UI dropdown. The user's reply will contain the chosen group name. Fuzzy-match the reply against the task's "groupsToSubmitComplete" to get the group's "name". Then proceed to STEP 3.

STEP 2 (isDimensionalTask = true): ALWAYS return this exact JSON — no text before or after it:
{
  "user_defined": {
    "command": "select_member_agentic",
    "parent_command": "submit_task",
    "task_id": "<chosen task id>"
  },
  "response_type": "user_defined"
}
Wait for the user to pick a member from the UI dropdown. The user's reply will contain the chosen member name. Use it as-is as the "member" value, then proceed to STEP 3.

STEP 3 — Comment (optional): Ask the user: "Would you like to add a comment?". If the user provides a comment, use it. If the user skips or provides no comment, use an empty string "". Then proceed to STEP 4.

Pre-fill rule for comment: If the user already provided a comment in their initial message, use it directly — do not ask again.

STEP 4: Return the final JSON — no extra text, no markdown.

JSON template for a normal task (isDimensionalTask = false):
{
  "user_defined": {
    "command": "submit_task",
    "task_id": "<chosen task id>",
    "groups": ["<name_of_chosen_group>"],
    "comment": "<comment_or_empty_string>"
  },
  "response_type": "user_defined"
}

JSON template for a DA task (isDimensionalTask = true):
{
  "user_defined": {
    "command": "submit_task",
    "task_id": "<chosen task id>",
    "member": "<member_name_provided_by_user>",
    "comment": "<comment_or_empty_string>"
  },
  "response_type": "user_defined"
}

Rules for generating the response:
1. Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2. Collect all required parameters using the UI selectors before generating the final response.
3. Always resolve the task selection to the task's "id". For groups, use the "name" value.
4. If the comment parameter is not provided, use an empty string "".
5. The "response_type" field must match the template exactly — do not change it.
6. Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `approve_task`

**Condition**

```text
This value "{data_context.userInformation.perspective}" must be equal to "pa-plan-contribute", and the user wants to approve a task (either a regular task or a dimensional task). Common phrasings include:
  • "Approve task"
  • "Approve regular task"
  • "Accept task"
  • "Approve this task"
  • "Approve dimensional task"
  • "Approve dimension task"
  • "Accept dimensional task"
  • "Approve this dimensional task"
  When NOT to trigger this action:
  • The user wants to reject or decline a task — that is a different command.
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to "pa-plan-contribute", respond "Sorry I cannot perform this action on this perspective"

If {data_context.planContributeContext.tasksToApprove} is empty or not present, respond "There are no tasks available to approve." and stop.

You MUST collect all parameters one at a time. Never auto-select. Never combine steps. Wait for each reply before proceeding.

STEP 1 — Task selection:
ALWAYS return this exact JSON first — no text before or after it:
{
  "user_defined": {
    "command": "select_task_agentic"
  },
  "response_type": "user_defined"
}
Wait for the user to pick a task from the UI dropdown. The user's reply will contain the chosen task name. Fuzzy-match the reply against {data_context.planContributeContext.tasksToApprove} using the "name" field to get the task "id", then proceed to STEP 2.

STEP 2 (regular task): ALWAYS return this exact JSON — no text before or after it:
{
  "user_defined": {
    "command": "select_group_agentic",
    "parent_command": "approve_task",
    "task_id": "<chosen task id>",
    "group_role": "approver",
    "groups": <chosen task's "approvers" array mapped to [{ "id": ..., "name": ... }]>
  },
  "response_type": "user_defined"
}
Wait for the user to pick a group from the UI dropdown. The user's reply will contain the chosen group name. Fuzzy-match the reply against the task's "approvers" array to get the approver's "id". Then proceed to STEP 3.
STEP 2 (dimensional task): ALWAYS return this exact JSON — no text before or after it:
{
  "user_defined": {
    "command": "select_member_agentic",
    "parent_command": "approve_task",
    "task_id": "<chosen task id>"
  },
  "response_type": "user_defined"
}
Wait for the user to pick a member from the UI dropdown. The user's reply will contain the chosen member name. Use it as-is as the "member_name" value, then proceed to STEP 4.

STEP 3 (regular task only): ALWAYS return this exact JSON — no text before or after it:
{
  "user_defined": {
    "command": "select_group_agentic",
    "parent_command": "approve_task",
    "task_id": "<chosen task id>",
    "group_role": "contributor",
    "groups": <chosen approver's "contributors" array mapped to [{ "id": ..., "name": ... }]>
  },
  "response_type": "user_defined"
}
Wait for the user to pick contributor groups from the UI dropdown. The user's reply will contain the chosen group name. Fuzzy-match the reply against the approver's "contributors" to get the contributor's "id". User may also type "all groups" or "all" — in that case use ["allGroups"] for contributor_groups.

STEP 4: Return the JSON — no extra text, no markdown.

Regular task JSON:
{
  "user_defined": {
    "command": "approve_task",
    "task_id": "<chosen task id>",
    "task_type": "regular",
    "approver_group": "<chosen approver id>",
    "contributor_groups": ["<chosen contributor id>"]
  },
  "response_type": "user_defined"
}
If user said "all groups" or "all": use ["allGroups"] for contributor_groups.

Dimensional task JSON:
{
  "user_defined": {
    "command": "approve_task",
    "task_id": "<chosen task id>",
    "task_type": "dimensional",
    "member_name": "<member name>"
  },
  "response_type": "user_defined"
}

Always resolve user's selection (number or name) to the entry's "id".
```

### `reject_task`

**Condition**

```text
This value "{data_context.userInformation.perspective}" must be equal to "pa-plan-contribute", and the user wants to reject or decline a task (either a regular task or a dimensional task). Common phrasings include:
  • "Reject task"
  • "Reject regular task"
  • "Decline task"
  • "Reject this task"
  • "Reject dimensional task"
  • "Decline dimensional task"
  • "Reject this dimensional task"
  When NOT to trigger this action:
  • The user wants to approve or accept a task — that is a different command.
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to "pa-plan-contribute", respond "Sorry I cannot perform this action on this perspective"

If {data_context.planContributeContext.tasksToApprove} is empty or not present, respond "There are no tasks available to reject." and stop.

You MUST collect all parameters one at a time. Never auto-select. Never combine steps. Wait for each reply before proceeding.

STEP 1 — Task selection:
ALWAYS return this exact JSON first — no text before or after it:
{
  "user_defined": {
    "command": "select_task_agentic",
    "parent_command": "reject_task"
  },
  "response_type": "user_defined"
}
Wait for the user to pick a task from the UI dropdown. The user's reply will contain the chosen task name. Fuzzy-match the reply against {data_context.planContributeContext.tasksToApprove} using the "name" field to get the task "id", then proceed to STEP 2.

STEP 2 (regular task): ALWAYS return this exact JSON — no text before or after it:
{
  "user_defined": {
    "command": "select_group_agentic",
    "parent_command": "reject_task",
    "task_id": "<chosen task id>",
    "group_role": "approver",
    "groups": <chosen task's "approvers" array mapped to [{ "id": ..., "name": ... }]>
  },
  "response_type": "user_defined"
}
Wait for the user to pick a group from the UI dropdown. The user's reply will contain the chosen group name. Fuzzy-match the reply against the task's "approvers" array to get the approver's "id". Then proceed to STEP 3.
STEP 2 (dimensional task): ALWAYS return this exact JSON — no text before or after it:
{
  "user_defined": {
    "command": "select_member_agentic",
    "parent_command": "reject_task",
    "task_id": "<chosen task id>"
  },
  "response_type": "user_defined"
}
Wait for the user to pick a member from the UI dropdown. The user's reply will contain the chosen member name. Use it as-is as the "member_name" value, then proceed to STEP 4.

STEP 3 (regular task only): ALWAYS return this exact JSON — no text before or after it:
{
  "user_defined": {
    "command": "select_group_agentic",
    "parent_command": "reject_task",
    "task_id": "<chosen task id>",
    "group_role": "contributor",
    "groups": <chosen approver's "contributors" array mapped to [{ "id": ..., "name": ... }]>
  },
  "response_type": "user_defined"
}
Wait for the user to pick contributor groups from the UI dropdown. The user's reply will contain the chosen group name. Fuzzy-match the reply against the approver's "contributors" to get the contributor's "id". User may also type "all groups" or "all" — in that case use ["allGroups"] for contributor_groups.

STEP 4: Return the JSON — no extra text, no markdown.

Regular task JSON:
{
  "user_defined": {
    "command": "reject_task",
    "task_id": "<chosen task id>",
    "task_type": "regular",
    "approver_group": "<chosen approver id>",
    "contributor_groups": ["<chosen contributor id>"]
  },
  "response_type": "user_defined"
}
If user said "all groups" or "all": use ["allGroups"] for contributor_groups.

Dimensional task JSON:
{
  "user_defined": {
    "command": "reject_task",
    "task_id": "<chosen task id>",
    "task_type": "dimensional",
    "member_name": "<member name>"
  },
  "response_type": "user_defined"
}

Always resolve user's selection (number or name) to the entry's "id".
```

### `take_ownership`

**Condition**

```text
This value "{data_context.userInformation.perspective}" must be equal to "pa-plan-contribute", and the user wants to take ownership of a DA task. Common phrasings include:
  • "Take ownership"
  • "Take ownership of task"
  • "Assign task to me"
  • "I want to take ownership"
  • "Take ownership of [task_name] for [member]"
  When NOT to trigger this action:
  • The user wants to release ownership — that is a different command.
  • The user wants to submit, approve, or reject a task — those are different commands.
  • The task is not a DA (dimensional) task.
  • The user is in a different perspective.
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to "pa-plan-contribute", respond "Sorry I cannot perform this action on this perspective"

Filter {data_context.planContributeContext.watsonTaskInfo.submitCompleteTask.tasksToSubmitComplete} to only entries where isDimensionalTask is true.
If no such entries exist, respond "There are no DA tasks available for ownership actions." and stop.

You MUST collect all parameters one at a time. Never auto-select. Never combine steps. Wait for each reply before proceeding.

Pre-fill rules — apply these BEFORE sending any selector JSON:
• If the user already provided a task name in their initial message:
  - Try to fuzzy-match it against the "name" field in the filtered DA tasks.
  - No match → send the select_task_agentic JSON (STEP 1) and wait.
  - Match found → skip STEP 1, use that task's "id", proceed to STEP 2.
• If the user already provided a member name in their initial message:
  - Use it directly — skip STEP 2 and proceed to STEP 3.

STEP 1 — Task selection:
ALWAYS return this exact JSON — no text before or after it:
{
  "user_defined": {
    "command": "select_task_agentic",
    "parent_command": "take_ownership"
  },
  "response_type": "user_defined"
}
Wait for the user to pick a task from the UI dropdown. The user's reply will contain the chosen task name. Fuzzy-match the reply against the filtered DA tasks using the "name" field to get the task "id", then proceed to STEP 2.

STEP 2 — Member selection:
ALWAYS return this exact JSON — no text before or after it:
{
  "user_defined": {
    "command": "select_member_agentic",
    "parent_command": "take_ownership",
    "task_id": "<chosen task id>"
  },
  "response_type": "user_defined"
}
Wait for the user to pick a member from the UI dropdown. The user's reply will contain the chosen member name. Use it as-is as the "member" value, then proceed to STEP 3.

STEP 3: Return the final JSON — no extra text, no markdown.

JSON template:
{
  "user_defined": {
    "command": "take_ownership",
    "task_id": "<chosen task id>",
    "member": "<member_name_provided_by_user>"
  },
  "response_type": "user_defined"
}

Rules for generating the response:
1. Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2. Collect all required parameters using the UI selectors before generating the final response.
3. Always resolve the task selection to the task's "id".
4. Preserve the user's exact spelling and casing for the member name.
5. The "response_type" field must match the template exactly — do not change it.
6. Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `release_ownership`

**Condition**

```text
This value "{data_context.userInformation.perspective}" must be equal to "pa-plan-contribute", and the user wants to release ownership of a DA task. Common phrasings include:
  • "Release ownership"
  • "Release ownership of task"
  • "Unassign task from me"
  • "I want to release ownership"
  • "Release ownership of [task_name] for [member]"
  When NOT to trigger this action:
  • The user wants to take ownership — that is a different command.
  • The user wants to submit, approve, or reject a task — those are different commands.
  • The task is not a DA (dimensional) task.
  • The user is in a different perspective.
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to "pa-plan-contribute", respond "Sorry I cannot perform this action on this perspective"

Filter {data_context.planContributeContext.watsonTaskInfo.submitCompleteTask.tasksToSubmitComplete} to only entries where isDimensionalTask is true.
If no such entries exist, respond "There are no DA tasks available for ownership actions." and stop.

You MUST collect all parameters one at a time. Never auto-select. Never combine steps. Wait for each reply before proceeding.

Pre-fill rules — apply these BEFORE sending any selector JSON:
• If the user already provided a task name in their initial message:
  - Try to fuzzy-match it against the "name" field in the filtered DA tasks.
  - No match → send the select_task_agentic JSON (STEP 1) and wait.
  - Match found → skip STEP 1, use that task's "id", proceed to STEP 2.
• If the user already provided a member name in their initial message:
  - Use it directly — skip STEP 2 and proceed to STEP 3.

STEP 1 — Task selection:
ALWAYS return this exact JSON — no text before or after it:
{
  "user_defined": {
    "command": "select_task_agentic",
    "parent_command": "release_ownership"
  },
  "response_type": "user_defined"
}
Wait for the user to pick a task from the UI dropdown. The user's reply will contain the chosen task name. Fuzzy-match the reply against the filtered DA tasks using the "name" field to get the task "id", then proceed to STEP 2.

STEP 2 — Member selection:
ALWAYS return this exact JSON — no text before or after it:
{
  "user_defined": {
    "command": "select_member_agentic",
    "parent_command": "release_ownership",
    "task_id": "<chosen task id>"
  },
  "response_type": "user_defined"
}
Wait for the user to pick a member from the UI dropdown. The user's reply will contain the chosen member name. Use it as-is as the "member" value, then proceed to STEP 3.

STEP 3: Return the final JSON — no extra text, no markdown.

JSON template:
{
  "user_defined": {
    "command": "release_ownership",
    "task_id": "<chosen task id>",
    "member": "<member_name_provided_by_user>"
  },
  "response_type": "user_defined"
}

Rules for generating the response:
1. Return the JSON in the exact format specified — do not add extra fields or modify the structure.
2. Collect all required parameters using the UI selectors before generating the final response.
3. Always resolve the task selection to the task's "id".
4. Preserve the user's exact spelling and casing for the member name.
5. The "response_type" field must match the template exactly — do not change it.
6. Return the JSON with no additional text, commentary, or markdown wrapping.
```

### `revert_submission`

**Condition**

```text
This value "{data_context.userInformation.perspective}" must be equal to "pa-plan-contribute", and the user wants to revert or reset a submission or completion on a task. Common phrasings include:
  • "Revert submission"
  • "Revert task submission"
  • "Reset submission"
  • "Undo submission"
  • "Revert completion"
  • "Revert task completion"
  • "Reset completion"
  • "Undo completion"
  • "Revert this task"
  • "Reset this task"
  When NOT to trigger this action:
  • The user mentions "approval", "approve", or "approved" — use revert_approve instead.
  • The user wants to approve, reject, or submit a task — those are different commands.
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to "pa-plan-contribute", respond "Sorry I cannot perform this action on this perspective"

If {data_context.planContributeContext.revertSubmissionTasks} is empty or not present, respond "There are no tasks available to revert." and stop.

You MUST collect all parameters one at a time. Never auto-select. Never combine steps. Wait for each reply before proceeding.

STEP 1 — Task selection:
ALWAYS return this exact JSON first — no text before or after it:
{
  "user_defined": {
    "command": "select_task_agentic",
    "parent_command": "revert_submission"
  },
  "response_type": "user_defined"
}
Wait for the user to pick a task from the UI dropdown. The user's reply will contain the chosen task name. Fuzzy-match the reply against {data_context.planContributeContext.revertSubmissionTasks} using the "name" field to get the task "id", then proceed to STEP 2.

STEP 2 (regular task): ALWAYS return this exact JSON — no text before or after it:
{
  "user_defined": {
    "command": "select_group_agentic",
    "parent_command": "revert_submission",
    "task_id": "<chosen task id>",
    "group_role": "contributor",
    "groups": <chosen task's "contributors" array mapped to [{ "id": ..., "name": ... }]>
  },
  "response_type": "user_defined"
}
Wait for the user to pick a contributor group from the UI dropdown. The user's reply will contain the chosen group name. Fuzzy-match the reply against the task's "contributors" to get the contributor's "id". User may also type "all groups" or "all" — in that case use ["allGroups"] for contributor_groups. Then proceed to STEP 3.
STEP 2 (dimensional task): ALWAYS return this exact JSON — no text before or after it:
{
  "user_defined": {
    "command": "select_member_agentic",
    "parent_command": "revert_submission",
    "task_id": "<chosen task id>"
  },
  "response_type": "user_defined"
}
Wait for the user to pick a member from the UI dropdown. The user's reply will contain the chosen member name. Use it as-is as the "member_name" value, then proceed to STEP 3.

STEP 3: Return the JSON — no extra text, no markdown.

Regular task JSON:
{
  "user_defined": {
    "command": "revert_submission",
    "task_id": "<chosen task id>",
    "task_type": "regular",
    "contributor_groups": ["<chosen contributor id>"]
  },
  "response_type": "user_defined"
}
If user said "all groups" or "all": use ["allGroups"] for contributor_groups.

Dimensional task JSON:
{
  "user_defined": {
    "command": "revert_submission",
    "task_id": "<chosen task id>",
    "task_type": "dimensional",
    "member_name": "<member name>"
  },
  "response_type": "user_defined"
}

Always resolve user's selection (number or name) to the entry's "id".
```

### `revert_approve`

**Condition**

```text
This value "{data_context.userInformation.perspective}" must be equal to "pa-plan-contribute", and the user wants to revert an approval on a task (either a regular task or a dimensional task). The user's message MUST contain the word "approval", "approve", or "approved". Common phrasings include:
  • "Revert approval"
  • "Revert task approval"
  • "Undo approval"
  • "Revert approve"
  • "Undo approve"
  When NOT to trigger this action:
  • The user mentions "submission" or "completion" — use revert_submission instead.
  • The user wants to approve, reject, or submit a task — those are different commands.
```

**Action**

```text
If {data_context.userInformation.perspective} is not equal to "pa-plan-contribute", respond "Sorry I cannot perform this action on this perspective"

If {data_context.planContributeContext.revertApproveTasks} is empty or not present, respond "There are no tasks available to revert approval for." and stop.

You MUST collect all parameters one at a time. Never auto-select. Never combine steps. Wait for each reply before proceeding.

STEP 1 — Task selection:
ALWAYS return this exact JSON first — no text before or after it:
{
  "user_defined": {
    "command": "select_task_agentic",
    "parent_command": "revert_approve"
  },
  "response_type": "user_defined"
}
Wait for the user to pick a task from the UI dropdown. The user's reply will contain the chosen task name. Fuzzy-match the reply against {data_context.planContributeContext.revertApproveTasks} using the "name" field to get the task "id", then proceed to STEP 2.

STEP 2 (regular task): ALWAYS return this exact JSON — no text before or after it:
{
  "user_defined": {
    "command": "select_group_agentic",
    "parent_command": "revert_approve",
    "task_id": "<chosen task id>",
    "group_role": "approver",
    "groups": <chosen task's "approvers" array mapped to [{ "id": ..., "name": ... }]>
  },
  "response_type": "user_defined"
}
Wait for the user to pick an approver group from the UI dropdown. The user's reply will contain the chosen group name. Fuzzy-match the reply against the task's "approvers" to get the approver's "id". Then proceed to STEP 3.
STEP 2 (dimensional task): ALWAYS return this exact JSON — no text before or after it:
{
  "user_defined": {
    "command": "select_member_agentic",
    "parent_command": "revert_approve",
    "task_id": "<chosen task id>"
  },
  "response_type": "user_defined"
}
Wait for the user to pick a member from the UI dropdown. The user's reply will contain the chosen member name. Use it as-is as the "member_name" value, then proceed to STEP 3.

STEP 3: Return the JSON — no extra text, no markdown.

CRITICAL: Always use the "id" field from the data — never use the "name" as the id value.

Regular task JSON:
{
  "user_defined": {
    "command": "revert_approve",
    "task_id": "<chosen task id>",
    "task_type": "regular",
    "approver_group": "<chosen approver id>"
  },
  "response_type": "user_defined"
}

Dimensional task JSON:
{
  "user_defined": {
    "command": "revert_approve",
    "task_id": "<chosen task id>",
    "task_type": "dimensional",
    "member_name": "<member name>"
  },
  "response_type": "user_defined"
}

Always resolve user's selection (number or name) to the entry's "id". Never put a name where an id is expected.
```
