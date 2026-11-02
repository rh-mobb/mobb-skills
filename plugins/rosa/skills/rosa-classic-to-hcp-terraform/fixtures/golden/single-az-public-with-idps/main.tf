module "rosa_hcp" {
  source  = "terraform-redhat/rosa-hcp/rhcs"
  version = "1.7.6"

  cluster_name      = var.cluster_name
  openshift_version = var.openshift_version
  channel           = var.channel

  aws_subnet_ids         = var.aws_subnet_ids
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

  machine_pools      = var.machine_pools
  identity_providers = merge(var.identity_providers, local.identity_providers_classic)
}
