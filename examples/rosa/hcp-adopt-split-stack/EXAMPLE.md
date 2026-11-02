# Example: HCP adopt (split stack)

| Field | Value |
|-------|--------|
| **Skills** | `rosa-hcp-adopt-terraform`, `rosa-classic-network-terraform` |
| **Command** | `/rosa:hcp-adopt` |
| **Workflow** | Live cluster JSON → `hcp_adopt_to_tf.py --write` + `network_to_tf.py --mode adopt --write` → `network/` + cluster root |
| **Scenario** | Public ROSA HCP cluster with BYO VPC (single-AZ); import blocks, Makefile, README |

Identifiers and ARNs are **fictional** (account `111111111111`). Do not apply against production without replacing values from your environment.

Discovery JSON under `_collect/` is omitted — regenerate locally with `discover_cluster_network.py`.

