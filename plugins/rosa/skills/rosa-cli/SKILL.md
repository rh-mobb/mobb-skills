---
name: rosa-cli
description: |
  Command reference, lifecycle sequences, and Classic/HCP behavioral differences for the ROSA CLI.

  Use when:
  - Creating, managing, or deleting ROSA Classic or HCP clusters
  - Setting up STS roles, OIDC configs, and operator roles
  - Working with node pools, IDPs, ingress, or autoscaler
  - Scheduling or monitoring cluster upgrades
  - Troubleshooting ROSA CLI commands

  Covers all rosa subcommands with exact flags and Classic/HCP parallel sections.
  NOT for: ROSA cost estimation (use rosa-cost skill).
license: Apache-2.0
user_invocable: false
model: inherit
color: "#cc0000"
allowed-tools: []
---

# ROSA CLI Reference

Cite https://docs.openshift.com/rosa/rosa_cli/rosa-cli-about.html when presenting CLI guidance. Commands in this skill are current as of ROSA CLI v1.2 — run `rosa version` and compare against https://github.com/openshift/rosa/releases to verify currency before advising customers.

## Section 1: Authentication & Config

### `rosa login`

```bash
rosa login [flags]
```

Authenticates the CLI against OCM. Writes credentials to `$OCM_CONFIG` (default: `~/.config/ocm/ocm.json`).

**Key flags:**

| Flag | Purpose |
|---|---|
| `--token <string>` | OCM offline token (from console.redhat.com/openshift/token) |
| `--token-url <string>` | Override SSO token URL (default: sso.redhat.com) |
| `--client-id <string>` | OAuth2 client ID (for service account auth) |
| `--client-secret <string>` | OAuth2 client secret |
| `--use-auth-code` | Authenticate via browser OAuth2 flow |
| `--insecure` | Skip TLS certificate verification |
| `--env <string>` | Override API environment (`production`, `staging`, `integration`) |

**Multiple profiles:** Use `OCM_CONFIG` env var to point at different config files.

```bash
OCM_CONFIG="$HOME/.config/ocm/ocm-customer.json" rosa login --token <token>
OCM_CONFIG="$HOME/.config/ocm/ocm-customer.json" rosa whoami
```

### `rosa logout`

```bash
rosa logout
```

Removes credentials from the active OCM config file. Does not delete the config file itself.

### `rosa token`

```bash
rosa token
```

Prints the current access token. Useful for scripting or passing to other tools.

### `rosa whoami`

```bash
rosa whoami
```

Prints the authenticated user, organization, and account details from the active OCM profile.

### `rosa config`

```bash
rosa config get <key>
rosa config set <key> <value>
rosa config delete <key>
```

Reads and writes individual keys in the active OCM config file. Useful for scripting and non-interactive flows.

---

## Section 2: Classic Cluster Lifecycle

### Overview

Classic ROSA uses STS (Security Token Service) for AWS permissions. The Day 0 sequence must be followed in order — each step creates prerequisites for the next.

```
account-roles → oidc-config → operator-roles → create cluster → oidc-provider → (logs) → ready
```

Day 2 operations (node pools, IDPs, ingress, upgrades) are independent and can run in any order after the cluster is ready.

### Day 0: Create Account Roles

```bash
rosa create account-roles \
  --mode auto \
  --prefix ManagedOpenShift \
  --version 4.16 \
  --yes
```

Creates the IAM roles that allow ROSA to manage AWS resources on behalf of the cluster. Must be done once per AWS account per OCP version family (4.14, 4.16, etc.). Roles are shared across all clusters in the account.

**Key flags:**

| Flag | Purpose |
|---|---|
| `--mode auto\|manual` | `auto`: creates roles immediately; `manual`: prints shell commands |
| `--prefix <string>` | IAM role name prefix (default: `ManagedOpenShift`) |
| `--version <string>` | OCP version (e.g., `4.16`) — determines policy ARNs |
| `--path <string>` | IAM path for roles (optional, for org policy compliance) |
| `--permissions-boundary <arn>` | IAM permissions boundary ARN |
| `--yes` | Skip confirmation prompt |

### Day 0: Create OIDC Config

```bash
# Managed OIDC config (Red Hat manages rotation)
rosa create oidc-config \
  --mode auto \
  --managed \
  --yes

# Unmanaged (customer controls the OIDC keys)
rosa create oidc-config \
  --mode auto \
  --yes
```

