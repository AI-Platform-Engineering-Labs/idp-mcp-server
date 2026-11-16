variable "resource_group_name" {
  description = "The playground's pre-created resource group (KodeKloud names it kml_rg_main_...)."
  type        = string
}

variable "location" {
  description = "Azure region. Empty = use the resource group's region (safest in the playground)."
  type        = string
  default     = ""
}

variable "prefix" {
  description = "Name prefix for resources. A random suffix is added."
  type        = string
  default     = "idp"

  validation {
    condition     = can(regex("^[a-z0-9-]{2,15}$", var.prefix))
    error_message = "Use 2-15 lowercase letters, digits or hyphens."
  }
}

variable "kubernetes_version" {
  description = "AKS Kubernetes version. Empty = the region's default."
  type        = string
  default     = ""
}

variable "node_vm_size" {
  description = "Node size. The KodeKloud playground allows only Standard_D2s_v3 for AKS."
  type        = string
  default     = "Standard_D2s_v3"
}

variable "node_count" {
  description = "Number of nodes. The playground allows at most 2."
  type        = number
  default     = 2

  validation {
    condition     = var.node_count >= 1 && var.node_count <= 2
    error_message = "The KodeKloud playground allows 1 or 2 nodes."
  }
}

variable "os_disk_type" {
  description = "Ephemeral avoids a Premium managed disk (not allowed in the playground). Use Managed if Ephemeral is refused."
  type        = string
  default     = "Ephemeral"

  validation {
    condition     = contains(["Ephemeral", "Managed"], var.os_disk_type)
    error_message = "Use Ephemeral or Managed."
  }
}

variable "os_disk_size_gb" {
  description = "OS disk size. With Ephemeral it must fit the VM cache (50 GB on Standard_D2s_v3)."
  type        = number
  default     = 48
}
