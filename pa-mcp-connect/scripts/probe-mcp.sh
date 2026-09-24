#!/usr/bin/env bash
# Probe IBM Planning Analytics agentic-AI MCP endpoints.
#
# Runs the MCP `initialize` handshake against candidate paths and reports which
# answer, with server name and version. Read-only: `initialize` and `tools/list`
# change nothing on the server.
#
# Usage:
#   probe-mcp.sh --host <base-url> [--tenant <id>] [auth] [--tools]
#   probe-mcp.sh --url  <full-mcp-url> [auth] [--tools]
#   probe-mcp.sh --host <base-url> [auth] --control   # is the server discriminating?
#
# Auth (pick one):
#   --basic user:pass | --basic-b64 <base64> | --bearer <token> | --no-auth
#
# Examples:
#   probe-mcp.sh --host http://paw.example.com:26929 --basic 'pm:secret' --tools
#   probe-mcp.sh --host https://eu.planninganalytics.saas.ibm.com \
#                --tenant ABCD1234 --bearer "$PA_TOKEN"
#   probe-mcp.sh --host http://paw.example.com:29889 --basic 'pm:secret' --control

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARSE="$HERE/parse_mcp.py"

HOST=""; URL=""; TENANT=""; AUTH_HEADER=""; SHOW_TOOLS=0; CONTROL=0; TIMEOUT=30

die() { printf 'error: %s\n' "$1" >&2; exit 2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --host)      HOST="${2:-}"; shift 2 ;;
    --url)       URL="${2:-}"; shift 2 ;;
    --tenant)    TENANT="${2:-}"; shift 2 ;;
    --basic)     AUTH_HEADER="Authorization: Basic $(printf '%s' "${2:-}" | base64)"; shift 2 ;;
    --basic-b64) AUTH_HEADER="Authorization: Basic ${2:-}"; shift 2 ;;
    --bearer)    AUTH_HEADER="Authorization: Bearer ${2:-}"; shift 2 ;;
    --no-auth)   AUTH_HEADER=""; shift ;;
    --tools)     SHOW_TOOLS=1; shift ;;
    --control)   CONTROL=1; shift ;;
    --timeout)   TIMEOUT="${2:-30}"; shift 2 ;;
    -h|--help)   sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)           die "unknown argument: $1" ;;
  esac
done

[ -n "$HOST$URL" ] || die "need --host or --url (see --help)"
[ -f "$PARSE" ]    || die "missing helper: $PARSE"
HOST="${HOST%/}"

INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe-mcp","version":"1"}}}'
LIST='{"jsonrpc":"2.0","id":2,"method":"tools/list"}'

BODY=""   # set by post()
CODE=""

post() {  # post <url> <json-body>
  local tmp; tmp="$(mktemp)"
  CODE="$(curl -s --max-time "$TIMEOUT" -o "$tmp" -w '%{http_code}' \
    ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -X POST -d "$2" "$1" 2>/dev/null)"
  BODY="$(cat "$tmp")"
  rm -f "$tmp"
}

probe_one() {  # probe_one <url> <label>
  post "$1" "$INIT"
  printf '  %-56s %s' "$2" "${CODE:-000}"
  case "$CODE" in
    200)
      printf '  -> %s\n' "$(printf '%s' "$BODY" | python3 "$PARSE")"
      if [ "$SHOW_TOOLS" -eq 1 ]; then
        post "$1" "$LIST"
        printf '%s' "$BODY" | python3 "$PARSE" | sed 's/^/      /'
      fi ;;
    401)    printf '  (credential missing or invalid)\n' ;;
    403)    printf '  (authenticated, not entitled — add-on or user rights)\n' ;;
    404)    printf '  (path not found — auth OK, wrong endpoint or version)\n' ;;
    500)    if [ "$CONTROL" -eq 1 ]; then printf '  (server error)\n'; else printf '  (server error — rerun with --control before blaming credentials)\n'; fi ;;
    000|"") printf '  (no response — wrong port, or service down)\n' ;;
    *)      printf '\n' ;;
  esac
}

if [ "$CONTROL" -eq 1 ]; then
  [ -n "$HOST" ] || die "--control needs --host"
  cat <<TXT
Control test on $HOST

A healthy server discriminates: wrong credentials give 401, a fake path gives 404.
Identical codes across the first three mean it is evaluating neither, so the fault
is server-side and the credentials cannot be judged either way.

TXT
  real="$HOST/api/v0/agentic-ai/cube/mcp"
  fake="$HOST/api/v0/totally/made/up/path"
  saved="$AUTH_HEADER"
  probe_one "$real" "real creds, real path"
  AUTH_HEADER="Authorization: Basic $(printf 'bogus:bogus' | base64)"
  probe_one "$real" "WRONG creds, real path"
  AUTH_HEADER="$saved"
  probe_one "$fake" "real creds, FAKE path"
  AUTH_HEADER=""
  probe_one "$real" "no auth at all"
  AUTH_HEADER="$saved"
  echo
  echo "First three identical => auth tier is down. Credentials remain UNVERIFIED."
  exit 0
fi

if [ -n "$URL" ]; then
  echo "Probing single URL"
  probe_one "$URL" "$(printf '%s' "$URL" | sed 's|^https\{0,1\}://[^/]*||')"
  exit 0
fi

echo "Probing $HOST${TENANT:+  (tenant: $TENANT)}"
echo
echo "2.1.22 / 3.1.9 and later — unified endpoint:"
probe_one "$HOST/api/v0/agentic-ai/ibm-pa-tools/mcp" "/api/v0/agentic-ai/ibm-pa-tools/mcp"
[ -n "$TENANT" ] && probe_one "$HOST/api/$TENANT/v0/agentic-ai/ibm-pa-tools/mcp" "/api/$TENANT/v0/.../ibm-pa-tools/mcp"
echo
echo "Before 2.1.22 / 3.1.9 — discrete endpoints:"
for p in cube analysis; do
  probe_one "$HOST/api/v0/agentic-ai/$p/mcp" "/api/v0/agentic-ai/$p/mcp"
  [ -n "$TENANT" ] && probe_one "$HOST/api/$TENANT/v0/agentic-ai/$p/mcp" "/api/$TENANT/v0/.../$p/mcp"
done
echo
echo "Any 200 is usable. All 404 => check the PA Agent add-on is installed."
echo "All 500 => rerun with --control. All 000 => wrong port."
