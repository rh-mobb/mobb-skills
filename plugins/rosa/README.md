# rosa

ROSA cost estimation and optimization plugin for the MOBB team.

Supports ROSA Classic and ROSA HCP cost calculation for individual clusters and fleets. Terraform generation for Classic→HCP and HCP adopt uses the official [`terraform-redhat/rosa-hcp/rhcs`](https://github.com/terraform-redhat/terraform-rhcs-rosa-hcp) module — see **[terraform.md](terraform.md)** for commands, **[examples/](../../examples/rosa/)** for anonymized sample output, and **[references/rosa-hcp-module-adopt-mapping.md](references/rosa-hcp-module-adopt-mapping.md)** for upstream module ↔ adopt coverage.

## Commands

| Command | Purpose |
|---|---|
| `/rosa:classic-to-hcp` | Generate HCP Terraform (rosa-hcp module + tfvars) from a Classic cluster |
| `/rosa:classic-to-hcp-full` | Network discover/adopt or copy + HCP stack + merged tfvars |
| `/rosa:hcp-adopt` | Adopt an **existing** HCP cluster (+ optional VPC adopt) with import blocks |
| `/rosa:cost` | Guided wizard — collects data conversationally, produces full analysis |
| `/rosa:cost-estimate` | Calculate monthly/annual costs for a fleet |
| `/rosa:cost-compare` | Classic vs HCP side-by-side with savings delta |
| `/rosa:cost-optimize` | Ranked savings opportunities with estimated impact |
| `/rosa:cost-report` | Full strategic advisory report for Classic→HCP migration |

## Input Modes

All commands accept three input modes:

- **Live**: OCM cluster IDs — requires active `ocm login`
- **Detailed**: Machine pool spec (cluster name, instance type, replica count per pool)
- **Estimate**: Cluster count + total vCPU budget

## Quick Start

```
/rosa:cost
```

For a fleet with known cluster IDs:
```
/rosa:cost-estimate cluster-id-1 cluster-id-2 cluster-id-3
```

For a quick estimate with 5 clusters at 240 total vCPUs:
```
/rosa:cost-estimate 5 clusters, 240 vCPUs total, 1yr contract
```

## Pricing Reference

Rates sourced from https://aws.amazon.com/rosa/pricing/ (us-east-1, current as of 2026-06).
Always verify current rates before quoting to customers.
