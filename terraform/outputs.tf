output "function_app_name" {
  description = "The name of the main Function App."
  value       = azurerm_linux_function_app.function_app.name
}

output "function_app_resource_group_name" {
  description = "The resource group of the function app."
  value       = azurerm_linux_function_app.function_app.resource_group_name
}

output "python_version" {
  description = "The Python version used for the Function App"
  value       = azurerm_linux_function_app.function_app.site_config[0].application_stack[0].python_version
}

output "stage_slot_name" {
  description = "The name of the app's staging deployment slot"
  value       = azurerm_linux_function_app_slot.staging_slot.name
}
