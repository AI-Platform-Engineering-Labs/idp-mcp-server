output "cluster_name" {
  value = azurerm_kubernetes_cluster.aks.name
}

output "resource_group_name" {
  value = data.azurerm_resource_group.sandbox.name
}

output "node_resource_group" {
  description = "Resource group AKS creates for the nodes, load balancer and public IPs."
  value       = azurerm_kubernetes_cluster.aks.node_resource_group
}
