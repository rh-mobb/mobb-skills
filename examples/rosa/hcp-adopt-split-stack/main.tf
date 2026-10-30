module "rosa_hcp" {
  source  = "terraform-redhat/rosa-hcp/rhcs"
  version = "1.7.6"

  cluster_name      = var.cluster_name
  openshift_version = var.openshift_version
  channel = "stable-4.22"

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

  create_account_roles  = false
  account_role_prefix   = var.account_role_prefix

  create_oidc      = false
  oidc_config_id   = var.oidc_config_id

  create_operator_roles = false
  operator_role_prefix  = var.operator_role_prefix

  cluster_autoscaler_enabled = var.cluster_autoscaler_enabled
  autoscaler_max_nodes_total = var.autoscaler_max_nodes_total

  ec2_metadata_http_tokens = var.ec2_metadata_http_tokens
  aws_billing_account_id   = var.aws_billing_account_id
  properties                 = var.properties

  aws_additional_control_plane_security_group_ids = var.aws_additional_control_plane_security_group_ids

  # true so rhcs_hcp_default_ingress is in the module graph (required for ingress import).
  wait_for_create_complete            = true
  wait_for_std_compute_nodes_complete = false

  machine_pools = var.machine_pools
  identity_providers = {}
}
