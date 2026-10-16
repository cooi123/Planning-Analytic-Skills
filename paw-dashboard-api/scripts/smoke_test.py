#!/usr/bin/env python3
"""Smoke-test the PAW book and dashboard APIs: build throwaway objects, read them
back, and clean them up.

    python3 -I smoke_test.py build   --config smoke_config.json
    python3 -I smoke_test.py cleanup --config smoke_config.json

Builds, in the database named in the config:
  1. an MDX view,
  2. a classic book with a grid widget,
  3. a dashboard with bar, line and column charts,
  4. a dashboard with two selectors and their synced grids.
It reports the HTTP status of each step and reads the dashboards back. It cannot
tell you whether the widgets RENDER; ask the user to open them in PAW.

Requirements
  * Python 3.10+ and `requests`.
  * The helper functions from the open-source builder. Clone
    github.com/filiplou/Planning-analytics-bob into its own directory, READ
    create_paw_demo.py, then pass that directory as "helpers_dir" in the config.
    This script imports it, so it runs that file's top-level code: only do so
    after you have read it.
  * The API key in the environment variable named by "key_env". It is never
    printed or accepted on the command line.

Writes to the tenant. Run it only on a database the user owns or named.
"""
import argparse, json, os, sys, urllib.parse

import requests
from requests.auth import HTTPBasicAuth