Creates the OIDC configuration that lets Kubernetes service accounts assume AWS IAM roles. On Classic, create one OIDC config per cluster. Note the OIDC config ID from the output — it is needed for operator-roles and cluster creation.

**Key flags:**

| Flag | Purpose |
|---|---|
| `--managed` | Red Hat manages OIDC key rotation |
| `--installer-role-arn <arn>` | Required for unmanaged config |
| `--prefix <string>` | Prefix for the S3 bucket name (unmanaged only) |

### Day 0: Create Operator Roles

```bash
rosa create operator-roles \
  --cluster <cluster-name-or-id> \
  --mode auto \
  --prefix ManagedOpenShift \
  --yes
```

Creates the IAM roles that cluster operators (ingress, storage, network) use to call AWS APIs. Requires the cluster to exist or the `--oidc-config-id` to be supplied.

**Key flags:**

| Flag | Purpose |
|---|---|
| `--cluster <name\|id>` | Target cluster |
| `--oidc-config-id <id>` | OIDC config ID (alternative to `--cluster` pre-creation) |
| `--prefix <string>` | IAM role name prefix |
| `--mode auto\|manual` | Create vs. print |

### Day 0: Create Cluster (Classic)

```bash
rosa create cluster \
  --cluster-name my-cluster \
  --sts \
  --region us-east-1 \
  --version 4.16.20 \
  --availability-zones us-east-1a,us-east-1b,us-east-1c \
  --compute-machine-type m5.xlarge \
  --replicas 3 \
  --operator-roles-prefix ManagedOpenShift \
  --oidc-config-id <id> \
  --yes
```

Creates a Classic ROSA cluster. The `--sts` flag is required for all new clusters.

**Core flags:**

| Flag | Purpose |
|---|---|
| `--cluster-name <string>` | Cluster name (must be unique in OCM org) |
| `--sts` | Use STS (required for all new clusters) |
| `--region <string>` | AWS region |
| `--version <string>` | OCP version (e.g., `4.16.20`) |
| `--channel-group <string>` | `stable` (default), `candidate`, `nightly` |
| `--availability-zones <list>` | Comma-separated AZ list |
| `--multi-az` | Shorthand for 3-AZ topology |
| `--compute-machine-type <type>` | Instance type for initial machine pool |
| `--replicas <int>` | Initial worker replica count |
| `--min-replicas <int>` | Autoscaler minimum |
| `--max-replicas <int>` | Autoscaler maximum |
| `--operator-roles-prefix <string>` | Prefix used for operator-roles |
| `--oidc-config-id <string>` | OIDC config ID |
| `--role-arn <arn>` | Installer role ARN |
| `--support-role-arn <arn>` | Support role ARN |
| `--controlplane-iam-roles <arn>` | Control plane IAM role ARN |
| `--worker-iam-role <arn>` | Worker node IAM role ARN |
| `--subnet-ids <list>` | Comma-separated subnet IDs (BYO VPC) |
| `--private-link` | Private cluster (no public API endpoint) |
| `--private` | Private API endpoint only |
| `--machine-cidr <cidr>` | Machine network CIDR |
| `--service-cidr <cidr>` | Service network CIDR |
| `--pod-cidr <cidr>` | Pod network CIDR |
| `--host-prefix <int>` | Host prefix for pod network per node |
| `--kms-key-arn <arn>` | Customer-managed KMS key for encryption |
| `--etcd-encryption` | Enable etcd encryption |
| `--fips` | Enable FIPS mode |
| `--enable-autoscaling` | Enable cluster autoscaler |
| `--worker-disk-size <size>` | Root disk size for workers (e.g., `300GiB`) |
| `--ec2-metadata-http-tokens <required\|optional>` | IMDSv2 enforcement |
| `--enable-customer-managed-key` | Use KMS key for encryption |
| `--watch` | Stream install logs after creation |
| `--dry-run` | Validate without creating |
| `--yes` | Skip confirmation |
| `--interactive` | Guided interactive mode |

### Day 0: Create OIDC Provider

```bash
rosa create oidc-provider \
  --cluster <cluster-name-or-id> \
  --mode auto \
  --yes
```

