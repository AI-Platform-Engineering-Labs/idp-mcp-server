#!/usr/bin/env bash
# Check a running MCP server (local or Azure) with plain curl, no MCP client needed.
# Usage: bash scripts/smoke-test.sh [mcp-base-url]   (default http://localhost:8000)
#   1. /healthz answers
#   2. read tools: list_services, get_service, get_service_status (through the Backstage
#      proxy), list_teams
#   3. knowledge base (search_docs, get_doc) and software templates (list_templates)
#   4. write tool: create_service only queues a request (pending_approval)
#   5. the human side: with ADMIN_TOKEN set, approve the request and see it become approved;
#      the admin endpoint refuses a call without the token
set -euo pipefail
BASE="${1:-http://localhost:8000}"

call() { # $1 = tool name, $2 = JSON arguments
  curl -fsS -X POST "$BASE/mcp" \
    -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"$1\",\"arguments\":$2}}"
}
expect() { # $1 = label, $2 = output, $3 = text it must contain
  # $3 is a regex; JSON inside the reply is escaped, so patterns allow any punctuation between words.
  if echo "$2" | grep -Eq "$3"; then echo "OK: $1"; else echo "FAIL: $1: $2" >&2; exit 1; fi
}

echo "== health"
curl -fsS "$BASE/healthz"; echo

echo "== list_services"
# Backstage answers requests a few seconds before its catalog has loaded, so retry for ~60 s.
OUT=""
for _ in $(seq 1 20); do
  OUT=$(call list_services '{}' || true)
  echo "$OUT" | grep -q 'payments-api' && break
  echo "  catalog not ready yet, retrying..."; sleep 3
done
expect "list_services returned the catalog" "$OUT" 'payments-api'

echo "== get_service orders-web"
OUT=$(call get_service '{"name":"orders-web"}')
expect "get_service shows the owner" "$OUT" 'team-storefront'
expect "get_service shows what it depends on" "$OUT" 'payments-api'

echo "== get_service_status orders-web (the platform checks it through Backstage)"
OUT=$(call get_service_status '{"name":"orders-web"}')
if echo "$OUT" | grep -q 'BACKSTAGE_URL is not set'; then
  echo "SKIP: server is not connected to Backstage"
else
  expect "orders-web is healthy" "$OUT" 'healthy[^a-z]+true'
fi

echo "== list_teams"
expect "list_teams shows team-payments" "$(call list_teams '{}')" 'team-payments'

echo "== knowledge base and templates"
expect "search_docs finds the deploy freeze policy" "$(call search_docs '{"query":"deploy freeze"}')" 'deploy-freeze-policy'
expect "get_doc reads an article" "$(call get_doc '{"slug":"deploy-freeze-policy"}')" 'Friday 15:00 IST'
expect "list_templates offers the golden paths" "$(call list_templates '{}')" 'python-service'

echo "== create_service (write: must only queue a request)"
NAME="smoke-$(date +%s)"
OUT=$(call create_service "{\"template\":\"python-service\",\"name\":\"$NAME\",\"owner\":\"team-platform\"}")
expect "create_service is pending approval" "$OUT" 'pending_approval'
REQ=$(echo "$OUT" | grep -o 'req-[0-9a-f]\{8\}' | head -1)
[ -n "$REQ" ] || { echo "FAIL: no request id in: $OUT" >&2; exit 1; }
expect "request is still pending" "$(call get_request_status "{\"request_id\":\"$REQ\"}")" 'pending_approval'

echo "== human approval ($REQ)"
CODE=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/admin/approvals/$REQ/approve")
case "$CODE" in
  401|404) echo "OK: approving without the admin token is refused ($CODE)" ;;
  *) echo "FAIL: approve without a token returned $CODE" >&2; exit 1 ;;
esac
if [ -n "${ADMIN_TOKEN:-}" ]; then
  curl -fsS -X POST -H "Authorization: Bearer $ADMIN_TOKEN" "$BASE/admin/approvals/$REQ/approve" >/dev/null
  expect "request approved by a human" "$(call get_request_status "{\"request_id\":\"$REQ\"}")" 'status[^a-z]+approved'
else
  echo "SKIP: set ADMIN_TOKEN to also test the approval step"
fi
