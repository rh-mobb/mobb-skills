# Classic → HCP Terraform field catalog

Implemented in `scripts/classic_to_hcp.py`. Update the script and golden fixtures when changing behavior.

## Cluster (`rosa describe cluster`)

| Classic JSON | HCP module input | Notes |
|--------------|------------------|--------|
| `hypershift.enabled == true` | — | Abort: already HCP |
| `region.id` | AWS provider region | |
| `version.raw_id` + `versions-hosted-cp` | `openshift_version`, `channel` | Same z-stream if listed; else newest same minor |
| `version.channel_group` | `channel` as `{group}-{minor}` | e.g. `stable-4.16` |
| `network.machine_cidr` | `machine_cidr` | Only with `--reuse-cidrs` |
| `network.pod_cidr` | `pod_cidr` | Only with `--reuse-cidrs` |
| `network.service_cidr` | `service_cidr` | Always copied |
| `network.host_prefix` | `host_prefix` | With `--reuse-cidrs` only |
| `multi_az` + worker pool AZs | `aws_availability_zones` | Drives worker-1..N fan-out |
| `aws.private_link` / default ingress | `private`, `default_ingress_listening_method` | |
| Worker pool | `replicas`, `compute_machine_type`, `worker_disk_size` | Default module pool only |
| — | `create_account_roles`, `create_oidc`, `create_operator_roles` | Always true; new HCP IAM |
| Target cluster name | `account_role_prefix`, `operator_role_prefix` | Shortened to fit 64-char IAM names |

## Machine pools (`rosa list machinepools`)

| Classic | HCP | Notes |
|---------|-----|--------|
| `worker` (or sole compute pool) | Module default pool | Multi-AZ → ROSA creates `worker-1`..`worker-N` |
| Other compute pools | `machine_pools` | Multi-AZ: one entry per AZ (`pool-1`..`pool-N`) |
| `infra` pool (optional) | `machine_pools` `infra-N` | Operator opt-in; infra taint/label |
| Autoscaling on default pool | `MIGRATION.md` | Module cluster autoscaler unavailable |
| Labels/taints/spot on default | `MIGRATION.md` | Not on module default pool |
| Per-pool disk on additional pools | `MIGRATION.md` | Not in module machine-pool API |

## CIDR validation (script)

| Check | When |
|-------|------|
| machine, pod, service present and non-overlapping | Always on Classic JSON |
| `--vpc-cidr` contains `machine_cidr` | Optional dry-run |
| `--unique-cidrs` | Empty machine/pod/host_prefix; Classic ranges in `MIGRATION.md` |

## Left empty for operator

| Variable | Reason |
|----------|--------|
| `vpc_cidr` | Target VPC not created by this skill |
| `aws_subnet_ids` | Cannot reuse Classic subnets |
| `machine_pools[].subnet_id` | One private subnet per AZ |
| `admin_credentials_*` | Sensitive |

## Unmapped → `MIGRATION.md`

FIPS, IDPs, Classic subnet/security group IDs, control-plane sizing, default-pool autoscaling/labels/taints, routing-unique CIDR guidance.