Creates the AWS IAM OIDC provider entry that links the cluster's OIDC config to AWS. Must be run after cluster creation completes.

### Day 1: Monitor Install Logs

```bash
rosa logs install --cluster <name|id> --watch
rosa logs install --cluster <name|id> --tail <n>
```

Streams or tails the cluster installation logs. Use `--watch` to follow in real time.

### Day 2: Describe Cluster

```bash
rosa describe cluster --cluster <name|id>
rosa describe cluster --cluster <name|id> --output json
```

Returns cluster metadata: state, version, region, network, STS configuration, upgrade schedule.

### Day 2: Machine Pools (Classic)

Classic uses MachineSets grouped into machine pools. One machine pool per instance type / AZ combination.

```bash
# List
rosa list machinepool --cluster <name|id>

# Create
rosa create machinepool \
  --cluster <name|id> \
  --name workers-high-mem \
  --instance-type r5.2xlarge \
  --replicas 3 \
  --labels env=prod,tier=high-mem \
  --taints dedicated=high-mem:NoSchedule

# Edit
rosa edit machinepool \
  --cluster <name|id> \
  --name workers-high-mem \
  --replicas 5

# Delete
rosa delete machinepool \
  --cluster <name|id> \
  --name workers-high-mem
```

**Key machinepool flags:**

| Flag | Purpose |
|---|---|
| `--name <string>` | Machine pool name |
| `--instance-type <type>` | EC2 instance type |
| `--replicas <int>` | Fixed replica count |
| `--min-replicas <int>` | Autoscaler min (requires `--enable-autoscaling`) |
| `--max-replicas <int>` | Autoscaler max |
| `--enable-autoscaling` | Enable autoscaler for this pool |
| `--labels <k=v,...>` | Kubernetes node labels |
| `--taints <k=v:Effect,...>` | Kubernetes node taints |
| `--availability-zone <az>` | Pin pool to specific AZ |
| `--subnet <subnet-id>` | Subnet ID (BYO VPC) |
| `--spot-max-price <price>` | Enable Spot with max bid price |
| `--use-spot-instances` | Enable Spot instances |
| `--disk-size <size>` | Root disk size (e.g., `300GiB`) |
| `--root-disk-size <size>` | Alias for `--disk-size` |
| `--aws-tags <k=v,...>` | AWS resource tags |
| `--node-drain-grace-period <duration>` | Grace period before draining |

### Day 2: Identity Providers

```bash
rosa create idp \
  --cluster <name|id> \
  --type htpasswd \
  --name htpasswd-idp

rosa create idp \
  --cluster <name|id> \
  --type github \
  --name github-idp \
  --client-id <id> \
  --client-secret <secret> \
  --organizations <org>

rosa list idp --cluster <name|id>
rosa delete idp --cluster <name|id> --name <idp-name>
```

Supported IDP types: `htpasswd`, `github`, `gitlab`, `google`, `ldap`, `openid`.

### Day 2: Cluster Admin

```bash
rosa create admin --cluster <name|id>
rosa delete admin --cluster <name|id>
```

Creates or deletes the `cluster-admin` local user. Prints the generated password on creation.

### Day 2: Ingress

```bash
rosa list ingress --cluster <name|id>
rosa create ingress --cluster <name|id> --private
rosa edit ingress --cluster <name|id> --id <ingress-id> --private=false
rosa delete ingress --cluster <name|id> --id <ingress-id>
```

### Day 2: Cluster Autoscaler

```bash
rosa create autoscaler --cluster <name|id> \
  --min-cores 0 \
  --max-cores 100 \
  --min-memory 0GiB \
  --max-memory 400GiB \
  --balance-similar-node-groups \
  --skip-nodes-with-local-storage

rosa describe autoscaler --cluster <name|id>
rosa edit autoscaler --cluster <name|id> --max-cores 200
rosa delete autoscaler --cluster <name|id>
```

### Day 2: KubeletConfig

```bash
rosa create kubeletconfig \
  --cluster <name|id> \
  --name high-pid \
  --pod-pids-limit 4096

rosa list kubeletconfig --cluster <name|id>
rosa edit kubeletconfig --cluster <name|id> --name high-pid --pod-pids-limit 8192
rosa delete kubeletconfig --cluster <name|id> --name high-pid
```

### Day 2: Tuning Configs

