import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_graph import arguments, build, to_mermaid


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.inventory = json.loads((Path(__file__).parent / 'fixtures/inventory_sample.json').read_text())

    def test_edges_and_observations(self):
        before = copy.deepcopy(self.inventory)
        deps = build(self.inventory)
        self.assertEqual(self.inventory, before)
        actual = {(e['kind'], e['from'], e['to']) for e in deps['edges']}
        self.assertEqual(actual, {
            ('rule_reads', 'cube:Rates', 'cube:DRP Route P&L'),
            ('feeds', 'cube:DRP Route P&L', 'cube:Summary'),
            ('ti_source', 'cube:Sales', 'process:Load Sales'),
            ('ti_reads', 'cube:Rates', 'process:Load Sales'),
            ('ti_writes', 'process:Load Sales', 'cube:Sales'),
            ('ti_clears', 'process:Load Sales', 'cube:Sales'),
            ('calls', 'process:Load Sales', 'process:Child'),
            ('runs', 'chore:Nightly', 'process:Load Sales'),
            ('shares_dimension', 'cube:DRP Route P&L', 'cube:Sales')})
        self.assertFalse(any('Commented' in n['id'] for n in deps['nodes']))
        self.assertEqual(deps['dynamic_refs'], [
            dict(object='cube:DRP Route P&L', kind='rule_reads', expression='sCube'),
            dict(object='process:Load Sales', kind='ti_reads', expression='1'),
            dict(object='process:Load Sales', kind='ti_reads', expression="pCube (default 'Rates')")])
        self.assertEqual(deps['observations'], dict(isolated_cubes=['Idle "Cube"'], cubes_without_rules=['Idle "Cube"', 'Rates', 'Sales', 'Summary'], unused_dimensions=['Unused'], unscheduled_processes=['Manual'], inactive_chores=['Disabled']))
        self.assertEqual(deps['edges'], sorted(deps['edges'], key=lambda e: (e['kind'],e['from'],e['to'],e['detail'])))

    def test_mermaid(self):
        diagram = to_mermaid(build(self.inventory), self.inventory)
        for line in ['flowchart LR', '  c0["DRP Route P&L"]', '  c1["Idle #quot;Cube#quot;"]', '  p1(["Load Sales"])', '  h1{{"Nightly"}}', '  c2 -- "DB()" --> c0', '  c0 -. "feeds" .-> c4', '  c3 -- "source" --> p1', '  p1 == "writes" ==> c3', '  p1 == "clears" ==> c3', '  p1 -- "calls" --> p0', '  h1 -- "runs" --> p1', '  c0 --- |"Period"| c3']:
            self.assertIn(line, diagram.splitlines())

    def test_unreferenced_control_cube_is_excluded(self):
        deps = build(self.inventory)
        self.assertNotIn('cube:}CellSecurity_Sales', {n['id'] for n in deps['nodes']})
        self.assertNotIn('}CellSecurity_Sales', to_mermaid(deps, self.inventory))

    def test_literal_control_cube_reference_is_known(self):
        self.inventory['cubes'].append(dict(name='}ClientGroups', is_control=True, dimensions=[]))
        self.inventory['processes'][0]['prolog'] += " CellGetS('}ClientGroups', 'client', 'group');"
        deps = build(self.inventory)
        control = next(n for n in deps['nodes'] if n['id'] == 'cube:}ClientGroups')
        self.assertNotIn('missing', control)
        self.assertIn(
            ('ti_reads', 'cube:}ClientGroups', 'process:Load Sales'),
            {(e['kind'], e['from'], e['to']) for e in deps['edges']})

    def test_parsing_and_missing(self):
        p = self.inventory['processes'][0]
        p['prolog'] = "cCube='Rates'; CCUBE='Sales'; CellIncrementN(f(1,2), ccube, 'a,b'); CellGetN(pCube,'x'); RunProcess('Child'); CubeClearData('Missing'); CellPutS('x','O''Brien','x'); #ignored"
        p['data'] = "\n # CellGetN('Commented',1);\n s='DB(''Fake'',1)';"
        deps = build(self.inventory)
        self.assertIn(dict(object='process:Load Sales',kind='ti_reads',expression="pCube (default 'Rates')"),deps['dynamic_refs'])
        self.assertTrue(next(n for n in deps['nodes'] if n['id']=='cube:Missing')['missing'])
        self.assertTrue(any(n['name']=="O'Brien" for n in deps['nodes']))
        self.assertFalse(any(n['name']=='Fake' for n in deps['nodes']))
        self.assertIn(('process:Load Sales','cube:Sales'),[(e['from'],e['to']) for e in deps['edges'] if e['kind']=='ti_writes'])
        diagram=to_mermaid(deps,self.inventory)
        self.assertIn('classDef missing stroke-dasharray: 5 5',diagram)
        self.assertRegex(diagram,r'class c\d+ missing')
        self.assertEqual(arguments("f(1,2), 'a,b', 'O''Brien')",0),['f(1,2)',"'a,b'","'O''Brien'"])

    def test_later_dynamic_assignment_invalidates_literal(self):
        self.inventory['processes'][0]['prolog'] = "cCube='Sales'; cCube=Expand('x'); CellPutN(1,cCube,'x');"
        deps = build(self.inventory)
        self.assertIn(dict(object='process:Load Sales', kind='ti_writes', expression='cCube'), deps['dynamic_refs'])
        self.assertFalse(any(e['kind'] == 'ti_writes' for e in deps['edges']))

    def test_no_edges_and_truncation(self):
        inv=copy.deepcopy(self.inventory)
        inv['cubes']=[inv['cubes'][4]]
        inv['processes']=[]
        inv['chores']=[]
        deps=build(inv)
        self.assertEqual(deps['edges'],[])
        self.assertIn('c0["Idle #quot;Cube#quot;"]',to_mermaid(deps,inv))
        deps['edges']=[dict(kind='shares_dimension',detail='x'*80,**{'from':deps['nodes'][0]['id'],'to':deps['nodes'][0]['id']})]
        self.assertIn('x'*59+'…',to_mermaid(deps,inv))


if __name__ == '__main__':
    unittest.main()
