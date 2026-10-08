# Rule examples

Each example pairs the rule with its feeder and says why. Cube, dimension and
element names are illustrative. Map them to the real names in Step 0 of the skill.

Cubes used below:

| Cube | Dimensions, in order |
|---|---|
| `Sales` | Version, Period, Product, Region, Sales Measure |
| `Exchange Rates` | Version, Period, Currency, Rate Measure |
| `Balance` | Version, Period, Account, Balance Measure |

## 1. Price × volume

```
SKIPCHECK;
['Sales Measure':'Revenue'] = N: ['Units'] * ['Price'];

FEEDERS;
['Sales Measure':'Units'] => ['Sales Measure':'Revenue'];
```

- `N:` so Revenue still consolidates by summing.
- The feeder comes from **Units**, not Price. A price exists for every product in
  every period, but units only where something sold. Feeding from Price would mark
  every price-bearing cell as non-empty.

## 2. A ratio that must not be summed

```
['Sales Measure':'Margin %'] = ['Margin'] \ ['Revenue'];
# No N:/C: on purpose: a total margin % is total margin over total revenue, not a sum of percentages.

FEEDERS;
['Sales Measure':'Revenue'] => ['Sales Measure':'Margin %'];
```

- Leaving off `N:` makes the same formula compute at every level, which is right
  for a ratio. Comment why, so a reviewer doesn't "fix" it (`RUL-003`).
- `\` returns 0 where Revenue is empty, instead of N/A.

## 3. Input allowed for one version only

```
['Version':'Budget', 'Sales Measure':'Price'] = STET;    # budget price is typed in
['Sales Measure':'Price'] = N: ['Revenue'] \ ['Units'];  # every other version derives it
```

The `STET` statement must sit **above** the general one. Swap them and Budget Price
becomes read-only.

## 4. Lookup from another cube

```
['Sales Measure':'Revenue Reporting'] = N:
    ['Revenue'] * DB('Exchange Rates', !Version, !Period,
                      ATTRS('Region', !Region, 'Currency'), 'Rate');

FEEDERS;
['Sales Measure':'Revenue'] => ['Sales Measure':'Revenue Reporting'];
```

- `DB()` takes all four `Exchange Rates` dimensions, in that cube's order.
- The sparse operand (Revenue) is in this cube, so the feeder lives here. No
  feeder is needed in `Exchange Rates`, because a rate on its own never makes
  Revenue Reporting non-zero.

## 5. Pulling a value in, with the feeder in the source cube

Rule in **`Margin`** (Version, Period, Product, Margin Measure):

```
['Margin Measure':'Units'] = N: DB('Sales', !Version, !Period, !Product, 'Total Region', 'Units');
```

Feeder in **`Sales`**:

```
FEEDERS;
['Sales Measure':'Units'] => DB('Margin', !Version, !Period, !Product, 'Units');
```

- The value comes from `Sales`, so `Sales` is where a new entry happens, and its
  feeder must point at `Margin` (`FED-002`). This feeder is the one most often
  forgotten, because it lives in a different file from the rule.
- The rule reads the consolidation `Total Region`, but the feeder is written on
  leaf Units in `Sales`. Every region's units feed the single Margin cell.
- IBM's Fishcakes example writes the same feeder with the consolidation named on
  the left side, mirroring the rule:
  `['Total Markets','Quantity Purchased - Kgs'] => DB('Inventory', !FishType, !Date, '1', 'Quantity in Stock - Kgs');`
  Both forms feed the one target cell. The left-side form reads as the exact
  inverse of the rule.

## 6. Conditional feeder

Only active products get a commission.

```
['Sales Measure':'Commission'] = N:
    IF(ATTRN('Product', !Product, 'Active') = 1, ['Revenue'] * 0.05, 0);

FEEDERS;
['Sales Measure':'Revenue'] =>
    DB(IF(ATTRN('Product', !Product, 'Active') = 1, 'Sales', ''),
       !Version, !Period, !Product, !Region, 'Commission');
```

The feeder mirrors the rule's condition, so inactive products aren't fed.
Conditional feeders aren't supported with multi-threaded feeders (`MTFeeders`). On
such servers, disable multi-threaded loading for this cube, or feed
unconditionally. A
feeder's condition is evaluated when the feeder fires. If the attribute changes
later, reprocess feeders (the **Process feeders** button in the rules editor, or
`CubeProcessFeeders` in TI).

## 7. String rule

`Status` must be a **string** element in `Sales Measure`, the cube's last
dimension.

```
FEEDSTRINGS;
SKIPCHECK;
['Sales Measure':'Status'] = S: IF(['Units'] > 0, 'Selling', 'No sales');

