output "function_app_name" {
  description = "The name of the main Function App."
  value       = azurerm_linux_function_app.function_app.name
}

output "function_app_resource_group_name" {
  description = "The resource group of the function app."
  value       = azurerm_linux_function_app.function_app.resource_group_name
}
