# rosa-classic-to-hcp-terraform — Developer Reference

For major mapper updates (new Classic fields, module variable changes), clone the Terraform module reference:

```bash
git clone https://github.com/terraform-redhat/terraform-rhcs-rosa-hcp references/rosa-hcp
```

The reference is gitignored. Do not commit it.

## Key paths

| Path | Use |
|------|-----|
| `variables.tf` | Root module inputs |
| `modules/machine-pool/` | Additional pool shape |
| `modules/account-iam-resources/` | HCP account role naming |
| `modules/operator-roles/` | Operator role naming (64-char limit) |

## Tests

```bash
cd plugins/rosa/skills/rosa-classic-to-hcp-terraform
bash scripts/run_fixture_tests.sh
```

Update `fixtures/golden/*` when intentional output changes.