```bash
rosa create tuning-config \
  --cluster <name|id> \
  --name high-throughput \
  --spec-path tuning.yaml

rosa list tuning-config --cluster <name|id>
rosa edit tuning-config --cluster <name|id> --name high-throughput --spec-path updated.yaml
rosa delete tuning-config --cluster <name|id> --name high-throughput
```

### Upgrades (Classic)

```bash
# List available versions
rosa list upgrade --cluster <name|id>

# Schedule upgrade
rosa upgrade cluster \
  --cluster <name|id> \
  --version 4.16.25 \
  --schedule-date 2026-07-01 \
  --schedule-time 04:00 \
  --yes

# Cancel scheduled upgrade
rosa delete upgrade --cluster <name|id>

# Upgrade operator roles after cluster upgrade
rosa upgrade operator-roles --cluster <name|id> --mode auto --yes
rosa upgrade account-roles --prefix ManagedOpenShift --mode auto --yes
```

### Hibernate / Resume

```bash
rosa hibernate cluster --cluster <name|id>
rosa resume cluster --cluster <name|id>
```

Hibernation stops worker nodes to reduce EC2 costs while preserving cluster configuration. Control plane continues running. Only available on supported cluster configurations.

### Delete Teardown (Classic)

Delete in reverse order. The cluster must be deleted before operator-roles and OIDC config.

```bash
# 1. Delete cluster
rosa delete cluster --cluster <name|id> --watch --yes

# 2. Delete operator roles
rosa delete operator-roles --cluster <name|id> --mode auto --yes

# 3. Delete OIDC provider
rosa delete oidc-provider --cluster <name|id> --mode auto --yes

# 4. Delete OIDC config (if no other clusters use it)
rosa delete oidc-config --oidc-config-id <id> --mode auto --yes

# 5. Delete account roles (only if no clusters in account remain)
rosa delete account-roles --prefix ManagedOpenShift --mode auto --yes
```

---

## Section 3: HCP Cluster Lifecycle

### HCP vs Classic Differences

| Aspect | Classic | HCP |
|---|---|---|
| Control plane | Customer-managed EC2 (3 × m5.2xlarge) | Red Hat-managed, multi-tenant |
| Infra nodes | Customer-managed EC2 (2–3 × r5.xlarge) | None |
| Node pools | MachinePools (MachineSet-based) | NodePools (Hypershift-based) |
| OIDC config | One per cluster | Reusable across clusters |
| Cluster fee | $0 | $0.25/hr ($182.50/mo) |
| ARM support | No | Yes |
| Karpenter | No | 4.22+ |
| Provisioning time | ~52 min | ~15 min |
| Cluster API flag | _(default)_ | `--hosted-cp` |

### Day 0: Create Account Roles (HCP)

Same command as Classic, but specify the HCP version. HCP requires its own account-roles set (different IAM policies).

```bash
rosa create account-roles \
  --mode auto \
  --prefix ManagedOpenShift \
  --version 4.16 \
  --hosted-cp \
  --yes
```

The `--hosted-cp` flag selects HCP-specific IAM policy versions.

### Day 0: Create OIDC Config (Reusable)

HCP OIDC configs can be shared across multiple clusters. Create one per environment or team, not per cluster.

```bash
rosa create oidc-config \
  --mode auto \
  --managed \
  --yes
```

Note the OIDC config ID — reuse it for all clusters that share this OIDC config.

```bash
# List existing OIDC configs
rosa list oidc-config
```

### Day 0: Create Operator Roles (HCP)

```bash
rosa create operator-roles \
  --oidc-config-id <id> \
  --prefix ManagedOpenShift \
  --mode auto \
  --hosted-cp \
  --yes
```

For HCP, pass `--oidc-config-id` directly and add `--hosted-cp`.

### Day 0: Create Cluster (HCP)

```bash
rosa create cluster \
  --cluster-name my-hcp-cluster \
  --hosted-cp \
  --sts \
  --region us-east-1 \
  --version 4.16.20 \
  --availability-zones us-east-1a,us-east-1b,us-east-1c \
  --compute-machine-type m6i.xlarge \
  --replicas 3 \
  --operator-roles-prefix ManagedOpenShift \
  --oidc-config-id <id> \
  --billing-account <aws-account-id> \
  --yes
```

