# rosa-hcp-adopt-terraform — Developer Reference

Clone the upstream module for import paths, variable names, and submodule layout:

```bash
git clone https://github.com/terraform-redhat/terraform-rhcs-rosa-hcp references/terraform-rhcs-rosa-hcp
```

The reference is gitignored. Do not commit it.

See **[references/rosa-hcp-module-adopt-mapping.md](../../references/rosa-hcp-module-adopt-mapping.md)** for which upstream modules map to adopt/discovery.

## Key paths

| Path | Use |
|------|-----|
| `main.tf` | Root module wiring (`create_* = false` adopt pattern) |
| `modules/rosa-cluster-hcp/` | `rhcs_cluster_rosa_hcp`, default ingress |
| `modules/machine-pool/` | `rhcs_hcp_machine_pool` |
| `modules/additional-cp-sg/` | Private cluster VPCE extra SG associations |
| `variables.tf` | STS ARNs, `oidc_config_id`, subnet inputs, `shared_vpc`, additional SG vars |

Module ↔ OCM/adopt matrix: **[references/rosa-hcp-module-adopt-mapping.md](references/rosa-hcp-module-adopt-mapping.md)**.

## Tests

```bash
bash plugins/rosa/skills/rosa-hcp-adopt-terraform/scripts/run_fixture_tests.sh
```

Update `fixtures/golden/demo-hcp-adopt` when intentional output changes.
