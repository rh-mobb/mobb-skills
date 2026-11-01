# Adopt stack for existing HCP cluster demo-hcp-public (01234567-89ab-cdef-0123-456789abcd01)
# Module: terraform-redhat/rosa-hcp/rhcs (same as create path; imports bind live resources)

aws_region        = "ap-southeast-2"
cluster_name      = "demo-hcp-public"
openshift_version = "4.22.15"
channel           = "stable-4.22"

aws_subnet_ids         = ["subnet-0aaa1111private2a", "subnet-0bbb2222public2a"]
aws_availability_zones = ["ap-southeast-2a"]

private                          = false
default_ingress_listening_method = "external"

machine_cidr = "10.2.0.0/16"
pod_cidr     = "10.128.0.0/14"
service_cidr = "172.30.0.0/16"
host_prefix  = 23

replicas             = null
compute_machine_type = "m5.xlarge"
worker_disk_size     = 300

account_role_prefix  = "demo-hcp-public"
oidc_config_id       = "0demooidc000000000000000000000000"
operator_role_prefix = "demo-hcp-public"

# Live installer ARN (for verification): arn:aws:iam::111111111111:role/demo-hcp-public-HCP-ROSA-Installer-Role

cluster_autoscaler_enabled = false
autoscaler_max_nodes_total = null

ec2_metadata_http_tokens = "required"
aws_billing_account_id   = "111111111111"
properties = {
  "rosa_creator_arn" = "arn:aws:iam::111111111111:user/demo-operator"
}

aws_additional_control_plane_security_group_ids = null

machine_pools = {
  workers = {
    name              = "workers"
    subnet_id         = "subnet-0aaa1111private2a"
    openshift_version = "4.22.15"
    auto_repair       = true
    autoscaling = {
      enabled      = true
      min_replicas = 2
      max_replicas = 4
    }
    aws_node_pool = {
      instance_type = "m5.xlarge"
      tags = {
        "Act"                                   = "3"
        "ClusterName"                           = "demo-hcp-public"
        "ManagedBy"                             = "Terraform"
        "Project"                               = "demo-workshop"
        "api.openshift.com/environment"         = "production"
        "api.openshift.com/id"                  = "01234567-89ab-cdef-0123-456789abcd01"
        "api.openshift.com/legal-entity-id"     = "00000000000000000000000000000000"
        "api.openshift.com/name"                = "demo-hcp-public"
        "api.openshift.com/nodepool-hypershift" = "demo-hcp-public-workers"
        "api.openshift.com/nodepool-ocm"        = "workers"
        "red-hat-clustertype"                   = "rosa"
        "red-hat-managed"                       = "true"
      }
      root_volume = { size = 300 }
    }
  }
}
