"""Tests against MDX captured from a live PAW dashboard (pa-context-json-example.md)."""
import json
import unittest

from cell_lineage import cell_coordinates, describe_view, lineage_mdx

# Route P&L table (4 measures x leaf routes)
PNL = ("SELECT {[DRP P&L Line].[DRP P&L Line].[Total Revenue],[DRP P&L Line].[DRP P&L Line].[Total Variable Cost],"
       "[DRP P&L Line].[DRP P&L Line].[Contribution Margin],[DRP P&L Line].[DRP P&L Line].[Contribution Margin %]} ON 0, "
       "{EXCEPT({DESCENDANTS([DRP Route].[DRP Route].[All Domestic Routes])}, {[DRP Route].[DRP Route].[Trunk Routes], "
       "[DRP Route].[DRP Route].[Leisure Routes], [DRP Route].[DRP Route].[Long Domestic Routes], "
       "[DRP Route].[DRP Route].[Other Domestic Routes], [DRP Route].[DRP Route].[All Domestic Routes]}, ALL)} ON 1 "
       "FROM [DRP Route P&L] WHERE ([DRP Version].[DRP Version].[Actual], [DRP Period].[DRP Period].[FY2026], "
       "[DRP Aircraft Type].[DRP Aircraft Type].[All Aircraft])")

# Same table after Total Revenue was drilled
DRILL = PNL.replace(
    PNL[PNL.index("SELECT {") + 7: PNL.index("} ON 0") + 1],
    "{DRILLDOWNMEMBER({[DRP P&L Line].[DRP P&L Line].[Total Revenue]}, {[DRP P&L Line].[DRP P&L Line].[Total Revenue]})}")

# Budget variance table, rows sorted by Var to Budget %
VAR = ("SELECT {[DRP Version].[DRP Version].[Actual],[DRP Version].[DRP Version].[Budget],"
       "[DRP Version].[DRP Version].[Var to Budget],[DRP Version].[DRP Version].[Var to Budget %]} ON 0, "
       "{ORDER({DISTINCT({EXCEPT({DESCENDANTS([DRP Route].[DRP Route].[All Domestic Routes])}, "
       "{[DRP Route].[DRP Route].[All Domestic Routes], [DRP Route].[DRP Route].[Leisure Routes], "
       "[DRP Route].[DRP Route].[Trunk Routes], [DRP Route].[DRP Route].[Long Domestic Routes], "
       "[DRP Route].[DRP Route].[Other Domestic Routes]}, ALL)})}, "
       "[DRP Route P&L].([DRP Version].[DRP Version].[Var to Budget %]), BASC)} ON 1 "
       "FROM [DRP Route P&L] WHERE ([DRP Period].[DRP Period].[FY2026], "
       "[DRP Aircraft Type].[DRP Aircraft Type].[All Aircraft], [DRP P&L Line].[DRP P&L Line].[Contribution Margin])")

# KPI tile with a calculated member
CALC = ("WITH MEMBER [DRP Route].[DRP Route].[Weak Route Count] AS COUNT(FILTER({[DRP Route].[DRP Route].[MEL-SYD],"
        "[DRP Route].[DRP Route].[MEL-BNE]} , [DRP P&L Line].[DRP P&L Line].[Contribution Margin %] < 0.15)) "
        "SELECT {[DRP P&L Line].[DRP P&L Line].[Contribution Margin %]} ON 0, "
        "{[DRP Route].[DRP Route].[Weak Route Count]} ON 1 FROM [DRP Route P&L] "
        "WHERE ([DRP Version].[DRP Version].[Actual], [DRP Period].[DRP Period].[FY2026], "
        "[DRP Aircraft Type].[DRP Aircraft Type].[All Aircraft])")


def dims(view, axis):
    return [d["dimension"] for d in view["axes"][axis]["dimensions"]]


