# rosa-classic-network-terraform — Developer Reference

For VPC module layout and `aws_subnet_ids` ordering, clone the Terraform module reference:

```bash
git clone https://github.com/terraform-redhat/terraform-rhcs-rosa-hcp references/terraform-rhcs-rosa-hcp
```

The reference is gitignored. Do not commit it.

## Key paths

| Path | Use |
|------|-----|
| `modules/vpc/` | Greenfield VPC patterns; compare with `network_to_tf.py` |
| `modules/shared-vpc-resources/` | Shared VPC account (not single-account adopt) |
| `modules/additional-cp-sg/` | Private cluster extra SGs on control-plane VPCE |
| `examples/rosa-hcp-public/main.tf` | `concat(public, private)` subnet list for public clusters |

## Tests

```bash
cd plugins/rosa/skills/rosa-classic-network-terraform
bash scripts/run_network_fixture_tests.sh
```

Update `fixtures/golden/*` when intentional output changes.

See **[references/rosa-hcp-module-adopt-mapping.md](../../references/rosa-hcp-module-adopt-mapping.md)**.
