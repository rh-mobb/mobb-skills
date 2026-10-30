# Terraform: Classic → HCP `demo-multi-hcp`

- Source Classic cluster: `demo-multi` (`01234567-89ab-cdef-0123-456789abcdef`)
- Module: [`terraform-redhat/rosa-hcp/rhcs`](https://registry.terraform.io/modules/terraform-redhat/rosa-hcp/rhcs/latest) `1.7.6`
- Region: **us-east-1**
- IAM prefix: `demo` (new HCP roles on apply)

Creates a **new** HCP cluster. Fill subnet IDs in `terraform.tfvars` or generate **`network/`** and merge wiring.

## Prerequisites

- [ROSA CLI](https://docs.openshift.com/rosa/) — `rosa login` (and OCM token for cluster stacks)
- AWS credentials with access to **`us-east-1`** (read for plan; write for apply)
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

- IAM prefix shortened from 'demo-multi-hcp' to 'demo' for 64-char role name limit.
- Default pool will materialize as worker-1 .. worker-3 with 2 replica(s) each (total 6).
- Additional pool gpu-1 -> AZ us-east-1a (private subnet for worker-1).
- Additional pool gpu-2 -> AZ us-east-1b (private subnet for worker-2).
- Additional pool gpu-3 -> AZ us-east-1c (private subnet for worker-3).
- Pool gpu autoscaling on Classic — verify HCP pool autoscaling limits after apply.
- Synthesized infra machine pools from Classic nodes.infra (no infra MachinePool in ROSA API).

## Manual follow-up

- Classic subnet IDs (do not reuse): subnet-private-a, subnet-private-b, subnet-private-c
- Classic control plane / infra node counts: {"master": 3, "infra": 3, "compute": 6} — HCP has no customer control plane.

## Related MOBB skills

- `/rosa:hcp-adopt`, `/rosa:classic-to-hcp`, `/rosa:classic-to-hcp-full`
- `plugins/rosa/terraform.md` in [mobb-skills](https://github.com/rh-mobb/mobb-skills)

