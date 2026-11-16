output "webapp_name" {
  value = azurerm_linux_web_app.mcp.name
}

output "webapp_url" {
  value = "https://${azurerm_linux_web_app.mcp.default_hostname}"
}

output "mcp_url" {
  description = "Point your MCP client here."
  value       = "https://${azurerm_linux_web_app.mcp.default_hostname}/mcp"
}
