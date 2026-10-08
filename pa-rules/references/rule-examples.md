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

The feeder mirrors the rule's condition, so inactive products aren't fed. A
feeder's condition is evaluated when the feeder fires. If the attribute changes
later, reprocess feeders (the **Process feeders** button in the rules editor, or
`CubeProcessFeeders` in TI).

## 7. String rule

`Status` must be a **string** element in `Sales Measure`, the cube's last
dimension.

```
FEEDSTRINGS;
SKIPCHECK;
['Sales Measure':'Status'] = N: IF(['Units'] > 0, 'Selling', 'No sales');

FEEDERS;
['Sales Measure':'Units'] => ['Sales Measure':'Status'];
```

Without `FEEDSTRINGS` and the feeder, `Status` disappears from zero-suppressed
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
    DB('Balance', !Version, ATTRS('Period', !Period, 'Next'), !Account, 'Opening');
```

- The feeder looks **forward** (Closing feeds the next period's Opening), while
  the rule looks back.
- The rule's `IF` handles the first period explicitly, using `@=` because it's a
  string comparison. Don't rely on a `DB()` with an empty element name to return 0.
- For the last period, `Next` is empty, so the feeder target is invalid and nothing
  is fed. That's the same mechanism as the conditional feeder.
- If Opening has no `C:` rule, a full-year total would sum twelve opening balances.
  Add a `C:` statement or exclude the measure from period consolidations.
