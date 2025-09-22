variable "tf_shared_resource_group_name" {
  type = string
}

variable "tf_shared_storage_account_name" {
  type = string
}

variable "tf_shared_container_name" {
  type = string
}

variable "tf_shared_key" {
  type = string
}

variable "institution_api_endpoint" {
  type = string
}

variable "institution_api_key" {
  type = string
  sensitive = true
}

variable "institution_api_endpoint_stage" {
  type = string
}

variable "institution_api_key_stage" {
  type = string
  sensitive = true
}