FEEDERS;
['Sales Measure':'Units'] => ['Sales Measure':'Status'];
```

- `S:` because a cell whose last coordinate is a string element is a string cell.
  `N:` covers leaf **numeric** cells only, so an `N:` statement would never fire
  here.
- Both `IF` branches are strings. Mixing a string and a number is an error.
- Reading `Units` with `['Units']` is fine because it's numeric. To read another
  string cell, use `DB()`, even in the same cube.
- Without `FEEDSTRINGS` and the feeder, `Status` disappears from zero-suppressed
  views.

## 8. Opening balance from the prior period

Each `Period` element has string attributes `Prior` and `Next`, and the first and
last periods hold an empty value.

```
['Balance Measure':'Opening'] = N:
    IF(ATTRS('Period', !Period, 'Prior') @= '', 0,
       DB('Balance', !Version, ATTRS('Period', !Period, 'Prior'), !Account, 'Closing'));

FEEDERS;
['Balance Measure':'Closing'] =>
    DB(IF(ATTRS('Period', !Period, 'Next') @= '', '', 'Balance'),
       !Version, ATTRS('Period', !Period, 'Next'), !Account, 'Opening');
```

- The feeder looks **forward** (Closing feeds the next period's Opening), while
  the rule looks back.
- Both ends are guarded explicitly. The rule returns 0 in the first period. In the
  last period, the feeder's cube name becomes empty, which is the
  conditional-feeder mechanism, so nothing is fed. IBM's guide also guards these
  edges explicitly rather than referencing a non-existent element.
- Attributes keep the logic independent of where consolidations sit in the
  dimension. The `DIMIX`/`DNEXT` alternative is in example 9.
- If Opening has no `C:` rule, a full-year total would sum twelve opening balances.
  Add a `C:` statement or exclude the measure from period consolidations.

## 9. Actuals, then projection, from a user-set current month

Adapted from IBM's Rules guide (time-based calculations). `Plan` has Product,
Month and Plan Measure. `Control` is a two-dimensional string cube whose single
cell holds the current month's name. Months 1–12 come first in the Month
dimension, with quarters and the year after them.

```
['Plan Measure':'Units'] =
    IF(DIMIX('Month', !Month) < DIMIX('Month', DB('Control', 'Value', 'Current Month')),
       DB('Actuals', !Product, !Month, 'Units'),
       DB('Plan', !Product, DIMNM('Month', DIMIX('Month', !Month) - 1), 'Units') * ['Growth %']);

FEEDERS;
['Plan Measure':'Units'] =>
    DB('Plan', !Product,
       IF(DIMIX('Month', !Month) < 12, DNEXT('Month', !Month), 'December'),
       'Units');
```

- One statement covers every month, and nobody edits the rule month to month.
  Users change the `Control` cell.
- Prefer the control cube over `TIMVL(NOW, 'M')`: it lets the business hold a
  month open until actuals are ready, and roll back to review an earlier
  projection.
- The feeder's `IF` stops `DNEXT` stepping from December into Q1, Q2 … Total Year.
  Feeding those consolidations would feed the whole cube.
- `DB('Control', …)` is how a rule reads a string cell.
- The `Actuals` cube also needs a feeder into `Plan` for the months pulled from it.
  It goes in the `Actuals` rule, because cross-cube feeders live in the source.

## 10. Allocation across two cubes

Adapted from IBM's Rules guide (fixed allocations). Fish required per cake is cake
production times the recipe percentage:

```
# in FishRequired (CakeType, FishType, Date, Measure)
['Qty Required - Kgs'] = N:
    DB('Production', !CakeType, !Date, 'Quantity Produced - Kgs')
  * DB('Ingredients', !CakeType, !FishType);
```

```
# in Production (CakeType, Date, Measure)
FEEDERS;
['Quantity Produced - Kgs'] =>
    DB('FishRequired', !CakeType, 'Total Fish Types', !Date, 'Qty Required - Kgs');
```

- The formula multiplies values from two cubes, so the feeder could live in either.
  It goes in **Production**, the sparser one: not every cake is made every day,
  while recipes are dense.
- FishRequired has a FishType dimension that Production lacks, so the feeder
  targets `Total Fish Types`, which feeds every fish type. This overfeeding is
  unavoidable when the target cube has more dimensions than the source.

## 11. A result that needs both operands

From IBM's stocks-and-flows example:

```
['Used'] = N: IF(['Available'] >= ['Required'], ['Required'], ['Available']);

FEEDERS;
['Available'] => ['Used'];
```

`Used` can only be non-zero when **both** Available and Required are, so one
feeder from either operand is enough. A second feeder would add nothing but cost.
Pick the sparser operand.
