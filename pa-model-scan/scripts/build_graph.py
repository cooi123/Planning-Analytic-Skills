#!/usr/bin/env python3
"""Build dependencies.json and a Mermaid architecture diagram from an inventory."""
import argparse
import json
from pathlib import Path
import re


def strip_comments(code):
    return '\n'.join(line for line in (code or '').splitlines() if not line.lstrip().startswith('#'))


def arguments(code, start):
    """Read arguments after an opening parenthesis, respecting TM1 string escapes."""
    result, begin, depth, quoted, i = [], start, 0, False, start
    while i < len(code):
        char = code[i]
        if char == "'":
            if quoted and i + 1 < len(code) and code[i + 1] == "'":
                i += 2
                continue
            quoted = not quoted
        elif not quoted:
            if char == '(':
                depth += 1
            elif char == ')':
                if depth == 0:
                    return result + [code[begin:i].strip()]
                depth -= 1
            elif char == ',' and depth == 0:
                result.append(code[begin:i].strip())
                begin = i + 1
        i += 1
    return []


def calls(code):
    # Tokenize strings as well so function-like text inside literals is ignored.
    pattern = r"'(?:[^']|'')*'|\b([A-Za-z_]\w*)\s*\("
    for match in re.finditer(pattern, code):
        if match.group(1):
            yield match.group(1).lower(), arguments(code, match.end())


def literal(expression):
    if re.fullmatch(r"'(?:[^']|'')*'", expression):
        return expression[1:-1].replace("''", "'")
    return None


def build(inventory):
    nodes, edges, dynamic_refs = {}, [], []
    cubes = [c for c in inventory['cubes'] if not c['is_control']]
    processes = [p for p in inventory['processes'] if not p['is_control']]

    def node(kind, name, missing=False):
        ident = f'{kind}:{name}'
        if ident not in nodes:
            nodes[ident] = dict(id=ident, type=kind, name=name)
            if missing:
                nodes[ident]['missing'] = True
        return ident

    for kind, objects in [('cube', cubes), ('process', processes), ('chore', inventory['chores'])]:
        for obj in objects:
            node(kind, obj['name'])
    known_cubes = {c['name'] for c in inventory['cubes']}

    def edge(source, target, kind, detail):
        entry = dict(**{'from': source, 'to': target}, kind=kind, detail=detail, dynamic=False)
        if entry not in edges:
            edges.append(entry)

    def reference(owner, kind, expression, target_type='cube', assignments=None, parameters=None):
        name = literal(expression)
        if name is None and assignments is not None:
            key = expression.lower()
            if key in (parameters or {}):
                expression = f"{expression} (default '{parameters[key]}')"
            else:
                name = assignments.get(key)
        if name is None:
            dynamic_refs.append(dict(object=owner, kind=kind, expression=expression))
            return None
        return node(target_type, name, target_type == 'cube' and name not in known_cubes)

    for cube in cubes:
        owner = 'cube:' + cube['name']
        parts = re.split(r'^\s*FEEDERS\s*;', strip_comments(cube.get('rules')), maxsplit=1, flags=re.I | re.M)
        for index, code in enumerate(parts):
            kind = 'feeds' if index else 'rule_reads'
            for function, args in calls(code):
                if function != 'db' or not args:
                    continue
                target = reference(owner, kind, args[0])
                if target and target != owner:
                    source, dest = (owner, target) if index else (target, owner)
                    edge(source, dest, kind, f'DB({args[0]}, ...) in {cube["name"]} rules')
    functions = {'cellgetn': ('ti_reads', 0), 'cellgets': ('ti_reads', 0), 'cellputn': ('ti_writes', 1), 'cellputs': ('ti_writes', 1), 'cellincrementn': ('ti_writes', 1), 'viewzeroout': ('ti_clears', 0), 'cubecleardata': ('ti_clears', 0), 'executeprocess': ('calls', 0), 'runprocess': ('calls', 0)}
    for process in processes:
        owner = 'process:' + process['name']
        ds = process.get('datasource') or {}
        if ds.get('type') == 'TM1CubeView' and ds.get('name'):
            source = node('cube', ds['name'], ds['name'] not in known_cubes)
            edge(source, owner, 'ti_source', 'TM1CubeView datasource')
        code = '\n'.join(strip_comments(process.get(section)) for section in ('prolog', 'metadata', 'data', 'epilog'))
        # Strings are tokens: an assignment-looking substring inside a string is ignored.
        assignments = {}
        for match in re.finditer(r"\b([A-Za-z_]\w*)\s*=\s*((?:'(?:[^']|'')*'|[^;'])*)\s*;|'(?:[^']|'')*'", code):
            if match.group(1):
                assignments[match.group(1).lower()] = literal(match.group(2).strip())
        parameters = {p['name'].lower(): p.get('value') for p in process.get('parameters', [])}
        for function, args in calls(code):
            if function not in functions:
                continue
            kind, position = functions[function]
            if len(args) <= position:
                continue
            target = reference(owner, kind, args[position], 'process' if kind == 'calls' else 'cube', assignments, parameters)
            if target:
                source, dest = (target, owner) if kind == 'ti_reads' else (owner, target)
                edge(source, dest, kind, function + '()')
    for chore in inventory['chores']:
        for name in chore['processes']:
            edge('chore:' + chore['name'], node('process', name), 'runs', 'chore task')
    for i, left in enumerate(sorted(cubes, key=lambda c: c['name'])):
        for right in sorted(cubes, key=lambda c: c['name'])[i + 1:]:
            shared = sorted(set(left['dimensions']) & set(right['dimensions']))
            if shared:
                edge('cube:' + left['name'], 'cube:' + right['name'], 'shares_dimension', ', '.join(shared))
    connected = {e[end] for e in edges if e['kind'] != 'shares_dimension' for end in ('from', 'to')}
    scheduled = {e['to'] for e in edges if e['kind'] in ('runs', 'calls')}
    used = {d for c in cubes for d in c['dimensions']}
    observations = dict(isolated_cubes=sorted(c['name'] for c in cubes if 'cube:' + c['name'] not in connected), cubes_without_rules=sorted(c['name'] for c in cubes if not (c.get('rules') or '').strip()), unused_dimensions=sorted(d['name'] for d in inventory['dimensions'] if not d['is_control'] and d['name'] not in used), unscheduled_processes=sorted(p['name'] for p in processes if 'process:' + p['name'] not in scheduled), inactive_chores=sorted(c['name'] for c in inventory['chores'] if not c['active']))
    return dict(schema_version=1, database=inventory['source']['database'], nodes=sorted(nodes.values(), key=lambda n: (n['type'], n['name'])), edges=sorted(edges, key=lambda e: (e['kind'], e['from'], e['to'], e['detail'])), dynamic_refs=sorted(dynamic_refs, key=lambda r: (r['object'], r['kind'], r['expression'])), observations=observations)


