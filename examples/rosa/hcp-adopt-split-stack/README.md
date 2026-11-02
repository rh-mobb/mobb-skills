> **Committed example** — provenance in [EXAMPLE.md](EXAMPLE.md). IDs and ARNs are fictional.

# Terraform adopt: `demo-hcp-public` (ROSA HCP)

- OCM cluster ID: `01234567-89ab-cdef-0123-456789abcd01`
- Module: [`terraform-redhat/rosa-hcp/rhcs`](https://registry.terraform.io/modules/terraform-redhat/rosa-hcp/rhcs/latest) `1.7.6`
- Region: **ap-southeast-2**

Import an **existing** ROSA HCP cluster into Terraform (`create_* = false` on IAM/OIDC/operator roles).

## Prerequisites

- [ROSA CLI](https://docs.openshift.com/rosa/) — `rosa login` (and OCM token for cluster stacks)
- AWS credentials with access to **`ap-southeast-2`** (read for plan; write for apply)
- [Terraform](https://developer.hashicorp.com/terraform) ≥ 1.5
- `` before cluster `plan`/`apply` (or use the generated **Makefile**)

## Makefile shortcuts

From this directory (stack root):

```bash
make help
make init
make plan
make apply   # review plan first; adopt binds import state
```

Split stack order: **`make apply`** runs **network → cluster**; **`make destroy`** runs **cluster → network**.

| Target | Purpose |
|--------|---------|
| `make network-plan` / `make network-apply` | VPC/subnets only (`network/`) |
| `make cluster-plan` / `make cluster-apply` | ROSA HCP module (this root) |

## Manual Terraform (cluster root)

```bash
export AWS_DEFAULT_REGION=<region>
terraform init
terraform fmt
terraform validate
terraform plan
terraform apply
```

Run **`network/`** init/plan/apply first when adopting both stacks (see `network/README.md`).

## Network stack (`network/`)

- Mode: **adopt** — see [`network/README.md`](network/README.md) and `network/INVENTORY.md`.
- Adopt: imports in `network/imports.tf`. Copy: new VPC CIDR; no imports.
- ROSA HCP **control-plane VPCE** is never adopted in `network/`. Customer VPC endpoints only when generated.

## Adopt notes

1. Review `imports.tf` — adjust import IDs if the provider rejects them.
2. Expect plan drift on read-only API fields (`state`, URLs).
3. Node pool import IDs use `{cluster_id},{pool_name}`.
4. Do not commit `RHCS_TOKEN` or production admin passwords.

## Generator notes

- Adopt mode: IAM/OIDC/operator roles are **not** created by Terraform (`create_* = false`).
- Run `terraform plan` after import; expect drift on read-only API fields (state, URLs).
- OCM reserved property keys `rosa_tf_version` / `rosa_tf_commit` are omitted from tfvars (provider-managed).
- Import IDs for node pools use `{cluster_id},{pool_name}` — verify against RHCS provider docs.
- Node pool autoscaling is active — `cluster_autoscaler_enabled` is false (HCP scales via node pools).

## Related MOBB skills

- `/rosa:hcp-adopt`, `/rosa:classic-to-hcp`, `/rosa:classic-to-hcp-full`
- `plugins/rosa/terraform.md` in [mobb-skills](https://github.com/rh-mobb/mobb-skills)

