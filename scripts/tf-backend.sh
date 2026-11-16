#!/usr/bin/env bash
# Run by the deploy workflow (not on your laptop).
# Makes sure the Terraform state storage account exists in the sandbox resource
# group, then exports its details for `terraform init -backend-config=...`.
# Safe to run every time. Needs: az logged in, RESOURCE_GROUP set.
set -euo pipefail
: "${RESOURCE_GROUP:?RESOURCE_GROUP is not set}"
SUB=$(az account show --query id -o tsv)
# Storage account names are global, 3-24 lowercase chars: derive a stable one per sandbox.
SA="tfidp$(printf '%s' "$SUB$RESOURCE_GROUP" | sha1sum | cut -c1-14)"
if ! az storage account show -n "$SA" -g "$RESOURCE_GROUP" -o none 2>/dev/null; then
  echo "Creating Terraform state storage account $SA"
  az storage account create -n "$SA" -g "$RESOURCE_GROUP" --sku Standard_LRS --kind StorageV2 \
    --min-tls-version TLS1_2 --allow-blob-public-access false -o none
fi
KEY=$(az storage account keys list -n "$SA" -g "$RESOURCE_GROUP" --query "[0].value" -o tsv)
az storage container create -n tfstate --account-name "$SA" --account-key "$KEY" -o none
echo "::add-mask::$KEY"
{
  echo "ARM_ACCESS_KEY=$KEY"
  echo "TF_BACKEND_SA=$SA"
} >> "$GITHUB_ENV"
