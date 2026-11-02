
aws_region          = "ap-southeast-2"
network_name_prefix = "demo-classic-hcp-net"
network_vpc_cidr    = "10.1.0.0/16"
network_common_tags = {
  Project = "demo-workshop"
}

# Generated from Classic cluster demo-classic (01234567-89ab-cdef-0123-456789abcdef)
# Fill empty values before terraform apply.

vpc_cidr = "" # optional; combined stack uses network_vpc_cidr + module.network

aws_subnet_ids = [] # wired from module.network in main.tf

aws_availability_zones = ["ap-southeast-2a", "ap-southeast-2b", "ap-southeast-2c"]

cluster_name      = "demo-classic-hcp"
openshift_version = "4.22.20"
channel           = "stable-4.22"

private                          = false
default_ingress_listening_method = "external"

machine_cidr = "10.1.0.0/16"
pod_cidr     = ""
service_cidr = "172.30.0.0/16"
host_prefix  = null

replicas             = 3
compute_machine_type = "m5.xlarge"
worker_disk_size     = null

account_role_prefix  = "rosa"
operator_role_prefix = "rosa"

admin_credentials_username = "admin"
admin_credentials_password = "" # set before apply — RHCS requires at least 14 characters

machine_pools = {
  infra_1 = {
    name              = "infra-1"
    subnet_id         = "" # private subnet AZ ap-southeast-2a (worker-1)
    openshift_version = "4.22.20"
    auto_repair       = true
    replicas          = 1
    labels            = { "node-role.kubernetes.io/infra" = "" }
    taints = [
      { key = "node-role.kubernetes.io/infra", value = "reserved", schedule_type = "NoSchedule" },
    ]
    aws_node_pool = {
      instance_type = "r5.xlarge"
      tags          = {}
    }
  }
  infra_2 = {
    name              = "infra-2"
    subnet_id         = "" # private subnet AZ ap-southeast-2b (worker-2)
    openshift_version = "4.22.20"
    auto_repair       = true
    replicas          = 1
    labels            = { "node-role.kubernetes.io/infra" = "" }
    taints = [
      { key = "node-role.kubernetes.io/infra", value = "reserved", schedule_type = "NoSchedule" },
    ]
    aws_node_pool = {
      instance_type = "r5.xlarge"
      tags          = {}
    }
  }
  infra_3 = {
    name              = "infra-3"
    subnet_id         = "" # private subnet AZ ap-southeast-2c (worker-3)
    openshift_version = "4.22.20"
    auto_repair       = true
    replicas          = 1
    labels            = { "node-role.kubernetes.io/infra" = "" }
    taints = [
      { key = "node-role.kubernetes.io/infra", value = "reserved", schedule_type = "NoSchedule" },
    ]
    aws_node_pool = {
      instance_type = "r5.xlarge"
      tags          = {}
    }
  }
}

identity_providers = {}
