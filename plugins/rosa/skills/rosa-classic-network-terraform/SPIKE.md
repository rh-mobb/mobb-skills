# VPC reverse-engineering spike (rosa-mta-classic)

**Cluster:** `rosa-mta-classic` — `ap-southeast-2`, public multi-AZ, VPC `10.0.0.0/16`, six subnets (3 private + 3 public), three NAT gateways, one IGW, six cluster-scoped security groups, no VPC endpoints or TGW attachments in this account.

**Date:** 2026-10-28 (live discovery via `discover_cluster_network.py`).

## Tools evaluated

| Tool | Result | Verdict |
|------|--------|---------|
| **Terraformer** | Not run | **Rejected** — project archived/deprecated; not a sustainable dependency. |
| **Former2** | Not automated in CI | **Supplement only** — browser/export workflow; incomplete Terraform coverage for IAM; useful for one-off human exports, not MOBB skill default. |
| **aws2tf** | Not installed in dev environment | **Optional bootstrap** — could import by resource ID, but output requires heavy normalization; add as documented escape hatch, not core path. |
| **Opinionated generator** (`discover_cluster_network.py` + `network_to_tf.py`) | Live inventory + HCL + import blocks | **Selected** — ROSA-aware subnet ordering, adopt/copy modes, merges into HCP tfvars, fixture-testable. |

## Spike measurements (live)

- Discovery: 6 subnets, 3 NAT, 1 IGW, 6 SGs, 0 endpoints, 0 TGW, 0 flow logs.
- ROSA HCP `aws_subnet_ids` order: private subnets sorted by AZ, then public subnets (matches `terraform-redhat/rosa-hcp` public-cluster examples).
- Adopt mode: import blocks generated for VPC, IGW, subnets; NAT/EIP/route-table zero-drift import left as follow-up (documented in `INVENTORY.md`).
- Copy mode: new `name_prefix` (`*-hcp`) and reprovisioned `/20` subnets inside operator-chosen VPC CIDR.

## Decision

Ship **deterministic discovery + template Terraform** as the skill default. Document Former2/aws2tf in `SKILL.md` for operators who want a broader resource sweep before manual refactor.

## Known gaps (v1)

- Route tables and associations: **included** for per-subnet public/private tables (see `references/mapping.md`; aligned with [terraform-rosa-networking/route.tf](https://github.com/rh-mobb/terraform-rosa/blob/main/modules/terraform-rosa-networking/route.tf)).
- VPC endpoints, TGW attachments, flow logs: discovered; Terraform emission is partial (inventory + manual follow-up).
- Classic IAM roles are out of scope; HCP account roles remain module-managed.
- Adopt mode copies live tags from AWS; use `var.common_tags` only for optional extras (avoid overwriting ROSA tags in apply).
- NAT EIPs are imported via `eip_allocation_id` from `describe_nat_gateways`; empty EIP tags in AWS may still show tag drift if NAT tags differ from EIP.
