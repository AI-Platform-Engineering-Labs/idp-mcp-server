output "backstage_url" {
  description = "The IDP portal."
  value       = "http://localhost:${var.backstage_port}"
}

output "mcp_url" {
  description = "Point your MCP client (VS Code, Claude, MCP Inspector) here."
  value       = "http://localhost:${var.mcp_port}/mcp"
}
