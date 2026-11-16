# Cloud deployment: Azure App Service in the KodeKloud Azure Sandbox Playground.
# Applied by GitHub Actions (.github/workflows/deploy-azure.yml), not from a laptop.
#
# Sandbox rules this code follows:
#   * One resource group is pre-created for you and you can't create others,
#     so it is read with a data source instead of a resource.
#   * Only some SKUs are allowed; App Service plan B1 (or F1) works.
#   * The service principal can't register resource providers.
#   * Everything is wiped when the 2-hour session ends, so names get a random
#     suffix and nothing depends on resources from an earlier session.

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

resource "azurerm_service_plan" "plan" {
  name                = "${var.prefix}-plan-${random_string.suffix.result}"
  resource_group_name = data.azurerm_resource_group.sandbox.name
  location            = local.location
  os_type             = "Linux"
  sku_name            = var.sku
  tags                = local.tags
}

resource "azurerm_linux_web_app" "mcp" {
  name                = "${var.prefix}-${random_string.suffix.result}"
  resource_group_name = data.azurerm_resource_group.sandbox.name
  location            = local.location
  service_plan_id     = azurerm_service_plan.plan.id
  https_only          = true
  tags                = local.tags

  site_config {
    always_on                         = var.sku != "F1"
    ftps_state                        = "Disabled"
    http2_enabled                     = true
    minimum_tls_version               = "1.2"
    health_check_path                 = "/healthz"
    health_check_eviction_time_in_min = 2
    # Same entrypoint as the Docker image, HTTP transport on the port App Service expects.
    app_command_line = "python -m idp_mcp --transport http --port 8000"

    application_stack {
      python_version = "3.12"
    }
  }

  app_settings = {
    SCM_DO_BUILD_DURING_DEPLOYMENT = "true" # App Service runs pip install -r requirements.txt
    WEBSITES_PORT                  = "8000"
    MCP_TRANSPORT                  = "http"
    # Added in later roadmap steps (as App Service settings, never in code):
    #   GITHUB_TOKEN    - fine-grained, least-privilege token for the GitHub API tools
    #   MCP_API_KEY     - bearer token clients must send
  }

  logs {
    detailed_error_messages = true
    failed_request_tracing  = true
    http_logs {
      file_system {
        retention_in_days = 3
        retention_in_mb   = 35
      }
    }
  }
}
