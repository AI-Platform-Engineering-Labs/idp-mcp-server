variable "resource_group_name" {
  description = "The sandbox's pre-created resource group (KodeKloud names it kml_rg_main_...)."
  type        = string
}

variable "location" {
  description = "Azure region. Empty = use the resource group's region (safest in the sandbox)."
  type        = string
  default     = ""
}

variable "prefix" {
  description = "Name prefix for resources. The web app name must be globally unique, so a random suffix is added."
  type        = string
  default     = "idpmcp"

  validation {
    condition     = can(regex("^[a-z0-9-]{3,20}$", var.prefix))
    error_message = "Use 3-20 lowercase letters, digits or hyphens."
  }
}

variable "sku" {
  description = "App Service plan SKU. The KodeKloud sandbox allows B1 or F1."
  type        = string
  default     = "B1"

  validation {
    condition     = contains(["B1", "F1"], var.sku)
    error_message = "The KodeKloud sandbox allows only B1 or F1."
  }
}
