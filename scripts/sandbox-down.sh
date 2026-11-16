#!/usr/bin/env bash
# After a session: remove the (now expired) sandbox credentials from GitHub.
# KodeKloud deletes the Azure resources and the state storage account itself.
set -euo pipefail
REPO="${1:-AI-Platform-Engineering-Labs/idp-mcp-server}"
for v in ARM_CLIENT_ID ARM_CLIENT_SECRET ARM_TENANT_ID ARM_SUBSCRIPTION_ID; do
  gh secret delete "$v" -R "$REPO" || true
done
echo "Sandbox credentials removed from $REPO."
