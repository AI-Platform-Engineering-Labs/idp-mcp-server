#!/usr/bin/env bash
# Optional shortcut for a new KodeKloud playground (needs only gh, from Git Bash).
# You can do the same by hand in GitHub: Settings > Secrets and variables > Actions.
#
#   export ARM_CLIENT_ID=... ARM_CLIENT_SECRET=... ARM_TENANT_ID=...
#   bash scripts/set-sandbox-secrets.sh
#
# The workflow finds the subscription and resource group itself.
set -euo pipefail
REPO="${1:-AI-Platform-Engineering-Labs/idp-mcp-server}"
for v in ARM_CLIENT_ID ARM_CLIENT_SECRET ARM_TENANT_ID; do
  printf '%s' "${!v:?$v is not set}" | gh secret set "$v" -R "$REPO"
done
# Clear overrides left over from an older playground, if any.
gh secret delete ARM_SUBSCRIPTION_ID -R "$REPO" 2>/dev/null || true
gh variable delete RESOURCE_GROUP -R "$REPO" 2>/dev/null || true
echo "Secrets set on $REPO. Deploy with:"
echo "  gh workflow run deploy-azure -R $REPO -f action=apply"
