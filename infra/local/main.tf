# Local deployment: the whole IDP demo on your laptop's Docker, driven by Terraform.
# Same init / plan / apply / destroy loop as the cloud, at zero cost.
#
#   Backstage portal  http://localhost:7007
#   MCP endpoint      http://localhost:8000/mcp
#   3 sample services on a private Docker network, no published ports:
#   only Backstage (and the MCP server through Backstage's proxy) can reach them.

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.6"
    }
  }
  # State stays in a local file (infra/local/terraform.tfstate, git-ignored).
}

provider "docker" {
  # Empty = provider default (unix socket on Linux/macOS).
  # On Windows with Docker Desktop set docker_host = "npipe:////./pipe/docker_engine".
  host = var.docker_host != "" ? var.docker_host : null
}

locals {
  repo_root = abspath("${path.module}/../..")

  images = {
    ghcr = {
      backstage = "ghcr.io/ai-platform-engineering-labs/idp-backstage:${var.image_tag}"
      mcp       = "ghcr.io/ai-platform-engineering-labs/idp-mcp-server:${var.image_tag}"
    }
    build = { backstage = "idp-backstage:local", mcp = "idp-mcp-server:local" }
    local = { backstage = "idp-backstage:local", mcp = "idp-mcp-server:local" }
  }[var.image_source]

  # Rebuild when sources change (image_source = "build").
  mcp_hash = sha1(join("", [for f in sort(concat(
    tolist(fileset(local.repo_root, "server/idp_mcp/**/*.py")),
    tolist(fileset(local.repo_root, "server/catalog/*")),
    ["server/requirements.txt", "Dockerfile"],
  )) : filesha1("${local.repo_root}/${f}")]))
  backstage_hash = sha1(join("", [for f in sort(concat(
    tolist(fileset(local.repo_root, "backstage/packages/**/src/**")),
    tolist(fileset(local.repo_root, "backstage/catalog/*")),
    tolist(fileset(local.repo_root, "backstage/app-config*.yaml")),
    ["backstage/yarn.lock", "backstage/Dockerfile"],
  )) : filesha1("${local.repo_root}/${f}")]))

  services = {
    payments-api         = "team-payments"
    orders-web           = "team-storefront"
    notifications-worker = "team-platform"
  }
}

resource "docker_network" "idp" {
  name = "idp"
}

# ---------- images

resource "docker_image" "backstage" {
  name         = local.images.backstage
  keep_locally = true

  dynamic "build" {
    for_each = var.image_source == "build" ? [1] : []
    content {
      context = "${local.repo_root}/backstage"
    }
  }
  triggers = var.image_source == "build" ? { source = local.backstage_hash } : {}
}

resource "docker_image" "mcp" {
  name         = local.images.mcp
  keep_locally = true

  dynamic "build" {
    for_each = var.image_source == "build" ? [1] : []
    content {
      context = local.repo_root
    }
  }
  triggers = var.image_source == "build" ? { source = local.mcp_hash } : {}
}

resource "docker_image" "echo" {
  name         = "hashicorp/http-echo:1.0"
  keep_locally = true
}

# ---------- the platform's services (private)

resource "docker_container" "service" {
  for_each = local.services

  name    = each.key
  image   = docker_image.echo.image_id
  restart = "unless-stopped"
  command = ["-listen=:5678", "-text=${jsonencode({ service = each.key, owner = each.value, status = "healthy" })}"]

  networks_advanced {
    name    = docker_network.idp.name
    aliases = [each.key]
  }
  # no ports block: not reachable from your laptop, only from the idp network
}

# ---------- Backstage (the IDP portal)

resource "docker_container" "backstage" {
  name    = "backstage"
  image   = docker_image.backstage.image_id
  restart = "unless-stopped"

  env = [
    "BACKSTAGE_BASE_URL=http://localhost:${var.backstage_port}",
    "MCP_BACKSTAGE_TOKEN=${var.mcp_backstage_token}",
  ]

  networks_advanced {
    name    = docker_network.idp.name
    aliases = ["backstage"]
  }

  ports {
    internal = 7007
    external = var.backstage_port
    ip       = "127.0.0.1"
  }

  healthcheck {
    test     = ["CMD", "node", "-e", "fetch('http://127.0.0.1:7007/.backstage/health/v1/readiness').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]
    interval = "10s"
    retries  = 30
  }

  depends_on = [docker_container.service]
}

# ---------- MCP server (the agent's way in)

resource "docker_container" "mcp" {
  name    = "idp-mcp-server"
  image   = docker_image.mcp.image_id
  restart = "unless-stopped"

  env = [
    "MCP_TRANSPORT=http",
    "PORT=8000",
    "BACKSTAGE_URL=http://backstage:7007",
    "BACKSTAGE_TOKEN=${var.mcp_backstage_token}",
  ]

  networks_advanced {
    name = docker_network.idp.name
  }

  ports {
    internal = 8000
    external = var.mcp_port
    ip       = "127.0.0.1"
  }

  healthcheck {
    test     = ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"]
    interval = "15s"
    timeout  = "3s"
    retries  = 3
  }
}
