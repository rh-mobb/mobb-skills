# Terraform: Classic → HCP `demo-idp-hcp`

- Source Classic cluster: `demo-single` (`fedcba98-7654-3210-fedc-ba9876543210`)
- Module: [`terraform-redhat/rosa-hcp/rhcs`](https://registry.terraform.io/modules/terraform-redhat/rosa-hcp/rhcs/latest) `1.7.6`
- Region: **us-west-2**
- IAM prefix: `demo` (new HCP roles on apply)

Creates a **new** HCP cluster. Fill subnet IDs in `terraform.tfvars` or generate **`network/`** and merge wiring.

## Prerequisites

- [ROSA CLI](https://docs.openshift.com/rosa/) — `rosa login` (and OCM token for cluster stacks)
- AWS credentials with access to **`us-west-2`** (read for plan; write for apply)
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

Cluster-only stack (no `network/` yet). After adding `network/`, re-run network generation to refresh this README and Makefile.

## Manual Terraform (cluster root)

```bash
export AWS_DEFAULT_REGION=<region>
terraform init
terraform fmt
terraform validate
terraform plan
terraform apply
```

## Migration notes

See **`MIGRATION.md`** for translations, IdPs, and unmapped fields.

Review **`terraform.tfvars`**: admin password, CIDRs, `aws_subnet_ids`, machine pools.

## Generator notes

- IAM prefix shortened from 'demo-idp-hcp' to 'demo' for 64-char role name limit.
- Default pool: single AZ us-west-2a, 2 replica(s).
- Additional pool memory -> AZ us-west-2a (single private subnet).

## Manual follow-up

- Classic subnet IDs (do not reuse): subnet-aaa
- Classic control plane / infra node counts: {"master": 1, "compute": 2} — HCP has no customer control plane.

## Identity providers (Classic → HCP)

### `developer` (htpasswd)
- Replicated **2** htpasswd user(s) with **new** random passwords (Classic passwords are not exported from OCM).
### `corp-oidc` (openid)
- Generated commented Terraform stub in `identity_providers_optional.tf`. Register a **new** OAuth/OIDC client for the HCP cluster callback URL before enabling.
### `github-org` (github)
- Generated commented Terraform stub in `identity_providers_optional.tf`. Register a **new** OAuth/OIDC client for the HCP cluster callback URL before enabling.

## Related MOBB skills

- `/rosa:hcp-adopt`, `/rosa:classic-to-hcp`, `/rosa:classic-to-hcp-full`
- `plugins/rosa/terraform.md` in [mobb-skills](https://github.com/rh-mobb/mobb-skills)

