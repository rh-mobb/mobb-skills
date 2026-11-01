# Generated from Classic cluster demo-single (fedcba98-7654-3210-fedc-ba9876543210)
# Fill empty values before terraform apply.

vpc_cidr = "" # Target VPC CIDR; machine_cidr must equal or be a subset.

aws_subnet_ids = [] # Private subnet for us-west-2a; add public subnet per AZ when private=false

aws_availability_zones = ["us-west-2a"]

cluster_name      = "demo-single-hcp"
openshift_version = "4.15.40"
channel           = "stable-4.15"

private                          = false
default_ingress_listening_method = "external"

machine_cidr = "10.10.0.0/16"
pod_cidr     = "10.132.0.0/14"
service_cidr = "172.31.0.0/16"
host_prefix  = 23

replicas             = 2
compute_machine_type = "m5.large"
worker_disk_size     = 300

account_role_prefix  = "demo"
operator_role_prefix = "demo"

admin_credentials_username = "admin"
admin_credentials_password = "REPLACE-ME-14chars-min" # RHCS min 14 chars; set before production apply

machine_pools = {
  memory = {
    name              = "memory"
    subnet_id         = "" # private subnet AZ us-west-2a
    openshift_version = "4.15.40"
    auto_repair       = true
    replicas          = 2
    labels            = { "workload" = "memory" }
    aws_node_pool = {
      instance_type = "r5.2xlarge"
      tags          = {}
    }
  }
}

identity_providers = {}
