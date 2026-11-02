> **Committed example** — provenance in [EXAMPLE.md](EXAMPLE.md). IDs and ARNs are fictional.

# Terraform: combined network + HCP `demo-classic-hcp`

- Module: [`terraform-redhat/rosa-hcp/rhcs`](https://registry.terraform.io/modules/terraform-redhat/rosa-hcp/rhcs/latest) `1.7.6`
- Region: **ap-southeast-2**

Single root: `module.network` (local `./network`) then `module.rosa_hcp`. One `terraform apply` after VPC is planned.

## Prerequisites

- [ROSA CLI](https://docs.openshift.com/rosa/) — `rosa login` (and OCM token for cluster stacks)
- AWS credentials with access to **`ap-southeast-2`** (read for plan; write for apply)
- [Terraform](https://developer.hashicorp.com/terraform) ≥ 1.5
- `` before cluster `plan`/`apply` (or use the generated **Makefile**)

## Apply

Single Terraform root (network module + HCP module). From this directory:

```bash
export AWS_DEFAULT_REGION=ap-southeast-2
terraform init && terraform plan && terraform apply
```

## Network stack (`network/`)

- Mode: **copy** — see [`network/README.md`](network/README.md) and `network/INVENTORY.md`.
- Adopt: imports in `network/imports.tf`. Copy: new VPC CIDR; no imports.
- ROSA HCP **control-plane VPCE** is never adopted in `network/`. Customer VPC endpoints only when generated.

## Related MOBB skills

- `/rosa:hcp-adopt`, `/rosa:classic-to-hcp`, `/rosa:classic-to-hcp-full`
- `plugins/rosa/terraform.md` in [mobb-skills](https://github.com/rh-mobb/mobb-skills)

