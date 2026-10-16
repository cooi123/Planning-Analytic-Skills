import ast
from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scan_model


class Response:
    def __init__(self, rows=None, status=200, text=''):
        self.status_code, self.rows, self.text = status, rows, text

    def json(self):
        return {'value': self.rows}


class FakeClient:
    def __init__(self):
        self.calls = []

    def get(self, path, accept='application/json'):
        self.calls.append(('GET', path, accept))
        if path.startswith('Cubes?$'):
            return Response([dict(Name=n, Rules='rule', Dimensions=[{'Name':"D's & /"}], LastDataUpdate='data', LastSchemaUpdate='schema') for n in ["Sales' & /", '}CellSecurity_Sales', '}ElementSecurity_Region']])
        if '/Views?' in path:
            return Response(status=403)
        if path.startswith('Dimensions?$'):
            return Response([dict(Name="D's & /", Hierarchies=[{'Name':'Main'}, {'Name':'Leaves'}]), dict(Name='}Control', Hierarchies=[{'Name':'}Control'}])])
        if '/Elements?' in path:
            return Response([dict(Type=t) for t in ['Numeric','Numeric','Consolidated','String']])
        if '/ElementAttributes?' in path:
            raise RuntimeError('secret must never appear in warnings')
        if path.startswith('Processes?'):
            return Response([dict(Name='Load', Parameters=[dict(Name='pCube',Type='String',Value='Sales')], DataSource=dict(Type='TM1CubeView',dataSourceNameForServer='Sales',view='v'),PrologProcedure='code'),dict(Name='Empty',DataSource={'Type':'None'}),dict(Name='}Control',PrologProcedure='hidden')])
        if path.startswith('Chores?'):
            return Response([dict(Name='Nightly',Active=True,StartTime='start',Frequency='daily',Tasks=[{'Process':{'Name':'Load'}}])])
        if path.startswith('Groups?'):
            return Response([{'Name':'ADMIN'}])
        if path.startswith('ErrorLogFiles?'):
            return Response([{'Filename':f'{i:02}.log'} for i in range(25)])
        if path == 'Configuration/ProductVersion/$value':
            return Response(text='12.6.3\n')
        raise AssertionError(f'Unexpected path: {path}')


class ScanTests(unittest.TestCase):
    def test_inventory(self):
        client=FakeClient()
        inv=scan_model.scan(client,'Demo')
        self.assertEqual(set(inv),{'schema_version','scanned_at','source','cubes','dimensions','processes','chores','security','error_logs','warnings'})
        self.assertEqual(inv['schema_version'],1)
        self.assertRegex(inv['scanned_at'],r'^\d{4}-\d\d-\d\dT.*Z$')
        self.assertEqual(inv['source'],dict(database='Demo',server_version='12.6.3'))
        self.assertEqual(inv['cubes'][0],dict(name="Sales' & /",is_control=False,dimensions=["D's & /"],rules='rule',last_data_update='data',last_schema_update='schema',views=[]))
        self.assertNotIn('rules',inv['cubes'][1])
        self.assertNotIn('views',inv['cubes'][1])
        self.assertEqual(inv['dimensions'][0]['hierarchies'],[dict(name='Main',element_count=4,leaf_count=2,consolidated_count=1,string_count=1,attributes=[])])
        self.assertEqual(inv['dimensions'][1]['hierarchies'],[{'name':'}Control'}])
        self.assertEqual([p['name'] for p in inv['processes']],['Load','Empty'])
        self.assertEqual(inv['processes'][0],dict(name='Load',is_control=False,parameters=[dict(name='pCube',type='String',value='Sales')],datasource=dict(type='TM1CubeView',name='Sales',view='v'),prolog='code',metadata='',data='',epilog=''))
        self.assertIsNone(inv['processes'][1]['datasource']['type'])
        self.assertEqual(inv['chores'],[dict(name='Nightly',active=True,start_time='start',frequency='daily',processes=['Load'])])
        self.assertEqual(inv['security'],dict(groups=['ADMIN'],cell_security_cubes=['Sales'],element_security_dimensions=['Region']))
        self.assertEqual(inv['error_logs'],dict(count=25,latest=[f'{i:02}.log' for i in range(24,4,-1)]))
        self.assertEqual(len(inv['warnings']),2)
        self.assertIn('HTTP 403',inv['warnings'][0])
        self.assertIn('RuntimeError',inv['warnings'][1])
        self.assertNotIn('secret',json.dumps(inv))
        self.assertTrue(all(method=='GET' for method,_,_ in client.calls))
        self.assertIn("Cubes('Sales%27%27%20%26%20%2F')/Views?$select=Name",[p for _,p,_ in client.calls])
        self.assertFalse(any('Leaves' in p or "Hierarchies('%7DControl')" in p for _,p,_ in client.calls))
        self.assertEqual(client.calls[-1][2],'text/plain')

    def test_http_client(self):
        with patch.object(scan_model.requests,'Session') as session:
            client=scan_model.Client('https://example.test/','tenant','A / B','private')
            client.get('Cubes')
            session.return_value.get.assert_called_once_with('https://example.test/api/tenant/v0/tm1/A%20%2F%20B/api/v1/Cubes',headers={'Accept':'application/json'},timeout=60)
            self.assertEqual(client.session.auth.username,'apikey')
        tree=ast.parse(Path(scan_model.__file__).read_text())
        self.assertFalse(any(isinstance(n,ast.Attribute) and n.attr in {'post','put','patch','delete'} for n in ast.walk(tree)))

    def test_login_failure_and_missing_key(self):
        options=['scan_model.py','--host','https://example.test','--tenant','t','--database','D','--key-env','TEST_SCAN_KEY','--out','unused.json']
        for environment, code, message in [({},1,'environment variable TEST_SCAN_KEY is not set'),({'TEST_SCAN_KEY':'private'},2,'login failed: HTTP 401')]:
            with self.subTest(code=code), patch.object(sys,'argv',options), patch.dict('os.environ',environment,clear=True), patch.object(scan_model,'Client') as cls, redirect_stderr(io.StringIO()) as stderr:
                cls.return_value.get.return_value=Response(status=401)
                with self.assertRaises(SystemExit) as exc:
                    scan_model.main()
                self.assertEqual(exc.exception.code,code)
                self.assertIn(message,stderr.getvalue())
                self.assertNotIn('private',stderr.getvalue())
                if code==2:
                    self.assertEqual(cls.return_value.get.call_count,1)


if __name__ == '__main__':
    unittest.main()
