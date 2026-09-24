#!/usr/bin/env python3
"""Summarise an MCP reply read from stdin.

PA endpoints answer over SSE (`data: {...}` lines) rather than plain JSON, so the
payload has to be reassembled before parsing. Prints one short line for an
`initialize` reply, or a tool listing for `tools/list`.
"""
import json
import sys


def payload(raw: str) -> str:
    data = "".join(l[6:] for l in raw.splitlines() if l.startswith("data: "))
    return (data or raw).strip()


def main() -> None:
    body = payload(sys.stdin.read())
    if not body:
        print("(empty response)")
        return
    try:
        doc = json.loads(body)
    except json.JSONDecodeError:
        print("(not JSON — probably an HTML login page, so this is the web tier)")
        return

    if "error" in doc:
        print("JSON-RPC error:", str(doc["error"])[:120])
        return

    result = doc.get("result", {})
    if "serverInfo" in result:
        info = result["serverInfo"]
        print(f"{info.get('name', '?')} {info.get('version', '?')}")
    elif "tools" in result:
        tools = result["tools"]
        print(f"{len(tools)} tools")
        for tool in tools:
            desc = (tool.get("description") or "").split("\n")[0][:70]
            print(f"  - {tool.get('name')}  {desc}".rstrip())
    else:
        print("200, unrecognised payload")


if __name__ == "__main__":
    main()
