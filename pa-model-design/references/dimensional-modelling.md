# Dimensional modelling

Version-neutral. Verify version-specific syntax against
`{{config.platform.docs_base}}/{{config.platform.pa_version}}`.

## 1. Grain before structure

The leaf grain of every dimension is the single most expensive decision in the model,
because changing it later means rebuilding the dimension and reloading every cube
that uses it.

Fix the grain by answering two questions:

- **Input grain.** What is the most detailed thing a user will actually type?
- **Reporting grain.** What is the most detailed thing anyone will need to see?

Leaves sit at the input grain. If reporting needs something finer than anyone inputs,
the model is missing a source feed, not a dimension level.

Do not add a level "in case we need it later", with time the one exception (see §4).

## 2. Cube inventory

One cube per coherent grain. Split when:

| Signal | Action |
|---|---|
| Measures share all dimensional axes | Keep in one cube |
| Measures differ in grain (daily actuals vs monthly budget) | Separate cubes |
| Some measures are input, others are reference data | Separate input cube and reference cube |
| A reporting view needs a different, flatter shape | Separate reporting cube, populated by TI or rules |
| Access rules differ fundamentally by measure | Separate cubes, or a cell security cube |

Do **not** split a cube merely because it has many measures. That is what the measure
dimension is for.

Apply `{{config.modelling.max_dimensions_per_cube}}`. A cube over the limit usually has
two grains fused; look for a dimension that is only meaningful for some measures.

## 3. Element types

TM1 has exactly three:

| Type | Code | Holds input |
|---|---|---|
| Numeric | N | Yes |
| String | S | Yes, text only |
| Consolidated | C | No. A write to a C cell spreads proportionally across its N descendants |

That spreading behaviour is a frequent source of "who changed my numbers". If a
consolidated cell must not be writable, that is a security or view-design decision.
Element type alone will not stop it.

## 4. Hierarchies

- Give every dimension a single top-level consolidation. Views and rules that need
  "everything" then have something to point at.
- Keep branches the same depth where you can. Ragged hierarchies make MDX and
  reporting harder for no structural gain.
- Never let a member be both an input cell and a consolidation. That double-counts.
- **Time is the exception to "no speculative levels."** Add the quarter rollup even
  for a monthly model when `{{config.modelling.time.include_quarter_rollup}}` is true.
  It costs nothing and retrofitting it means rebuilding the dimension.
- Fiscal year start comes from `{{config.modelling.time.fiscal_year_start_month}}`.
  Never assume January.

Use alternate hierarchies only when a dimension genuinely has two independent rollups
(cost centre by geography *and* by business unit). Never add one speculatively, since
each one is another thing to maintain.

### Inheriting a dimension you didn't build

Dimensions sourced from SAP or an older model carry defects you have to design
around, not just record. Check these before scoping a load. Each was found on a live
model:

- **Mixed-level consolidations.** A node with both leaf and consolidated children.
  Any script or rule that treats "reporting line" as "a node whose children are all
  leaves" drops the direct leaves. On one model that lost 91 marketing accounts and
  turned a DC cost block positive, because only its income line was loaded.
- **Period-to-date consolidations that include an opening-balance member.** If
  `06 YTD` = `00` + `01` ... `06`, load nothing to `00` for flow measures. Load monthly
  leaves only and let the YTD consolidations sum them. Loading YTD directly
  double-counts.
- **Rollups with missing or wrong children.** Compare sibling consolidations of the
  same family. Rolling-3 nodes with two children each, built before a month existed,
  give wrong numbers silently. Keep them out of subsets until rebuilt.
- **Element index out of sequence.** A member added later carries a late index. Sort
  subsets by name or hierarchy, never by index.
- **Accounting constructs filed beside operating units.** Calendar-adjustment and
  lease-overlay centres under a "Distribution Centres" node are not warehouses. Read
  member names before loading operational data to them.
- **Mis-parented members.** A code that embeds another parent's key, such as a
  department leaf of store 1190 under store 1001. Load and label it, or exclude it,
  but footnote every total it touches.
