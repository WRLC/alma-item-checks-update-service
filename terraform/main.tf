locals {
  service_name = "aic-update-service"
}
data "terraform_remote_state" "shared" {
  backend = "azurerm"
  config = {
    resource_group_name: var.tf_shared_resource_group_name
    storage_account_name: var.tf_shared_storage_account_name
    container_name: var.tf_shared_container_name
    key: var.tf_shared_key
  }
}

data "azurerm_resource_group" "existing" {
  name = data.terraform_remote_state.shared.outputs.resource_group_name
}

data "azurerm_storage_account" "existing" {
  name                     = data.terraform_remote_state.shared.outputs.storage_account_name
  resource_group_name      = data.terraform_remote_state.shared.outputs.resource_group_name
}

# Access storage resources from shared state
locals {
  storage_queues = data.terraform_remote_state.shared.outputs.storage_queues
  storage_containers = data.terraform_remote_state.shared.outputs.storage_containers
}

data "azurerm_service_plan" "existing" {
  name                = data.terraform_remote_state.shared.outputs.app_service_plan_name
  resource_group_name = data.terraform_remote_state.shared.outputs.app_service_plan_resource_group
}

data "azurerm_log_analytics_workspace" "existing" {
  name                = data.terraform_remote_state.shared.outputs.log_analytics_workspace_name
  resource_group_name = data.terraform_remote_state.shared.outputs.log_analytics_workspace_resource_group_name
}

resource "azurerm_application_insights" "main" {
  name                = local.service_name
  resource_group_name = data.azurerm_resource_group.existing.name
  location            = data.azurerm_resource_group.existing.location
  workspace_id        = data.azurerm_log_analytics_workspace.existing.id
  application_type    = "web"
}


resource "azurerm_linux_function_app" "function_app" {
  name                       = local.service_name
  resource_group_name        = data.azurerm_resource_group.existing.name
  location                   = data.azurerm_resource_group.existing.location
  service_plan_id            = data.azurerm_service_plan.existing.id
  storage_account_name       = data.azurerm_storage_account.existing.name
  storage_account_access_key = data.azurerm_storage_account.existing.primary_access_key

  site_config {
    always_on        = true
    application_insights_connection_string = azurerm_application_insights.main.connection_string
    application_insights_key = azurerm_application_insights.main.instrumentation_key
    application_stack {
      python_version = "3.12"
    }
  }


  app_settings = {
    "WEBSITE_RUN_FROM_PACKAGE" = "1"
    "INSTITUTION_API_ENDPOINT" = var.institution_api_endpoint
    "INSTITUTION_API_KEY"      = var.institution_api_key
    "UPDATE_QUEUE"             = local.storage_queues["update-queue"]
    "UPDATED_ITEMS_CONTAINER"  = local.storage_containers["updated-items-container"]
    "NOTIFICATION_QUEUE"       = local.storage_queues["update-queue"]
    "REPORT_CONTAINER"         = local.storage_containers["reports-container"]
  }

  sticky_settings {
    app_setting_names = [
      "INSTITUTION_API_ENDPOINT",
      "INSTITUTION_API_KEY",
      "UPDATE_QUEUE",
      "UPDATED_ITEMS_CONTAINER",
      "NOTIFICATION_QUEUE",
      "REPORT_CONTAINER"
    ]
  }
}

resource "azurerm_linux_function_app_slot" "staging_slot" {
  name                       = "stage"
  function_app_id            = azurerm_linux_function_app.function_app.id
  storage_account_name       = data.azurerm_storage_account.existing.name
  storage_account_access_key = data.azurerm_storage_account.existing.primary_access_key

  site_config {
    always_on        = true
    application_insights_connection_string = azurerm_application_insights.main.connection_string
    application_insights_key = azurerm_application_insights.main.instrumentation_key
    application_stack {
      python_version = "3.12"
    }
  }

  app_settings = {
    "WEBSITE_RUN_FROM_PACKAGE" = "1"
    "INSTITUTION_API_ENDPOINT" = var.institution_api_endpoint_stage
    "INSTITUTION_API_KEY"      = var.institution_api_key_stage
    "UPDATE_QUEUE"             = local.storage_queues["update-queue-stage"]
    "UPDATED_ITEMS_CONTAINER"  = local.storage_containers["updated-items-container-stage"]
    "NOTIFICATION_QUEUE"       = local.storage_queues["update-queue-stage"]
    "REPORT_CONTAINER"         = local.storage_containers["reports-container-stage"]
  }
}
