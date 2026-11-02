module "network" {
  source = "./network"

  aws_region  = var.aws_region
  name_prefix = var.network_name_prefix
  vpc_cidr    = var.network_vpc_cidr
  common_tags = var.network_common_tags
}

locals {
  machine_pools_wired = {
    for k, v in var.machine_pools : k => merge(v, {
      subnet_id = try(v.subnet_id, "") != "" ? v.subnet_id : try(
        module.network.private_subnet_ids_by_az[
          var.aws_availability_zones[tonumber(regex("-([0-9]+)$", v.name)[0]) - 1]
        ],
        try(v.subnet_id, "")
      )
    })
  }
}

module "rosa_hcp" {
  source  = "terraform-redhat/rosa-hcp/rhcs"
  version = "1.7.6"

  depends_on = [module.network]

  cluster_name      = var.cluster_name
  openshift_version = var.openshift_version
  channel           = var.channel

  aws_subnet_ids         = module.network.aws_subnet_ids
  aws_availability_zones = var.aws_availability_zones

  private                          = var.private
  default_ingress_listening_method = var.default_ingress_listening_method

  machine_cidr = var.machine_cidr
  pod_cidr     = var.pod_cidr
  service_cidr = var.service_cidr
  host_prefix  = var.host_prefix

  replicas             = var.replicas
  compute_machine_type = var.compute_machine_type
  worker_disk_size     = var.worker_disk_size

  create_account_roles  = true
  account_role_prefix   = var.account_role_prefix
  create_oidc           = true
  managed_oidc          = true
  create_operator_roles = true
  operator_role_prefix  = var.operator_role_prefix

  admin_credentials_username = var.admin_credentials_username
  admin_credentials_password = var.admin_credentials_password

  machine_pools      = local.machine_pools_wired
  identity_providers = merge(var.identity_providers, local.identity_providers_classic)
}

output "network_vpc_id" {
  value = module.network.vpc_id
}

output "network_aws_subnet_ids" {
  value = module.network.aws_subnet_ids
}

output "hcp_cluster_id" {
  value = module.rosa_hcp.cluster_id
}
