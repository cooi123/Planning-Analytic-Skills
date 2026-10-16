"""Tests against execute_mdx_and_get_view output captured live from PAW 2.1.23
(IBM_PA_Financial, Financial Reporting, Income Statement by Current Year)."""
import json
import unittest

import resolve_selected_cell as m

# The @tool decorator wraps the function; call the plain one underneath.
_cells_fn = getattr(m.resolve_selected_cells, "fn", None) or m.resolve_selected_cells


def resolve_cells(table_text, cells):
    out = _cells_fn(table_text, cells)
    return getattr(out, "content", out)


TABLE = (
    "|  | 2023 | Jan 2023 | Feb 2023 |\n"
    "| - | - | - | - |\n"
    "| Gross Margin | $61,573,533 | $6,058,518 | $5,622,345 |\n"
    "| Expenses | $21,435,447 | $1,910,647 | $1,832,537 |\n"
    "| Operating Income | $40,138,085 | $4,147,871 | $3,789,807 |\n"
    "| Taxes | $8,428,998 | $871,053 | $795,859 |\n"
    "| Net Income | $31,709,088 | $3,276,818 | $2,993,948 |"
)
# The MCP tool wraps the table in a JSON envelope with an opaque state blob.
ENVELOPE = json.dumps({"data": TABLE, "state": "eyJvcGFxdWUiOiJibG9iIn0="})


class CleanNumber(unittest.TestCase):
    def test_display_formats(self):
        cases = {
            "$31,709,088": 31709088,
            "79.4M": 79_400_000,
            "8,916.0K": 8_916_000,
            "(19,910,700)": -19910700,
            "−125.5": -125.5,
            "€ 1,000": 1000,
            "17.8%": 17.8,
            "31709087.5242995": 31709087.5242995,
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertAlmostEqual(m._clean_number(raw), expected, places=4)

    def test_unparseable(self):
        for raw in ("", "N/A", "abc"):
            self.assertIsNone(m._clean_number(raw))


class ResolveSelectedCells(unittest.TestCase):
    def test_currency_formatted_cell_matches(self):
        out = resolve_cells(ENVELOPE, [{"row_index": 4, "col_index": 0, "expected_value": "$31,709,088"}])
        self.assertIn("Row label: Net Income", out)
        self.assertIn("Column label: 2023", out)
        self.assertIn("MATCH CHECK: MATCH", out)

    def test_raw_value_matches_display(self):
        out = resolve_cells(ENVELOPE, [{"row_index": 4, "col_index": 0, "expected_value": "31709087.5242995"}])
        self.assertIn("MATCH CHECK: MATCH", out)

    def test_wrong_row_is_mismatch(self):
        out = resolve_cells(ENVELOPE, [{"row_index": 3, "col_index": 0, "expected_value": "$31,709,088"}])
        self.assertIn("MISMATCH", out)

    def test_several_cells_in_one_call(self):
        out = resolve_cells(TABLE, [
            {"row_index": 0, "col_index": 1, "expected_value": "6.1M"},
            {"row_index": 4, "col_index": 2, "expected_value": "$2,993,948"},
        ])
        self.assertIn("Cell 1:", out)
        self.assertIn("Row label: Gross Margin", out)
        self.assertIn("Cell 2:", out)
        self.assertIn("Column label: Feb 2023", out)
        self.assertEqual(out.count("MATCH CHECK: MATCH"), 2)

    def test_percentage_against_ratio(self):
        table = "|  | Margin % |\n| - | - |\n| Total | 0.178 |"
        out = resolve_cells(table, [{"row_index": 0, "col_index": 0, "expected_value": "17.8%"}])
        self.assertIn("MATCH CHECK: MATCH", out)

    def test_missing_expected_value_is_refused(self):
        out = resolve_cells(TABLE, [{"row_index": 4, "col_index": 0}])
        self.assertIn("ERROR", out)


if __name__ == "__main__":
    unittest.main()
