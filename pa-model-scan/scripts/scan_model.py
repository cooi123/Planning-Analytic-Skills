#!/usr/bin/env python3
"""Read a TM1 model's structure into a JSON inventory using GET requests only."""
import argparse
from datetime import datetime, timezone
import json
import os
import sys
from urllib.parse import quote

import requests
from requests.auth import HTTPBasicAuth


class Client:
    def __init__(self, host, tenant, database, key):
        self.root = f"{host.rstrip('/')}/api/{quote(tenant, safe='')}/v0"
        self.base = f"{self.root}/tm1/{quote(database, safe='')}/api/v1"
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth('apikey', key)

    def get(self, path, accept='application/json'):
        url = path if path.startswith('https://') else f"{self.base}/{path}"
        return self.session.get(url, headers={'Accept': accept}, timeout=60)


def member(name):
    return "('" + quote(name.replace("'", "''"), safe='') + "')"


def scan(client, database):
    warnings = []

    def read(path, label, plain=False):
        try:
            response = client.get(path, accept='text/plain' if plain else 'application/json')
            if response.status_code != 200:
                warnings.append(f'{label} could not be read: HTTP {response.status_code}')
                return None if plain else []
            if plain:
                return response.text.strip()
            payload = response.json()
            rows = payload['value']
            if not isinstance(rows, list):
                raise ValueError('expected a value array')
            return rows
        except Exception as exc:
            # Exception messages can contain request credentials; report only the type.
            warnings.append(f'{label} could not be read: {type(exc).__name__}')
            return None if plain else []

    cubes = []
    for item in read('Cubes?$select=Name,Rules,LastDataUpdate,LastSchemaUpdate&$expand=Dimensions($select=Name)', 'Cubes'):
        name = item['Name']
        control = name.startswith('}')
        cube = dict(name=name, is_control=control,
                    dimensions=[d['Name'] for d in item.get('Dimensions', [])],
                    last_data_update=item.get('LastDataUpdate'),
                    last_schema_update=item.get('LastSchemaUpdate'))
        if not control:
            cube['rules'] = item.get('Rules') or None
            cube['views'] = [v['Name'] for v in read(f'Cubes{member(name)}/Views?$select=Name', f'Views for cube {name}')]
        cubes.append(cube)
    dimensions = []
    for item in read('Dimensions?$select=Name&$expand=Hierarchies($select=Name)', 'Dimensions'):
        name = item['Name']
        control = name.startswith('}')
        hierarchies = []
        for h in item.get('Hierarchies', []):
            if h['Name'] == 'Leaves':
                continue
            hierarchy = {'name': h['Name']}
            if not control:
                path = f'Dimensions{member(name)}/Hierarchies{member(h["Name"])}'
                elements = read(path + '/Elements?$select=Type', f'Elements for {name}/{h["Name"]}')
                hierarchy.update(element_count=len(elements),
                                 leaf_count=sum(e.get('Type') == 'Numeric' for e in elements),
                                 consolidated_count=sum(e.get('Type') == 'Consolidated' for e in elements),
                                 string_count=sum(e.get('Type') == 'String' for e in elements),
                                 attributes=[a['Name'] for a in read(path + '/ElementAttributes?$select=Name', f'Attributes for {name}/{h["Name"]}')])
            hierarchies.append(hierarchy)
        dimensions.append(dict(name=name, is_control=control, hierarchies=hierarchies))
    processes = []
    for p in read('Processes?$select=Name,PrologProcedure,MetadataProcedure,DataProcedure,EpilogProcedure,DataSource,Parameters', 'Processes'):
        if p['Name'].startswith('}'):
            continue
        ds = p.get('DataSource') or {}
        process = dict(name=p['Name'], is_control=False,
                       parameters=[dict(name=x['Name'], type=x.get('Type'), value=x.get('Value')) for x in p.get('Parameters', [])],
                       datasource=dict(type=None if ds.get('Type') == 'None' else ds.get('Type'), name=ds.get('dataSourceNameForServer'), view=ds.get('view')))
        for target, source in [('prolog', 'PrologProcedure'), ('metadata', 'MetadataProcedure'), ('data', 'DataProcedure'), ('epilog', 'EpilogProcedure')]:
            process[target] = p.get(source) or ''
        processes.append(process)
    chores = [dict(name=c['Name'], active=c.get('Active', False), start_time=c.get('StartTime'), frequency=c.get('Frequency'), processes=[t['Process']['Name'] for t in c.get('Tasks', []) if t.get('Process')]) for c in read('Chores?$expand=Tasks($expand=Process($select=Name))', 'Chores')]
    groups = [g['Name'] for g in read('Groups?$select=Name', 'Groups')]
    logs = [l['Filename'] for l in read('ErrorLogFiles?$select=Filename', 'Error logs')]
    version = read('Configuration/ProductVersion/$value', 'Server version', plain=True)
    return dict(schema_version=1, scanned_at=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'), source=dict(database=database, server_version=version), cubes=cubes, dimensions=dimensions, processes=processes, chores=chores,
                security=dict(groups=groups, cell_security_cubes=sorted(c['name'][14:] for c in cubes if c['name'].startswith('}CellSecurity_')), element_security_dimensions=sorted(c['name'][17:] for c in cubes if c['name'].startswith('}ElementSecurity_'))), error_logs=dict(count=len(logs), latest=sorted(logs, reverse=True)[:20]), warnings=warnings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('host', 'tenant', 'database', 'key-env', 'out'):
        parser.add_argument('--' + option, required=True)
    args = parser.parse_args()
    key = os.environ.get(args.key_env)
    if not key:
        parser.exit(1, f'environment variable {args.key_env} is not set\n')
    client = Client(args.host, args.tenant, args.database, key)
    try:
        response = client.get(client.root + '/rolemgmt/v1/users/me')
    except requests.RequestException:
        parser.exit(2, 'login failed: request error\n')
    if response.status_code != 200:
        parser.exit(2, f'login failed: HTTP {response.status_code}\n')
    inventory = scan(client, args.database)
    with open(args.out, 'w', encoding='utf-8') as handle:
        json.dump(inventory, handle, indent=2, ensure_ascii=False)
        handle.write('\n')
    print(', '.join(f'{len(inventory[k])} {k}' for k in ('cubes', 'dimensions', 'processes', 'chores', 'warnings')))


if __name__ == '__main__':
    main()
