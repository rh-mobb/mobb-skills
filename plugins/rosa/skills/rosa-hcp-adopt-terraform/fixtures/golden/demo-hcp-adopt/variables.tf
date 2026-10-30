variable "aws_region" {
  type = string
}

variable "cluster_name" {
  type = string
}

variable "openshift_version" {
  type = string
}

variable "channel" {
  type    = string
  default = null
}

variable "aws_subnet_ids" {
  type = list(string)
}

variable "aws_availability_zones" {
  type    = list(string)
  default = []
}

variable "private" {
  type = bool
}

variable "default_ingress_listening_method" {
  type = string
}

variable "machine_cidr" {
  type    = string
  default = null
}

variable "pod_cidr" {
  type    = string
  default = null
}

variable "service_cidr" {
  type    = string
  default = null
}

variable "host_prefix" {
  type    = number
  default = null
}

variable "replicas" {
  type    = number
  default = null
}

variable "compute_machine_type" {
  type = string
}

variable "worker_disk_size" {
  type    = number
  default = null
}

variable "account_role_prefix" {
  type = string
}

variable "oidc_config_id" {
  type = string
}

variable "operator_role_prefix" {
  type = string
}

variable "cluster_autoscaler_enabled" {
  type    = bool
  default = false
}

variable "autoscaler_max_nodes_total" {
  type    = number
  default = null
}

variable "ec2_metadata_http_tokens" {
  type    = string
  default = "optional"
}

variable "aws_billing_account_id" {
  type    = string
  default = null
}

variable "properties" {
  type    = map(string)
  default = {}
}

variable "aws_additional_control_plane_security_group_ids" {
  type        = list(string)
  default     = null
  description = "Private clusters only: extra SGs on ROSA HCP control-plane VPCE (additional-cp-sg module)."
}

variable "machine_pools" {
  type    = any
  default = {}
}
