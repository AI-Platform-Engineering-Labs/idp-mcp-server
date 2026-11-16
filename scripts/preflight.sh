#!/usr/bin/env bash
# Read-only checks before a deploy (deploy-azure with action = preflight).
# Run AFTER scripts/azure-login.sh (needs az logged in, RESOURCE_GROUP, ARM_SUBSCRIPTION_ID).
# Changes nothing in Azure. Prints a report to the run summary.
#   FAIL = the apply will not work, fix it first.   WARN = worth knowing, apply may still work.
set -uo pipefail
: "${RESOURCE_GROUP:?}" "${IMAGE_TAG:=latest}"
VM_SIZE="${VM_SIZE:-Standard_D2s_v3}"
fails=0
report() { echo "$1"; echo "$1" >> "${GITHUB_STEP_SUMMARY:-/dev/null}"; }
ok()   { report "- ✅ $1"; }
warn() { report "- ⚠️ $1"; echo "::warning::$1"; }
fail() { report "- ❌ $1"; echo "::error::$1"; fails=$((fails + 1)); }

report "### Preflight"

# 1. Playground: subscription and resource group
SUB=$(az account show --query id -o tsv)
ok "Logged in. Subscription \`$SUB\`"
if LOC=$(az group show -n "$RESOURCE_GROUP" --query location -o tsv 2>/dev/null); then
  ok "Resource group \`$RESOURCE_GROUP\` exists in \`$LOC\`"
else
  fail "Resource group $RESOURCE_GROUP not found"; exit 1
fi

# 2. Is the VM size usable in this region (the playground allows only Standard_D2s_v3 for AKS)?
RESTR=$(az vm list-skus -l "$LOC" --size "$VM_SIZE" --resource-type virtualMachines \
  --query "[0].restrictions[].reasonCode" -o tsv 2>/dev/null || true)
COUNT=$(az vm list-skus -l "$LOC" --size "$VM_SIZE" --resource-type virtualMachines \
  --query "length(@)" -o tsv 2>/dev/null || echo 0)
if [ "${COUNT:-0}" = 0 ]; then
  warn "Could not confirm $VM_SIZE is offered in $LOC (the check may be blocked for this account)"
elif [ -n "$RESTR" ]; then
  fail "$VM_SIZE is restricted in $LOC: $RESTR"
else
  ok "VM size \`$VM_SIZE\` is available in \`$LOC\`"
fi

# 3. Anything already there from an earlier run in this playground?
CLUSTERS=$(az aks list -g "$RESOURCE_GROUP" --query "[].name" -o tsv 2>/dev/null || true)
if [ -n "$CLUSTERS" ]; then
  warn "AKS cluster(s) already in the resource group: $(echo "$CLUSTERS" | tr '\n' ' '). The playground allows few nodes; a second cluster may be refused. Run action = destroy first, or reuse it."
else
  ok "No AKS cluster in the resource group yet"
fi
SA=$(az storage account list -g "$RESOURCE_GROUP" --query "[?starts_with(name,'tfidp')].name | [0]" -o tsv 2>/dev/null || true)
if [ -n "$SA" ]; then ok "Terraform state storage account \`$SA\` already exists (state is reused)"; else ok "Terraform state storage account will be created on apply"; fi

# 4. Can AKS be listed/read with this identity at all?
if az aks get-versions -l "$LOC" -o none 2>/dev/null; then
  ok "AKS API is reachable (\`az aks get-versions\`)"
else
  warn "az aks get-versions failed (not fatal; the apply may still work)"
fi

# 5. Images
for img in idp-backstage idp-mcp-server; do
  TOKEN=$(curl -fsS "https://ghcr.io/token?scope=repository:ai-platform-engineering-labs/$img:pull" | jq -r .token 2>/dev/null)
  INDEX=$(curl -fsS -H "Authorization: Bearer $TOKEN" \
    -H "Accept: application/vnd.oci.image.index.v1+json,application/vnd.docker.distribution.manifest.list.v2+json" \
    "https://ghcr.io/v2/ai-platform-engineering-labs/$img/manifests/$IMAGE_TAG" 2>/dev/null || true)
  if [ -z "$INDEX" ]; then
    fail "Image $img:$IMAGE_TAG can't be pulled anonymously. Run the images workflow and make the package public."
  elif echo "$INDEX" | grep -q '"amd64"'; then
    ok "Image \`$img:$IMAGE_TAG\` is public and has linux/amd64 (what AKS runs)"
  else
    fail "Image $img:$IMAGE_TAG has no linux/amd64 variant"
  fi
done

if [ "$fails" -gt 0 ]; then report ""; report "**$fails blocking problem(s).** Fix them, then run apply."; exit 1; fi
report ""; report "**Ready.** Run the workflow again with action = apply."
