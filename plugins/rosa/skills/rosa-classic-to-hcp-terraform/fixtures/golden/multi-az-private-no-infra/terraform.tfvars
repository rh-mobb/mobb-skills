# Generated from Classic cluster demo-multi (01234567-89ab-cdef-0123-456789abcdef)
# Fill empty values before terraform apply.

vpc_cidr = "" # Target VPC CIDR; machine_cidr must equal or be a subset.

aws_subnet_ids = [] # One private subnet per AZ in order worker-1..N

aws_availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]

cluster_name      = "demo-multi-hcp"
openshift_version = "4.16.20"
channel           = "stable-4.16"

private                          = true
default_ingress_listening_method = "internal"

machine_cidr = "10.0.0.0/16"
pod_cidr     = "10.128.0.0/14"
service_cidr = "172.30.0.0/16"
host_prefix  = 23

replicas             = 6
compute_machine_type = "m5.xlarge"
worker_disk_size     = 300

account_role_prefix  = "demo"
operator_role_prefix = "demo"

admin_credentials_username = "admin"
admin_credentials_password = "REPLACE-ME-14chars-min" # RHCS min 14 chars; set before production apply

machine_pools = {
  gpu_1 = {
    name              = "gpu-1"
    subnet_id         = "" # private subnet AZ us-east-1a (worker-1)
    openshift_version = "4.16.20"
    auto_repair       = true
    labels            = { "gpu" = "true" }
    autoscaling = {
      enabled      = true
      min_replicas = 1
      max_replicas = 3
    }
    aws_node_pool = {
      instance_type = "g4dn.xlarge"
      tags          = {}
    }
  }
  gpu_2 = {
    name              = "gpu-2"
    subnet_id         = "" # private subnet AZ us-east-1b (worker-2)
    openshift_version = "4.16.20"
    auto_repair       = true
    labels            = { "gpu" = "true" }
    autoscaling = {
      enabled      = true
      min_replicas = 1
      max_replicas = 3
    }
    aws_node_pool = {
      instance_type = "g4dn.xlarge"
      tags          = {}
    }
  }
  gpu_3 = {
    name              = "gpu-3"
    subnet_id         = "" # private subnet AZ us-east-1c (worker-3)
    openshift_version = "4.16.20"
    auto_repair       = true
    labels            = { "gpu" = "true" }
    autoscaling = {
      enabled      = true
      min_replicas = 1
      max_replicas = 3
    }
    aws_node_pool = {
      instance_type = "g4dn.xlarge"
      tags          = {}
    }
  }
}

identity_providers = {}
