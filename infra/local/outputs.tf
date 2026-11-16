output "mcp_url" {
  description = "Point your MCP client (VS Code, MCP Inspector) here."
  value       = "http://localhost:${var.host_port}/mcp"
}

output "health_url" {
  value = "http://localhost:${var.host_port}/healthz"
}
