# Writing and deploying TM1 rules: a guide

For modellers who need to add or change a business rule and get it onto a Planning
Analytics server safely. The syntax is in `rules-syntax.md` and worked examples are
in `rule-examples.md`.

## 1. Before you write

**A rule is a formula that TM1 evaluates every time a cell is read.** That makes
rules ideal for values that must always reflect current inputs (price × volume,
ratios, currency conversion), and expensive for values that rarely change.

Use a TurboIntegrator (TI) process instead when the value:

- is loaded once and doesn't change,
- is needed only at period end, or
- is costly to calculate and read constantly.

Have these to hand:

| You need | Where to find it |
|---|---|
| Cube name and its dimensions, **in order** | Modeling workbench → database tree → cube, or the cube's dimension list |
| Exact element names | The dimension editor. Names must match exactly |
| Which cells people type into, and which the rule fills | The business owner. A rule-filled cell can't be typed into |
| The cube's current rule file | The rules editor (section 3). Saving replaces the whole file |

## 2. Write the rule

A rule file has four parts, in this order:

```
FEEDSTRINGS;          # only if any rule returns text
SKIPCHECK;
# rules: the calculations, most specific first
FEEDERS;
# feeders: which cells the calculations can make non-empty
```

**Write the rule.** For example, Revenue is units times price, at leaf level only:

```
['Sales Measure':'Revenue'] = N: ['Units'] * ['Price'];
```

| Part | Meaning |
|---|---|
| `['Sales Measure':'Revenue']` | Which cells: Revenue in the Sales Measure dimension |
| `N:` | Leaf cells only. Totals still add up normally |
| `['Units'] * ['Price']` | The formula, read at the same coordinates |

**Write its feeder in the same step.** With `SKIPCHECK` on, TM1 skips cells it
thinks are empty, and a rule cell is "empty" until something feeds it. Feed from
the input that is most often empty, here Units:

```
FEEDERS;
['Sales Measure':'Units'] => ['Sales Measure':'Revenue'];
```

A rule without its feeder shows correct values cell by cell, but totals read zero
and zero-suppressed views hide the rows.

**Watch for these mistakes:**

