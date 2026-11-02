# Import existing HCP cluster into terraform-redhat/rosa-hcp/rhcs module graph.
# Apply imports before or during first `terraform apply` (Terraform 1.5+).

import {
  to = module.rosa_hcp.module.rosa_cluster_hcp.rhcs_cluster_rosa_hcp.rosa_hcp_cluster
  id = "01234567-89ab-cdef-0123-456789abcd01"
}

import {
  to = module.rosa_hcp.module.rosa_cluster_hcp.rhcs_hcp_default_ingress.default_ingress[0]
  id = "01234567-89ab-cdef-0123-456789abcd01"
}

import {
  to = module.rosa_hcp.module.rhcs_hcp_machine_pool["workers"].rhcs_hcp_machine_pool.machine_pool
  id = "01234567-89ab-cdef-0123-456789abcd01,workers"
}
