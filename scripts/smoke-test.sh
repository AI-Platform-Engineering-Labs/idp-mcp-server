#!/usr/bin/env bash
# Check a running server (local or Azure) with plain curl, no MCP client needed.
# Usage: bash scripts/smoke-test.sh [base-url]   (default http://localhost:8000)
set -euo pipefail
BASE="${1:-http://localhost:8000}"
echo "== health"; curl -fsS "$BASE/healthz"; echo
echo "== tools/call list_services"
curl -fsS -X POST "$BASE/mcp" \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_services","arguments":{}}}' \
  | grep -q 'payments-api' && echo "OK: list_services returned the catalog"
