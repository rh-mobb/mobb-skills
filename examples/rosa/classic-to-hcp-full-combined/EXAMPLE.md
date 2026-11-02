# Example: Classic → HCP (combined stack)

| Field | Value |
|-------|--------|
| **Skills** | `rosa-classic-to-hcp-terraform`, `rosa-classic-network-terraform` |
| **Command** | `/rosa:classic-to-hcp-full` |
| **Workflow** | Classic JSON + network discover → `classic_to_hcp.py --write` + `network_to_tf.py --mode copy` + `combine_stack.py` |
| **Scenario** | New VPC (`network/` copy) + greenfield HCP module in one root (`module.network` → `module.rosa_hcp`) |

Identifiers are **fictional**. Review `terraform.tfvars` (admin password, CIDRs) before any apply.

Supporting JSON in `json/` is anonymized fixture-style inventory, not live exports.

