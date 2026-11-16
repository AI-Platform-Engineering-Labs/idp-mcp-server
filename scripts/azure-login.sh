#!/usr/bin/env bash
# Used by the deploy-azure workflow (not on your laptop).
# Logs in with the KodeKloud playground's service principal and works out the
# rest by itself, so for a new playground you only update three GitHub secrets:
#   ARM_CLIENT_ID, ARM_CLIENT_SECRET, ARM_TENANT_ID
# It finds:
#   * the subscription  (the one the service principal can see; or SUBSCRIPTION_OVERRIDE)
#   * the resource group (the playground's kml_rg_main_*; or RESOURCE_GROUP_OVERRIDE)
# and exports ARM_SUBSCRIPTION_ID and RESOURCE_GROUP for the next steps.
set -euo pipefail

missing=0
for v in ARM_CLIENT_ID ARM_CLIENT_SECRET ARM_TENANT_ID; do
  if [ -z "${!v:-}" ]; then
    echo "::error::Secret $v is empty. Settings > Secrets and variables > Actions > update it from the KodeKloud playground page."
    missing=1
  fi
done
[ "$missing" = 0 ] || exit 1

echo "::add-mask::$ARM_CLIENT_SECRET"
if ! az login --service-principal -u "$ARM_CLIENT_ID" -p "$ARM_CLIENT_SECRET" --tenant "$ARM_TENANT_ID" -o none 2>login.err; then
  cat login.err >&2
  echo "::error::Azure login failed. The playground has probably expired or the secrets are from an old one. Start a playground and update ARM_CLIENT_ID / ARM_CLIENT_SECRET / ARM_TENANT_ID."
  exit 1
fi
rm -f login.err

# Subscription: use the secret if set, otherwise the service principal's (it sees only one).
if [ -n "${SUBSCRIPTION_OVERRIDE:-}" ]; then
  az account set --subscription "$SUBSCRIPTION_OVERRIDE"
fi
SUB=$(az account show --query id -o tsv)

# Resource group: the variable if it exists in this subscription, else the playground's group.
RG=""
OVR="${RESOURCE_GROUP_OVERRIDE:-}"
if [ -n "$OVR" ] && az group show -n "$OVR" -o none 2>/dev/null; then
  RG="$OVR"
else
  if [ -n "$OVR" ]; then
    echo "::warning::Variable RESOURCE_GROUP=$OVR is not in this playground (old session?). Looking it up instead."
  fi
  RG=$(az group list --query "[?starts_with(name, 'kml_rg_main')].name | [0]" -o tsv)
  if [ -z "$RG" ]; then
    # Not a KodeKloud-style name: accept it only if there is exactly one group.
    mapfile -t ALL < <(az group list --query "[].name" -o tsv)
    if [ "${#ALL[@]}" = 1 ]; then RG="${ALL[0]}"; fi
  fi
fi
if [ -z "$RG" ]; then
  echo "::error::Could not find the playground resource group. Set the repository variable RESOURCE_GROUP."
  az group list --query "[].name" -o tsv >&2 || true
  exit 1
fi

LOCATION=$(az group show -n "$RG" --query location -o tsv)
echo "Subscription: $SUB"
echo "Resource group: $RG ($LOCATION)"
{
  echo "ARM_SUBSCRIPTION_ID=$SUB"
  echo "RESOURCE_GROUP=$RG"
} >> "$GITHUB_ENV"
{
  echo "### Azure playground"
  echo "- Resource group: \`$RG\` ($LOCATION)"
} >> "$GITHUB_STEP_SUMMARY"
