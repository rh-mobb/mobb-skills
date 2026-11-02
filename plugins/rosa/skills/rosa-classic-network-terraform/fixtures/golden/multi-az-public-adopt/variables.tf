variable "aws_region" {
  type        = string
  description = "AWS region for network resources."
}

variable "name_prefix" {
  type        = string
  description = "Prefix for Name tags on created resources (copy mode) or labels (adopt mode)."
}

variable "vpc_cidr" {
  type        = string
  description = "VPC CIDR block."
}

variable "common_tags" {
  type        = map(string)
  default     = {}
  description = "Tags applied to all resources."
}