- **Division.** `\` returns 0 on division by zero, and `/` returns N/A.
- **Strings.** Compare with `@=`, not `=`.
- **Logic.** OR is `%`, AND is `&`, NOT is `~`. `|` joins text.
- **Order.** The first matching statement wins, so put exceptions such as `STET`
  above general rules.

## 3. Put it on the server through PAW

Since PAW 2.0.78, rules are created and edited only in a **Modeling workbench**.
The options in a book's Databases tree are gone. You need the modeler or
administrator role.

1. **Open a workbench.** Go to **Data and Models**, open an existing Modeling
   workbench, or use **Create → Modeling workbench**. Workbenches exist only in the
   new PAW experience, not in PAW Classic.
2. **Find the cube.** In the workbench's database tree, expand the database, then
   **Cubes**.
3. **Open the rules editor.** Right-click the cube and choose **Create business
   rules** if it has none, or **Edit business rules** if it has some. To give the
   editor more room, use **Open tab in floating window**.
4. **Bring the rules in:**
   - **Typing a new rule:** use **Ctrl+Space** for auto-complete of dimensions,
     elements and functions.
   - **Importing an existing `.rux` or text file:** open it locally, copy the
     contents and paste them into the editor. That works in every release. For a
     scripted import, use one of the routes in section 4.
   - **Changing an existing file:** edit in place. Don't paste over it unless your
     text already contains everything the server has.
5. **Validate.** Click **Validate business rules**. Fix every error it reports
   before saving.
6. **Review your change** (PAW 2.1.22 and later):
   - **Diff view** compares your unsaved edits with the saved version, and shows
     if someone else changed the rules while you were editing.
   - **Split view** puts the rules and the feeders side by side.
7. **Save.** TM1 compiles the file and reprocesses the cube's feeders. On a large
   cube this takes time.
8. **Process feeders**, if you changed a conditional feeder's condition data rather
   than the rule text. Use **Process feeders** in the editor's top-right menu. It
   runs `CubeProcessFeeders` for the cube.

### What the rules editor gives you

| Feature | How | Use it for |
|---|---|---|
| Auto-complete | **Ctrl+Space** | Cube, dimension, element and function names, narrowed as you type. This avoids misspelt element names, the most common silent failure |
| Function list | Function icon | Inserts a rules function, by category, with placeholders for its arguments |
| Rule Builder | Editor toolbar (IBM documents it; check your release has it) | Builds a `DB()` reference by picking a slice of a cube |
| Validate business rules | Validation icon | Checks syntax and structure **without saving** |
| Process feeders | Top-right menu | Runs `CubeProcessFeeders` for this cube |
| Shortcut keys | Shortcuts icon | Lists the editing, find/replace and navigation keystrokes |
| Find in tree | Toolbar button | Shows the cube in the database tree |
| Split view, Diff view | Toolbar (PAW 2.1.22+) | Rules and feeders side by side. Your unsaved edits compared with the saved version |
| Line wrap, font | Toolbar icons | Readability |

There's no documented import or upload button. Paste the file's text in, or use
one of the routes in section 4.

## 4. Other ways to load rules

Use these to promote rules between environments in a repeatable way, rather than
pasting by hand in production.

**TurboIntegrator.** `RuleLoadFromFile` replaces a cube's rules with a text file's
contents. It works on TM1 v11 and v12.

```
RuleLoadFromFile('Sales', 'Sales.rux');
# RuleLoadFromFileEx('Sales', 'Sales.rux', 'UTF-8') also sets the character set
```

Without a full path, the file is read from the database's data directory. Without
an extension, `.rux` is assumed. On TM1 v12 / PA as a Service, the file has to be
in the database's file area first.

**TM1 REST API:**

| Call | Does |
|---|---|
| `GET /api/v1/Cubes('Sales')?$select=Rules` | Read the current rules |
| `PATCH /api/v1/Cubes('Sales')` with `{"Rules": "<full text>"}` | Replace the rules. Send the **whole** file |
| `POST /api/v1/Cubes('Sales')/tm1.CheckRules` | Check the saved rules for errors, without changing anything |

On PA on Cloud, the TM1 REST API sits behind PAW at
`/tm1/api/<database>/api/v1/…` and expects a PAW session. A script using Basic
auth got a `401` and a redirect to the login page in testing.

**AI assistants on the PA MCP endpoint.** The `ibm-pa-tools` endpoint (1.27.2) has
tools for cubes, views, dimensions, sandboxes and TI processes, but none for rules.
An assistant connected only through MCP can draft rules but can't save them. Paste
its output into the workbench.

## 5. Test it

1. **Check the number.** Open a view of the cube, ideally in a sandbox, enter an
   input (Units), and confirm the calculated cell (Revenue).
2. **Check totals.** Look at the consolidation above it. If the leaf shows a value
   but the total is zero, the rule is unfed.
3. **Check feeders.** Right-click a consolidated cell in an exploration and choose
   **Check feeders**. The report shows whether the components are fed.
4. **Turn on zero suppression.** Calculated rows should still show. String results
   should still show too (they need `FEEDSTRINGS`).
5. **Check input cells.** Cells that should stay typeable must still accept input.
   If one doesn't, a rule covers it.

## 6. Troubleshooting

| You see | Look at |
|---|---|
| Total is zero, children have values | Missing feeder. For `DB()` rules, the feeder belongs in the **source** cube |
| `N/A` | `/` dividing by zero (use `\`), or a reference to an element that doesn't exist |
| Rule has no effect | A broader statement above it, or a misspelt element name in the area |
| Total doesn't equal the sum of its parts | The rule has no `N:` and also overrides the total |
| Text disappears | `FEEDSTRINGS` missing, or the string cell unfed |
| Model slower, or memory up, after a change | Overfeeding: a feeder from a total, or to an unqualified target |
| Save fails | Validation error. Read the message for the line, and check `;` and quotes first |
| `invalid string expression` | A `!Dim` names a dimension that isn't in this cube, or a `DB()` argument isn't an element name |
| Text rule shows nothing | It uses `N:`. String cells need `S:` (or no qualifier) |
| `Possible Circular Reference` | Two statements depend on each other |
| A rule is slow | Set `RULE_STATS` to YES for the cube in `}CubeProperties`, then read `}StatsByRule` (run count and time per line). Turn it off afterwards |

## 7. Keep it maintainable

- **Comment every statement** with `#`, saying what it does and why, especially any
  statement without `N:`.
- **Keep the `.rux` files in source control.** Promote dev → test → prod with
  `RuleLoadFromFile` or REST, not by retyping.
- **Don't edit production rules directly.** Change dev, validate, test, then
  promote.
- **Re-read the whole file before adding a statement.** Where it sits decides
  whether it ever fires.
