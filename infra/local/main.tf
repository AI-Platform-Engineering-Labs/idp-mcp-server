# Local deployment: Terraform drives Docker on your laptop.
# Same workflow as the cloud (init / plan / apply / destroy) at zero cost,
# so you can rehearse the demo without a sandbox session.

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
  # Rebuild the image whenever the server code, catalog or Dockerfile changes.
  source_hash = sha1(join("", concat(
    [for f in sort(fileset(local.repo_root, "server/idp_mcp/**/*.py")) : filesha1("${local.repo_root}/${f}")],
    [for f in sort(fileset(local.repo_root, "server/catalog/*")) : filesha1("${local.repo_root}/${f}")],
    [filesha1("${local.repo_root}/server/requirements.txt"), filesha1("${local.repo_root}/Dockerfile")],
  )))
}

resource "docker_image" "server" {
  name = "idp-mcp-server:local"

  build {
    context = local.repo_root
  }

  triggers = {
    source_hash = local.source_hash
  }
  keep_locally = true
}

resource "docker_container" "server" {
  name    = var.container_name
  image   = docker_image.server.image_id
  restart = "unless-stopped"

  env = [
    "MCP_TRANSPORT=http",
    "PORT=8000",
  ]

  ports {
    internal = 8000
    external = var.host_port
    ip       = "127.0.0.1" # only reachable from your laptop
  }

  healthcheck {
    test     = ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"]
    interval = "15s"
    timeout  = "3s"
    retries  = 3
  }
}
