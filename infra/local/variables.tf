variable "docker_host" {
  description = "Docker daemon address. Leave empty to use DOCKER_HOST or the default socket. Windows: npipe:////./pipe/docker_engine. macOS: unix:///Users/<you>/.docker/run/docker.sock. Never use the Windows value on macOS/Linux."
  type        = string
  default     = ""
}

variable "image_source" {
  description = <<-EOT
    Where the Backstage and MCP server images come from:
      ghcr  = pull the published images (fast; built by the images workflow on every merge)
      build = build them from this checkout (Backstage takes ~10-15 minutes the first time)
      local = use idp-backstage:local / idp-mcp-server:local already on this machine
  EOT
  type        = string
  default     = "ghcr"

  validation {
    condition     = contains(["ghcr", "build", "local"], var.image_source)
    error_message = "Use ghcr, build or local."
  }
}

variable "image_tag" {
  description = "Tag to pull when image_source = ghcr."
  type        = string
  default     = "latest"
}

variable "backstage_port" {
  description = "Port on your laptop for Backstage."
  type        = number
  default     = 7007
}

variable "mcp_port" {
  description = "Port on your laptop for the MCP server."
  type        = number
  default     = 8000
}

variable "mcp_backstage_token" {
  description = "Token the MCP server uses to call Backstage (catalog + proxy only). Local demo default, same as compose.yaml."
  type        = string
  default     = "local-dev-token-change-me"
  sensitive   = true
}

variable "admin_token" {
  description = "Token a human uses to approve or deny the agent's write requests (scripts/approve.sh). Local demo default."
  type        = string
  default     = "local-admin-token"
  sensitive   = true
}
