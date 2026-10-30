# Full stack: copy VPC + HCP `demo-classic-hcp`

Regenerated from Classic **`demo-classic`** on **2026-10-29**.

## Layout

| Path | Role |
|------|------|
| `network/` | Copy-mode VPC **10.1.0.0/16** (Classic stays on **10.0.0.0/16**) |
| `main.tf` | `module.network` → `module.rosa_hcp` (single apply) |
| `json/` | ROSA inputs used for this run |

## Choices (same as prior live test)

- **Target:** `demo-classic-hcp` (IAM prefix `rosa`)
- **OpenShift:** `4.22.20` (`stable-4.22`)
- **Network:** public multi-AZ, copy VPC, machine CIDR **10.1.0.0/16** (`--unique-cidrs`), pod/service from Classic mapping
- **Pools:** 3× workers (`m5.xlarge`) + synthesized **infra-1..3** (`r5.xlarge`)
- **IdPs:** htpasswd **`developer`** (fixture users) + commented OAuth/GitHub stubs in `identity_providers_optional.tf` (see `classic-idps-inventory.json`)

## Apply (operator)

```bash
cd tmp/demo-classic-hcp
terraform plan
# terraform apply
```

Admin credentials are in `terraform.tfvars` (default generated password — change before production).

See **`MIGRATION.md`** for translations, Classic subnet IDs not to reuse, and IdP notes.
