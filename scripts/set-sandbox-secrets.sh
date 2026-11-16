#!/usr/bin/env bash
# Run at the start of EVERY KodeKloud sandbox session, from Git Bash (needs only gh).
# 1. Start the Azure playground and copy its service principal details.
# 2. export ARM_CLIENT_ID=... ARM_CLIENT_SECRET=... ARM_TENANT_ID=... \
#           ARM_SUBSCRIPTION_ID=... RESOURCE_GROUP=kml_rg_main_...
# 3. bash scripts/set-sandbox-secrets.sh
set -euo pipefail
REPO="${1:-AI-Platform-Engineering-Labs/idp-mcp-server}"
for v in ARM_CLIENT_ID ARM_CLIENT_SECRET ARM_TENANT_ID ARM_SUBSCRIPTION_ID; do
  printf '%s' "${!v:?$v is not set}" | gh secret set "$v" -R "$REPO"
done
gh variable set RESOURCE_GROUP -R "$REPO" -b "${RESOURCE_GROUP:?RESOURCE_GROUP is not set}"
echo "Secrets set on $REPO. Deploy with:"
echo "  gh workflow run deploy-azure -R $REPO -f action=apply"
