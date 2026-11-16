# Cloud deployment: an AKS cluster in the KodeKloud Azure playground.
# Applied by GitHub Actions (.github/workflows/deploy-azure.yml), not from a laptop.
# What runs on the cluster (Backstage, the MCP server, the sample services) is in k8s/.
#
# Playground rules this code follows (kodekloud.com/cloud-playgrounds/azure):
#   * One resource group is pre-created and you can't create others,
#     so it is read with a data source instead of a resource.
#   * AKS: 1 node pool, max 2 nodes, VM size Standard_D2s_v3 only. Alerting must be off
#     (so no monitoring add-on).
#   * Premium disks are not allowed: nodes use an ephemeral OS disk (on the VM's local cache).
#   * No role assignments: so no ACR attach. Images come from public GHCR instead.
#   * The service principal can't register resource providers.
#   * Everything is wiped when the session ends: names get a random suffix.

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote state in a storage account inside the same resource group.
  # scripts/tf-backend.sh creates it and the workflow passes -backend-config.
  backend "azurerm" {}
}

provider "azurerm" {
  features {}
  resource_provider_registrations = "none"
}

data "azurerm_resource_group" "sandbox" {
  name = var.resource_group_name
}

resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

locals {
  location = var.location != "" ? var.location : data.azurerm_resource_group.sandbox.location
  tags = {
    project = "idp-mcp-server"
    purpose = "cncg-demo"
  }
}

resource "azurerm_kubernetes_cluster" "aks" {
  name                = "${var.prefix}-aks-${random_string.suffix.result}"
  resource_group_name = data.azurerm_resource_group.sandbox.name
  location            = local.location
  dns_prefix          = "${var.prefix}-${random_string.suffix.result}"
  kubernetes_version  = var.kubernetes_version != "" ? var.kubernetes_version : null
  sku_tier            = "Free"
  tags                = local.tags

  default_node_pool {
    name            = "system"
    vm_size         = var.node_vm_size
    node_count      = var.node_count
    os_disk_type    = var.os_disk_type
    os_disk_size_gb = var.os_disk_size_gb
  }

  # AKS manages its own identity; we never create a role assignment.
  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin      = "azure"
    network_plugin_mode = "overlay"
    network_data_plane  = "cilium"
    network_policy      = "cilium" # enforces k8s/network-policy.yaml (services reachable only from Backstage)
    load_balancer_sku   = "standard"
  }
}
