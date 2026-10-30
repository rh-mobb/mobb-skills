---
description: Generate Terraform for a new ROSA HCP cluster from a running ROSA Classic cluster (terraform-redhat/rosa-hcp module and tfvars).
argument-hint: <classic-cluster-name-or-id> [output-directory]
---

## Name

rosa:classic-to-hcp

## Synopsis

```
/rosa:classic-to-hcp <classic-cluster> [output-dir]
```

## Description

Inspects a **ROSA Classic** cluster with the `rosa` CLI, runs the deterministic mapper in the `rosa-classic-to-hcp-terraform` skill, and writes a Terraform stack (pinned `terraform-redhat/rosa-hcp/rhcs` module, `terraform.tfvars`, and `MIGRATION.md`). Does not create a VPC, reuse Classic subnet IDs, or run `terraform apply`.

## Implementation

**The agent runs every step below** (rosa/ocm, Python generators, `terraform fmt`/`validate`). Do not tell the operator to run skill scripts unless they explicitly want offline copy-paste.

Follow the **rosa-classic-to-hcp-terraform** skill end to end:

1. Use the **rosa-cli** skill for profile / login.
2. Collect cluster, machine pool, ingress, and hosted-cp version JSON for `<classic-cluster>`.
3. When the operator may change VPC or cluster CIDRs, or is using `/rosa:classic-to-hcp-full`, run discovery and **summarize_classic_inventory.py** first (see **rosa-classic-network-terraform**).
4. Run `scripts/classic_to_hcp.py --dry-run` and present the summary together with the inventory briefing.
5. **Wait for answers**, then ask for target cluster name, infra pools (yes/no), CIDR reuse vs unique ranges, any change to private/public or AZ layout, and **customer VPC endpoints** when discovery lists them (same rules as **hcp-adopt**: ask before network write; **`--skip-endpoints`** if declined; never adopt ROSA HCP control-plane VPCE in `network/`).
6. Run the script with `--write`, then `terraform fmt` and `terraform validate` in `[output-dir]` (default `./<target-cluster-name>/`).

Set `OUTPUT_DIR` from the optional second argument when provided.

## Notes

- Refuses clusters where `hypershift.enabled` is true (already HCP).
- Operator must fill `vpc_cidr`, subnet IDs, and admin credentials in `terraform.tfvars` before apply — or run **rosa-classic-network-terraform** / `/rosa:classic-to-hcp-full` to generate and merge network values.
- For VPC-only Terraform generation, use **rosa-classic-network-terraform** (see `/rosa:classic-to-hcp-full` for combined workflow).
