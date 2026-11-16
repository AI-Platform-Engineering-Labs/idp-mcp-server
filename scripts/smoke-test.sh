#!/usr/bin/env bash
# Check a running MCP server (local or Azure) with plain curl, no MCP client needed.
# Usage: bash scripts/smoke-test.sh [mcp-base-url]   (default http://localhost:8000)
#   1. /healthz answers
#   2. list_services returns the catalog (from Backstage when it is connected)
#   3. call_service reaches payments-api through the Backstage proxy
#      (skipped when the server runs without Backstage)
set -euo pipefail
BASE="${1:-http://localhost:8000}"

call() { # $1 = tool name, $2 = JSON arguments
  curl -fsS -X POST "$BASE/mcp" \
    -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"$1\",\"arguments\":$2}}"
}

echo "== health"
curl -fsS "$BASE/healthz"; echo

echo "== list_services"
OUT=$(call list_services '{}')
echo "$OUT" | grep -q 'payments-api' || { echo "FAIL: list_services: $OUT" >&2; exit 1; }
echo "OK: list_services returned the catalog"

echo "== call_service payments-api (through the IDP)"
OUT=$(call call_service '{"name":"payments-api"}')
if echo "$OUT" | grep -q 'BACKSTAGE_URL is not set'; then
  echo "SKIP: server is not connected to Backstage"
elif echo "$OUT" | grep -q 'healthy'; then
  echo "OK: payments-api answered through Backstage"
else
  echo "FAIL: call_service: $OUT" >&2; exit 1
fi
