variable "cluster_name" {
  type = string
}

variable "openshift_version" {
  type = string
}

variable "channel" {
  type = string
}

variable "vpc_cidr" {
  type        = string
  description = "Target VPC CIDR. machine_cidr must equal or be a subset of this CIDR."
  default     = ""
}

variable "aws_subnet_ids" {
  type        = list(string)
  description = "Private subnet per AZ (and public per AZ when private=false). Every subnet CIDR must fall inside machine_cidr."
  default     = []
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
  default = ""

  validation {
    condition = (
      var.vpc_cidr == "" || var.machine_cidr == "" ||
      can(cidrcontains(var.vpc_cidr, var.machine_cidr))
    )
    error_message = "machine_cidr must equal or be a subset of vpc_cidr when both are set."
  }
}

variable "pod_cidr" {
  type    = string
  default = ""
}

variable "service_cidr" {
  type = string
}

variable "host_prefix" {
  type    = number
  default = null
}

variable "replicas" {
  type = number
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

variable "operator_role_prefix" {
  type = string
}

variable "admin_credentials_username" {
  type    = string
  default = ""
}

variable "admin_credentials_password" {
  type      = string
  sensitive = true
  default   = ""
}

variable "machine_pools" {
  type    = any
  default = {}
}