def to_mermaid(deps, inventory):
    lines, ids = ['flowchart LR'], {}
    def escape(text):
        return text.replace('"', '#quot;').replace('\n', ' ').replace('\r', ' ')
    for kind, prefix, opening, closing in [('cube', 'c', '[', ']'), ('process', 'p', '([', '])'), ('chore', 'h', '{{', '}}')]:
        for i, n in enumerate(sorted((n for n in deps['nodes'] if n['type'] == kind), key=lambda n: n['name'])):
            ids[n['id']] = ident = f'{prefix}{i}'
            lines.append(f'  {ident}{opening}"{escape(n["name"])}"{closing}')
    styles = {'rule_reads': '-- "DB()" -->', 'feeds': '-. "feeds" .->', 'ti_source': '-- "source" -->', 'ti_reads': '-- "reads" -->', 'ti_writes': '== "writes" ==>', 'ti_clears': '== "clears" ==>', 'calls': '-- "calls" -->', 'runs': '-- "runs" -->'}
    for edge in deps['edges']:
        if edge['kind'] == 'shares_dimension':
            label = edge['detail']
            if len(label) > 60:
                label = label[:59] + '…'
            style = f'--- |"{escape(label)}"|'
        else:
            style = styles[edge['kind']]
        lines.append(f'  {ids[edge["from"]]} {style} {ids[edge["to"]]}')
    lines.append('  classDef missing stroke-dasharray: 5 5')
    for n in deps['nodes']:
        if n.get('missing'):
            lines.append(f'  class {ids[n["id"]]} missing')
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inventory')
    parser.add_argument('--out-dir', required=True)
    args = parser.parse_args()
    with open(args.inventory, encoding='utf-8') as handle:
        inventory = json.load(handle)
    deps = build(inventory)
    directory = Path(args.out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'dependencies.json').write_text(json.dumps(deps, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (directory / 'architecture.mmd').write_text(to_mermaid(deps, inventory), encoding='utf-8')
    print(f"{len(deps['nodes'])} nodes, {len(deps['edges'])} edges, {len(deps['dynamic_refs'])} dynamic refs")
    for name, values in deps['observations'].items():
        print(f'{name}: {json.dumps(values, ensure_ascii=False)}')


if __name__ == '__main__':
    main()
