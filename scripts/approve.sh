#!/usr/bin/env bash
# The human side of the approval flow. An agent can only ask (create_service);
# you approve or deny here.
#
#   bash scripts/approve.sh list                 # pending requests
#   bash scripts/approve.sh approve req-1a2b3c4d
#   bash scripts/approve.sh deny    req-1a2b3c4d
#
# Local default: server http://localhost:8000, token local-admin-token (same as compose.yaml
# and infra/local). Against AKS: MCP_URL=http://<ip> ADMIN_TOKEN=$(kubectl -n idp get secret
# idp-tokens -o jsonpath='{.data.admin-token}' | base64 -d) bash scripts/approve.sh list
set -euo pipefail
BASE="${MCP_URL:-http://localhost:8000}"
TOKEN="${ADMIN_TOKEN:-local-admin-token}"
case "${1:-}" in
  list) curl -fsS -H "Authorization: Bearer $TOKEN" "$BASE/admin/approvals"; echo ;;
  approve | deny)
    [ -n "${2:-}" ] || { echo "Usage: $0 $1 <request-id>" >&2; exit 1; }
    curl -fsS -X POST -H "Authorization: Bearer $TOKEN" "$BASE/admin/approvals/$2/$1"; echo ;;
  *) echo "Usage: $0 list | approve <id> | deny <id>" >&2; exit 1 ;;
esac