def load_config(path):
    cfg = json.load(open(path))
    for k in ("host", "tenant_id", "database", "cube", "page", "chart", "selectors", "grid",
              "helpers_dir", "key_env", "prefix"):
        if k not in cfg:
            sys.exit(f"config is missing '{k}'")
    key = os.environ.get(cfg["key_env"])
    if not key:
        sys.exit(f"environment variable {cfg['key_env']} is not set")
    return cfg, key


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["build", "cleanup"])
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg, key = load_config(args.config)

    host = cfg["host"].rstrip("/")
    api = f"{host}/api/{cfg['tenant_id']}/v0"
    tm1 = f"{api}/tm1/{urllib.parse.quote(cfg['database'])}/api/v1"
    viz = f"{host}/idvisualizations/r/v2"
    cube = cfg["cube"]
    pre = cfg["prefix"]
    names = {"view": f"{pre}View", "book": f"{pre}Book",
             "charts": f"{pre}Charts", "selectors": f"{pre}Selector"}
    state_path = cfg.get("state_file", "smoke_state.json")

    s = requests.Session()
    s.auth = HTTPBasicAuth("apikey", key)
    s.headers.update({"Accept": "application/json", "Content-Type": "application/json"})

    def viz_url(name):
        return f"{viz}/content{urllib.parse.quote('/shared/' + name, safe='/')}/"

    me = s.get(f"{api}/rolemgmt/v1/users/me", timeout=60)
    if me.status_code != 200:
        sys.exit(f"login failed: HTTP {me.status_code}. Check tenant, region and that the key is a PA API key.")
    print(f"authenticated as {me.json().get('displayName', '?')}; database {cfg['database']!r}")

    if args.command == "cleanup":
        for n in (names["charts"], names["selectors"]):
            print("dashboard", n, s.delete(viz_url(n), timeout=30).status_code)
        print("classic book", s.delete(f"{tm1}/Contents('Applications')/Contents('{names['book']}')",
                                       timeout=30).status_code)
        print("view", s.delete(f"{tm1}/Cubes('{cube}')/Views('{names['view']}')", timeout=30).status_code)
        return

    sys.path.insert(0, cfg["helpers_dir"])
    import create_paw_demo as m  # noqa: E402  (reads the builder's helpers)
    m.PA, m.T, m.DB, m.KEY = host, cfg["tenant_id"], cfg["database"], key
    m.TM1, m.VIZ = tm1, viz
    m.APPS = f"{tm1}/Contents('Applications')/Contents"

    def h(d): return f"[{d}].[{d}]"
    def mem(d, x): return f"[{d}].[{d}].[{x}]"
    page = cfg["page"]  # {dimension: member}; must cover every dimension of the cube

    def qs(rows, cols):
        return m.build_query_state(cube, h(rows), h(cols),
                                   [(h(d), mem(d, x)) for d, x in page.items() if d not in (rows, cols)])

    results = {}
    state = {"names": names, "viz": []}

    # 1) view
    g = cfg["grid"]  # {"rows": dim, "cols": dim, "rows_members": [...], "cols_members": [...]}
    where = ",".join(mem(d, x) for d, x in page.items() if d not in (g["rows"], g["cols"]))
    mdx = (f"SELECT {{{','.join(mem(g['cols'], x) for x in g['cols_members'])}}} ON 0, "
           f"{{{','.join(mem(g['rows'], x) for x in g['rows_members'])}}} ON 1 "
           f"FROM [{cube}] WHERE ({where})")
    s.delete(f"{tm1}/Cubes('{cube}')/Views('{names['view']}')", timeout=30)
    r = s.post(f"{tm1}/Cubes('{cube}')/Views",
               json={"@odata.type": "#ibm.tm1.api.v1.MDXView", "Name": names["view"], "MDX": mdx}, timeout=60)
    results["view"] = r.status_code

    # 2) classic book
    ok = m.create_or_replace_book(s, names["book"], [m._sheet("Sheet1", 0,
                                  [m._widget("Test grid", cube, names["view"])])])
    results["classic book"] = "ok" if ok else "FAIL"

    # 3) charts dashboard
    c = cfg["chart"]  # {"category_dim", "series_dim", "series_members": [...]}
    def values():
        return [m._di(mem(c["series_dim"], x), x) for x in c["series_members"]]
    cat = m._di(h(c["category_dim"]), f"{c['category_dim']}: Selection")
    charts = m._tab("Charts", [
        m._chart_widget("com.ibm.vis.rave2bundlebar", "Bar chart", cube, qs(c["category_dim"], c["series_dim"]),
                        cat, values(), "color", "2%", "0.5%", "49%", "46%"),
        m._chart_widget("com.ibm.vis.rave2line", "Line chart", cube, qs(c["category_dim"], c["series_dim"]),
                        cat, values(), "series", "2%", "50.5%", "49%", "46%"),
        m._chart_widget("com.ibm.vis.rave2bundlecolumn", "Column chart", cube, qs(c["category_dim"], c["series_dim"]),
                        cat, values(), "color", "52%", "0.5%", "49%", "46%"),
    ])

    # 4) selector dashboard
    rows = [{"cube": cube, "view": names["view"], "qs": qs(g["rows"], g["cols"]),
             "title": f"{g['rows']} x {g['cols']}", "sync_hierarchy": h(x["dimension"]),
             "root_member_id": f"[{x['root_member']}]"} for x in cfg["selectors"]]
    selectors = m._selector_tab("Selectors", rows)

    for key_name, tab in (("charts", charts), ("selectors", selectors)):
        name = names[key_name]
        url = viz_url(name)
        s.delete(url, timeout=30)
        r1 = s.put(url, json={"type": "dashboard", "name": name, "content": {}, "custom_properties": {}}, timeout=30)
        if r1.status_code not in (200, 201):
            results[f"{name} stub"] = r1.status_code
            continue
        state["viz"].append({"name": name, "id": r1.json().get("id")})
        r2 = s.put(url, json={"type": "dashboard", "content": m._content_envelope(name, [tab]),
                              "custom_properties": {}}, timeout=60)
        results[f"{name} content"] = r2.status_code
        back = s.get(url, timeout=30)
        results[f"{name} read back"] = back.status_code

    json.dump(state, open(state_path, "w"))
    print("\nRESULTS (HTTP status; 2xx means the server accepted it, not that it renders)")
    for k, v in results.items():
        print(f"  {k}: {v}")
    print("\nNow ask the user to open these in PAW and report anything blank or broken.")
    print(f"Clean up with: python3 -I smoke_test.py cleanup --config {args.config}")


if __name__ == "__main__":
    main()
