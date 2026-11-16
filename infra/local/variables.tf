variable "docker_host" {
  description = "Docker daemon address. Leave empty on Linux/macOS; on Windows use npipe:////./pipe/docker_engine."
  type        = string
  default     = ""
}

variable "host_port" {
  description = "Port on your laptop for the MCP server."
  type        = number
  default     = 8000
}

variable "container_name" {
  description = "Name of the local container."
  type        = string
  default     = "idp-mcp-server"
}