- **Overlapping channel accounts.** Two account families, for example store and
  admin, each carrying a sales line under one +1-weighted total. Load both and
  company revenue double-counts. Decide which channel owns each posting.
- **Untidy names.** Trailing full stops and double spaces in element names break
  exact-match lookups. Quote names from the server, never retype them.

### Sign convention follows the weights

If every weight on the account or measure dimension is +1, costs must be stored
negative or rollups add cost to revenue. Record the convention in the spec. Variance
formulas and agent instructions depend on it. See
`views-and-calculated-members.md` §2.

## 5. Measure dimension

When `{{config.modelling.measure_dimension}}` is `required`, every cube gets one,
named per `{{config.naming.measure_dimension}}`.

It pays for itself because:

- Rules scope precisely: `[{Measure}:'Amount'] = N: [{Measure}:'Rate'] * [{Measure}:'Quantity'];`
- Feeders stay narrow: `[{Measure}:'Rate'] => [{Measure}:'Amount'];`
- A new metric is one element, not a new cube.

Mark each measure as **input**, **rule-derived**, or **loaded**. Rule-derived measures
must be protected from manual entry when
`{{config.rules.protect_calculated_measures}}` is true, through cell security or
input view design. A rule-derived cell that a user can type into will silently disagree with
its own formula.

## 6. Sparsity and dimension order

TM1 stores data sparsely: empty cells cost nothing. Consequences:

- A large dimension with few populated combinations is cheap. Do not denormalise to
  avoid it.
- Rule-derived cells do not exist until fed. Sparsity is why feeders exist at all.
- Sparsity **changes over time**. What is dense in year one may be sparse by year
  three. Revisit order when data volume changes materially, not just at build time.

### Order policy

Apply `{{config.modelling.dimension_order_policy}}`.

Under `hourglass`, the widely used TM1 rule of thumb:

```
smallest sparse -> largest sparse -> smallest dense -> largest dense
```

The **last dimension matters most**: it forms the columns of TM1's storage arrays, so a
wide, dense last dimension compresses well and shortens the key for every other
dimension. A measure dimension often lands last for exactly that reason, because it
is small and dense, not because of anything to do with rule scoping.

Two cautions, both worth stating in the spec:

- There is no single optimal order. Storage size, view retrieval, and write-back each
  favour different orders. Name which one you optimised for.
- Density beats raw size for choosing the last dimension once dimensions are large.

Under `manual`: record the order the project supplies and offer no reordering advice.

## 7. Attributes

| Kind | Use | Access in rules |
|---|---|---|
| Alias | Alternative display name | resolved automatically |
| String | Metadata that drives logic or display | `ATTRS(dim, element, attr)` |
| Numeric | Sort order, weights, factors | `ATTRN(dim, element, attr)` |

Attributes are the right home for anything that varies *by member* and would otherwise
be hard-coded into a rule. A rule containing a literal list of element names is almost
always an attribute waiting to be created.

Attributes write to the `}ElementAttributes_<dim>` control cube. They don't touch
members, parentage or weights, so they are allowed under a "no dimension changes"
constraint and come off cleanly.

**Alias versus String for display text.** An alias must be unique within the
hierarchy **and** must not equal any existing element name, or TM1 rejects it. Use an
`Alias` for display names that are unique by construction, such as "Northside VIC" for
a store code. Use a `String` attribute for descriptions that legitimately repeat,
such as "Store payroll cost" on many accounts. Check collisions before writing: on one
model `Total Admin`, `Total Trading Stores` and `Total Distribution Centres` already
existed as elements, which forced different alias text for three rollups.

**Label text you made up.** If the source has no description, as with GL accounts
exported as bare codes, any text you generate is derived, not authoritative. Prefix it
`[derived]` or `[assumed]` and keep the code inside the alias, for example
"Northside VIC Electrical (EL)", so anyone who knows the real meaning spots a wrong
one. Record where real descriptions would come from, such as the SAP GL text table.

Agents and users can only find a member by name if the name exists somewhere in the
model. See `views-and-calculated-members.md` §8.

Attribute naming follows `{{config.naming.attribute_case}}`.