The `--hosted-cp` flag is the primary switch. `--billing-account` specifies which AWS account is billed for HCP compute.

**HCP-specific flags** (in addition to Classic flags):

| Flag | Purpose |
|---|---|
| `--hosted-cp` | Create an HCP cluster |
| `--billing-account <account-id>` | AWS account for billing (may differ from infrastructure account) |
| `--external-auth-providers-enabled` | Enable external authentication providers |

**Networking note for HCP:** HCP requires at least one private subnet per AZ. If using BYO VPC, pass `--subnet-ids` with private subnets only.

### Day 0: No OIDC Provider Step

HCP does not require a separate `rosa create oidc-provider` step. The OIDC provider is automatically configured from the OIDC config ID at cluster creation.

### Day 1: Monitor Install Logs (HCP)

```bash
rosa logs install --cluster <name|id> --watch
```

Same command as Classic; HCP installs in ~15 minutes.

### Day 2: Node Pools (HCP)

HCP uses NodePools (not MachinePools). NodePools support ARM architecture and Karpenter (4.22+).

```bash
# List
rosa list machinepool --cluster <name|id>

# Create node pool (ARM/Graviton)
rosa create machinepool \
  --cluster <name|id> \
  --name arm-workers \
  --instance-type m7g.xlarge \
  --replicas 3 \
  --labels arch=arm64

# Create node pool with autoscaling
rosa create machinepool \
  --cluster <name|id> \
  --name scalable-workers \
  --instance-type m6i.xlarge \
  --enable-autoscaling \
  --min-replicas 2 \
  --max-replicas 20

# Delete
rosa delete machinepool \
  --cluster <name|id> \
  --name arm-workers \
  --yes
```

Note: HCP uses the same `rosa create/list/edit/delete machinepool` CLI surface as Classic, but internally creates NodePool resources.

**HCP node pool additional flags:**

| Flag | Purpose |
|---|---|
| `--upgrade-max-surge-percentage <int>` | Max nodes beyond desired during upgrade |
| `--upgrade-max-unavailable-percentage <int>` | Max nodes unavailable during upgrade |
| `--node-drain-grace-period <duration>` | Grace period before draining nodes |

### Day 2: External Auth Providers (HCP)

HCP supports external OIDC authentication providers (e.g., Entra ID, Okta) as an alternative to OCM-managed IDPs.

```bash
rosa create external-auth-provider \
  --cluster <name|id> \
  --name entra-id \
  --issuer-url https://login.microsoftonline.com/<tenant>/v2.0 \
  --client-id <app-client-id>

rosa list external-auth-provider --cluster <name|id>
rosa describe external-auth-provider --cluster <name|id> --name entra-id
rosa delete external-auth-provider --cluster <name|id> --name entra-id
```

### Upgrades (HCP)

HCP supports cron-scheduled upgrades (Classic uses date/time scheduling only).

```bash
# List available versions
rosa list upgrade --cluster <name|id>

# One-time upgrade
rosa upgrade cluster \
  --cluster <name|id> \
  --version 4.16.25 \
  --schedule-date 2026-07-01 \
  --schedule-time 04:00 \
  --yes

# Recurring cron schedule
rosa upgrade cluster \
  --cluster <name|id> \
  --version 4.16.25 \
  --schedule "0 4 * * 2" \
  --yes

# Upgrade a specific node pool
rosa upgrade machinepool \
  --cluster <name|id> \
  --machinepool <name> \
  --version 4.16.25 \
  --schedule-date 2026-07-01 \
  --schedule-time 05:00 \
  --yes

# Cancel scheduled upgrade
rosa delete upgrade --cluster <name|id>
```

### Delete Teardown (HCP)

HCP teardown is simpler — no OIDC provider to delete separately.

```bash
# 1. Delete cluster
rosa delete cluster --cluster <name|id> --watch --yes

# 2. Delete operator roles
rosa delete operator-roles \
  --oidc-config-id <id> \
  --prefix ManagedOpenShift \
  --mode auto \
  --yes

# 3. Delete OIDC config (only if no other clusters use it)
rosa delete oidc-config --oidc-config-id <id> --mode auto --yes

# 4. Delete account roles (only if account is fully decommissioned)
rosa delete account-roles --prefix ManagedOpenShift --mode auto --yes
```

---

<!-- sections 4 and 5 follow in the next commit -->
