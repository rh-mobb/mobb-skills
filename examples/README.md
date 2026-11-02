# MOBB skills — example outputs

Committed **anonymized** Terraform stacks produced by MOBB ROSA plugin skills. They are documentation and review artifacts — not runnable against AWS/OCM without replacing IDs, ARNs, and credentials from your environment.

Regenerate or refresh from a local run:

```bash
python3 plugins/rosa/scripts/publish_example_stack.py --help
```

## ROSA Terraform (`examples/rosa/`)

| Directory | Command | Skills | Layout |
|-----------|---------|--------|--------|
| [`rosa/hcp-adopt-split-stack/`](rosa/hcp-adopt-split-stack/) | [`/rosa:hcp-adopt`](../plugins/rosa/commands/hcp-adopt.md) | `rosa-hcp-adopt-terraform`, `rosa-classic-network-terraform` | Cluster root + `network/` (split stack, adopt imports, Makefile) |
| [`rosa/classic-to-hcp-full-combined/`](rosa/classic-to-hcp-full-combined/) | [`/rosa:classic-to-hcp-full`](../plugins/rosa/commands/classic-to-hcp-full.md) | `rosa-classic-to-hcp-terraform`, `rosa-classic-network-terraform` | Single root: `module.network` + `module.rosa_hcp`, copy VPC under `network/` (one `terraform apply` at stack root) |

Each example includes **`EXAMPLE.md`** (provenance), **`README.md`** (operator runbook from the generator), and skill-specific notes (`ADOPT.md`, `MIGRATION.md`, `network/INVENTORY.md`).

**Anonymization:** fictional AWS account `111111111111`, cluster names `demo-*`, synthetic resource IDs. Live discovery JSON is not shipped for the HCP adopt example (`_collect/` omitted).

See also **[plugins/rosa/terraform.md](../plugins/rosa/terraform.md)** for the full command and skill map.
