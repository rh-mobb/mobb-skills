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

Follow the **rosa-classic-to-hcp-terraform** skill end to end:

1. Use the **rosa-cli** skill for profile / login.
2. Collect cluster, machine pool, ingress, and hosted-cp version JSON for `<classic-cluster>`.
3. Run `scripts/classic_to_hcp.py --dry-run` and present the summary.
4. Ask the operator for target cluster name, infra pools (yes/no), and CIDR reuse vs unique ranges.
5. Run the script with `--write`, then `terraform fmt` and `terraform validate` in `[output-dir]` (default `./<target-cluster-name>/`).

Set `OUTPUT_DIR` from the optional second argument when provided.

## Notes

- Refuses clusters where `hypershift.enabled` is true (already HCP).
- Operator must fill `vpc_cidr`, subnet IDs, and admin credentials in `terraform.tfvars` before apply.
- For VPC-only Terraform generation, use a separate workflow (out of scope for this command).