class DescribeView(unittest.TestCase):
    def test_pnl(self):
        v = describe_view(PNL)
        self.assertEqual(v["cube"], "DRP Route P&L")
        self.assertEqual(dims(v, 0), ["DRP P&L Line"])
        self.assertEqual(dims(v, 1), ["DRP Route"])
        self.assertTrue(v["axes"][0]["members_readable_from_text"])
        self.assertEqual(v["axes"][0]["literal_members"],
                         ["Total Revenue", "Total Variable Cost", "Contribution Margin", "Contribution Margin %"])
        self.assertFalse(v["axes"][1]["members_readable_from_text"])
        self.assertEqual([s["dimension"] for s in v["slicer"]], ["DRP Version", "DRP Period", "DRP Aircraft Type"])

    def test_drilldown_columns_not_readable(self):
        v = describe_view(DRILL)
        self.assertEqual(dims(v, 0), ["DRP P&L Line"])
        self.assertFalse(v["axes"][0]["members_readable_from_text"])

    def test_sorted_rows_exclude_sort_measure_dimension(self):
        v = describe_view(VAR)
        self.assertEqual(dims(v, 0), ["DRP Version"])
        self.assertEqual(dims(v, 1), ["DRP Route"])
        self.assertTrue(v["axes"][1]["sorted_by_value"])
        self.assertIn("DRP P&L Line", [s["dimension"] for s in v["slicer"]])

    def test_calculated_member(self):
        v = describe_view(CALC)
        self.assertEqual(v["calculated_members"][0]["member"], "Weak Route Count")
        self.assertEqual(dims(v, 1), ["DRP Route"])


class Coordinates(unittest.TestCase):
    def test_var_cell(self):
        c = cell_coordinates(VAR, ["MEL-BNE"], ["Actual"])
        got = {x["dimension"]: (x["member"], x["source"]) for x in c["coordinates"]}
        self.assertEqual(got, {
            "DRP Version": ("Actual", "axis 0"),
            "DRP Route": ("MEL-BNE", "axis 1"),
            "DRP Period": ("FY2026", "slicer"),
            "DRP Aircraft Type": ("All Aircraft", "slicer"),
            "DRP P&L Line": ("Contribution Margin", "slicer"),
        })

    def test_label_count_mismatch(self):
        with self.assertRaises(ValueError):
            cell_coordinates(PNL, ["SYD-BNE", "extra"], ["Total Revenue"])

    def test_calc_flagged(self):
        c = cell_coordinates(CALC, ["Weak Route Count"], ["Contribution Margin %"])
        route = next(x for x in c["coordinates"] if x["dimension"] == "DRP Route")
        self.assertTrue(route["calculated"])
        with self.assertRaises(ValueError):
            lineage_mdx(c["cube"], c["coordinates"], "DRP Route")


class Lineage(unittest.TestCase):
    def test_route_lineage(self):
        c = cell_coordinates(PNL, ["SYD-BNE"], ["Total Revenue"])
        q = lineage_mdx(c["cube"], c["coordinates"], "DRP Route")
        self.assertEqual(
            q["rollup_path"],
            "SELECT {[DRP P&L Line].[DRP P&L Line].[Total Revenue]} ON 0, "
            "{ASCENDANTS([DRP Route].[DRP Route].[SYD-BNE])} ON 1 FROM [DRP Route P&L] "
            "WHERE ([DRP Version].[DRP Version].[Actual], [DRP Period].[DRP Period].[FY2026], "
            "[DRP Aircraft Type].[DRP Aircraft Type].[All Aircraft])")
        self.assertIn("TM1SUBSETALL([DRP Route].[DRP Route])", q["all_direct_parents"])
        self.assertIn("[}ElementAttributes_DRP Route]", q["attributes"])

    def test_measure_lineage_moves_route_to_columns(self):
        c = cell_coordinates(PNL, ["SYD-BNE"], ["Total Revenue"])
        q = lineage_mdx(c["cube"], c["coordinates"], "DRP P&L Line")
        self.assertTrue(q["children"].startswith("SELECT {[DRP Route].[DRP Route].[SYD-BNE]} ON 0, "
                                                 "{[DRP P&L Line].[DRP P&L Line].[Total Revenue].CHILDREN} ON 1"))


if __name__ == "__main__":
    unittest.main()
