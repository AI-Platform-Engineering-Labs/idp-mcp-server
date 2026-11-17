#!/usr/bin/env bash
# Optional shortcut for a new KodeKloud playground (needs only gh, from Git Bash/zsh).
# You can do the same by hand in GitHub: Settings > Secrets and variables > Actions.
#
#   export ARM_CLIENT_ID=... ARM_CLIENT_SECRET=... ARM_TENANT_ID=...
#   bash scripts/set-sandbox-secrets.sh
#
# Optional, only if your subscription / resource group are the same every time:
#   export ARM_SUBSCRIPTION_ID=...  RESOURCE_GROUP=kml_rg_main_...
# Otherwise leave them unset: the workflow finds them itself (see docs/runbook-aks.md).
# CLEAR_OVERRIDES=1 removes an old ARM_SUBSCRIPTION_ID / RESOURCE_GROUP instead.
set -euo pipefail
REPO="${1:-AI-Platform-Engineering-Labs/idp-mcp-server}"
for v in ARM_CLIENT_ID ARM_CLIENT_SECRET ARM_TENANT_ID; do
  val="${!v:-}"   # plain indirect expansion: works in macOS's bash 3.2 (${!v:?msg} does not)
  [ -n "$val" ] || { echo "ERROR: $v is not set. Run: export $v=..." >&2; exit 1; }
  printf '%s' "$val" | gh secret set "$v" -R "$REPO"
done
if [ "${CLEAR_OVERRIDES:-}" = 1 ]; then
  gh secret delete ARM_SUBSCRIPTION_ID -R "$REPO" 2>/dev/null || true
  gh variable delete RESOURCE_GROUP -R "$REPO" 2>/dev/null || true
else
  [ -z "${ARM_SUBSCRIPTION_ID:-}" ] || printf '%s' "$ARM_SUBSCRIPTION_ID" | gh secret set ARM_SUBSCRIPTION_ID -R "$REPO"
  [ -z "${RESOURCE_GROUP:-}" ] || gh variable set RESOURCE_GROUP -R "$REPO" -b "$RESOURCE_GROUP"
fi
echo "Done. Next: Actions > deploy-azure > Run workflow (preflight first, then apply), or:"
echo "  gh workflow run deploy-azure -R $REPO -f action=preflight"
