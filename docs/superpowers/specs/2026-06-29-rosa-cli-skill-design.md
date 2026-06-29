# ROSA CLI Skill Design

## Goal

Create `plugins/rosa/skills/rosa-cli/SKILL.md` — a comprehensive AI guidance skill covering the ROSA CLI (`rosa`). The skill gives Claude accurate command syntax, flag names, Classic/HCP behavioral differences, sequencing requirements, and output formats so it can guide users through any ROSA CLI task without making up flags or ordering errors.

## Placement and Companions

- **Skill:** `plugins/rosa/skills/rosa-cli/SKILL.md`
- **Reference companion:** `plugins/rosa/skills/rosa-cli/AGENTS.md` (clone instruction for `references/rosa-cli`)
- **Plugin:** existing `plugins/rosa/` — bump `plugin.json` version

## Scope

- **Self-contained.** No cross-references to the ocm-cli skill. Any command that overlaps (e.g. login, cluster describe) is documented fully in this skill.
- **Classic and HCP.** Both cluster types covered with explicit parallel sections — no "similar to Classic" shortcuts.
- **Every subcommand has a reference entry** in the Command Reference section (Section 4).
- **Not in scope:** rosa-cost pricing calculations (handled by rosa-cost skill).

---

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

## Section 4: Command Reference

Every `rosa` subcommand, organized alphabetically within groups. For commands covered in Sections 2–3, this section provides the complete flag table without repeating the lifecycle context.

### attach / detach

```bash
rosa attach policy --cluster <name|id> --policy-arn <arn>
rosa detach policy --cluster <name|id> --policy-arn <arn>
```

Attaches or detaches IAM managed policies to cluster IAM roles. Used for adding permissions beyond the default ROSA policy set.

### completion

```bash
rosa completion bash
rosa completion zsh
rosa completion fish
rosa completion powershell
```

Generates shell completion scripts. Add to shell profile with:

```bash
source <(rosa completion bash)
```

### config

```bash
rosa config get <key>
rosa config set <key> <value>
rosa config delete <key>
```

Manages individual keys in the active OCM config file (`$OCM_CONFIG`). Useful for scripting and CI pipelines.

### create account-roles

See Section 2 (Classic) and Section 3 (HCP). Key additional flags:

| Flag | Purpose |
|---|---|
| `--force-policy-creation` | Recreate policies even if they exist |
| `--path <path>` | IAM path (e.g., `/rosa/`) |
| `--permissions-boundary <arn>` | IAM permissions boundary |

### create admin

```bash
rosa create admin --cluster <name|id>
```

Creates a local `cluster-admin` user. The generated password is printed once — save it. There is no flag to set a custom password; delete and recreate to rotate.

### create autoscaler

```bash
rosa create autoscaler --cluster <name|id> [flags]
```

| Flag | Purpose |
|---|---|
| `--min-cores <int>` | Minimum cluster-wide cores |
| `--max-cores <int>` | Maximum cluster-wide cores |
| `--min-memory <size>` | Minimum cluster-wide memory (e.g., `0GiB`) |
| `--max-memory <size>` | Maximum cluster-wide memory |
| `--balance-similar-node-groups` | Attempt to balance similar node groups |
| `--skip-nodes-with-local-storage` | Don't scale down nodes with local storage |
| `--log-verbosity <int>` | Autoscaler log verbosity |
| `--max-pod-grace-period <int>` | Seconds before force-deleting pods |
| `--pod-priority-threshold <int>` | Only scale for pods above this priority |
| `--scale-down-enabled` | Enable scale-down |
| `--scale-down-delay-after-add <duration>` | Wait after scale-up before scale-down |
| `--scale-down-delay-after-delete <duration>` | Wait after scale-down before next |
| `--scale-down-delay-after-failure <duration>` | Wait after failed scale-down |
| `--scale-down-utilization-threshold <float>` | Scale down if node below this utilization |

### create break-glass-credentials

```bash
rosa create break-glass-credentials \
  --cluster <name|id> \
  --username <name> \
  --expiration <duration>
```

Creates emergency credentials (kubeconfig) for cluster access when normal auth is unavailable. HCP only.

### create cluster

See Section 2 (Classic) and Section 3 (HCP) for the full flag table.

### create dns-domain

```bash
rosa create dns-domain
```

Creates a custom DNS domain for use with ROSA clusters. Not commonly needed — OCM provides a default `openshiftapps.com` domain.

### create external-auth-provider

See Section 3 (HCP Day 2).

### create iam-service-account

```bash
rosa create iam-service-account \
  --cluster <name|id> \
  --name <name> \
  --namespace <namespace> \
  --role-arn <arn>
```

Creates an AWS IAM service account annotation on a Kubernetes service account, enabling IRSA (IAM Roles for Service Accounts) for workloads.

### create idp

```bash
rosa create idp --cluster <name|id> --type <type> --name <name> [type-specific-flags]
```

| IDP type | Required flags |
|---|---|
| `htpasswd` | _(interactive — no CLI flags for user/pass)_ |
| `github` | `--client-id`, `--client-secret`, `--organizations` or `--teams` |
| `gitlab` | `--client-id`, `--client-secret`, `--host-url` |
| `google` | `--client-id`, `--client-secret`, `--hosted-domain` |
| `ldap` | `--url`, `--bind-dn`, `--bind-password`, `--id-attrs` |
| `openid` | `--client-id`, `--client-secret`, `--issuer-url`, `--email-claims`, `--name-claims`, `--username-claims` |

### create image-mirror

```bash
rosa create image-mirror \
  --cluster <name|id> \
  --source <registry/image> \
  --dest <registry/image>
```

Configures image mirroring rules for disconnected or air-gapped cluster environments.

### create ingress

```bash
rosa create ingress --cluster <name|id> [--private]
```

Creates an additional ingress controller. The `--private` flag makes the load balancer internal-only.

### create kubeletconfig

See Section 2 (Day 2 KubeletConfig).

### create log-forwarder

```bash
rosa create log-forwarder \
  --cluster <name|id> \
  --spec-path logforwarder.yaml
```

Configures cluster-level log forwarding via a ClusterLogForwarder manifest. HCP and Classic.

### create machinepool

See Section 2 (Classic Day 2 Machine Pools) and Section 3 (HCP Day 2 Node Pools).

### create network

```bash
rosa create network \
  --region us-east-1 \
  --template-dir ./network-templates \
  --param VpcCidr=10.0.0.0/16
```

Creates AWS network resources from a CloudFormation template. Used for pre-provisioning VPCs for BYO networking.

### create ocm-role

```bash
rosa create ocm-role \
  --mode auto \
  --prefix ManagedOpenShift \
  --admin \
  --yes
```

Creates the OCM organization role that allows OCM to interact with the AWS account. Required for the first ROSA cluster in an AWS account.

| Flag | Purpose |
|---|---|
| `--admin` | Create with admin permissions (required for STS cluster creation) |
| `--prefix <string>` | Role name prefix |

### create oidc-config

See Section 2 (Classic Day 0) and Section 3 (HCP Day 0).

### create oidc-provider

```bash
rosa create oidc-provider --cluster <name|id> --mode auto --yes
```

Classic only — creates the IAM OIDC provider entry. HCP creates this automatically.

### create operator-roles

See Section 2 (Classic) and Section 3 (HCP).

### create service

```bash
rosa create service --type <type> [flags]
```

Creates a managed cloud service (e.g., RDS, ElastiCache) linked to the cluster via AWS Controllers for Kubernetes (ACK). Experimental.

### create tuning-config

See Section 2 (Day 2 Tuning Configs).

### create user-role

```bash
rosa create user-role --mode auto --prefix ManagedOpenShift --yes
```

Creates the OCM user role that links the OCM user account to an AWS IAM role. Required for STS cluster creation.

### delete account-roles

```bash
rosa delete account-roles --prefix ManagedOpenShift --mode auto --yes
```

Deletes all account-level IAM roles with the given prefix. Only run when decommissioning the entire ROSA presence in an AWS account.

### delete admin

```bash
rosa delete admin --cluster <name|id>
```

Removes the `cluster-admin` local user.

### delete autoscaler

```bash
rosa delete autoscaler --cluster <name|id>
```

### delete break-glass-credentials

```bash
rosa delete break-glass-credentials --cluster <name|id> --id <credential-id>
```

### delete cluster

```bash
rosa delete cluster --cluster <name|id> --watch --yes
```

Initiates cluster deletion. `--watch` streams the deletion log. After deletion completes, clean up operator-roles and OIDC config.

### delete dns-domain

```bash
rosa delete dns-domain --id <domain-id>
```

### delete external-auth-provider

```bash
rosa delete external-auth-provider --cluster <name|id> --name <provider-name>
```

### delete iam-service-account

```bash
rosa delete iam-service-account --cluster <name|id> --name <name> --namespace <namespace>
```

### delete idp

```bash
rosa delete idp --cluster <name|id> --name <idp-name>
```

### delete image-mirror

```bash
rosa delete image-mirror --cluster <name|id> --id <mirror-id>
```

### delete ingress

```bash
rosa delete ingress --cluster <name|id> --id <ingress-id>
```

The default ingress controller cannot be deleted.

### delete kubeletconfig

```bash
rosa delete kubeletconfig --cluster <name|id> --name <config-name>
```

### delete log-forwarder

```bash
rosa delete log-forwarder --cluster <name|id>
```

### delete machinepool

```bash
rosa delete machinepool --cluster <name|id> --name <pool-name> --yes
```

The default machine pool (`workers`) cannot be deleted.

### delete ocm-role

```bash
rosa delete ocm-role --role-arn <arn> --mode auto --yes
```

### delete oidc-config

```bash
rosa delete oidc-config --oidc-config-id <id> --mode auto --yes
```

Only delete if no clusters are using the OIDC config.

### delete oidc-provider

```bash
rosa delete oidc-provider --cluster <name|id> --mode auto --yes
```

Classic only. Run after cluster deletion.

### delete operator-roles

```bash
# By cluster (Classic)
rosa delete operator-roles --cluster <name|id> --mode auto --yes

# By OIDC config ID (HCP, or when cluster is already deleted)
rosa delete operator-roles --oidc-config-id <id> --prefix ManagedOpenShift --mode auto --yes
```

### delete service

```bash
rosa delete service --id <service-id>
```

### delete tuning-config

```bash
rosa delete tuning-config --cluster <name|id> --name <config-name>
```

### delete upgrade

```bash
rosa delete upgrade --cluster <name|id>
```

Cancels a scheduled cluster upgrade.

### delete user-role

```bash
rosa delete user-role --role-arn <arn> --mode auto --yes
```

### describe access-request

```bash
rosa describe access-request --id <request-id>
```

### describe account-roles

```bash
rosa describe account-roles --prefix ManagedOpenShift
```

Shows the ARNs and policy versions of account-level IAM roles.

### describe addon

```bash
rosa describe addon --addon-id <id>
```

### describe break-glass-credentials

```bash
rosa describe break-glass-credentials --cluster <name|id>
```

### describe cluster

```bash
rosa describe cluster --cluster <name|id>
rosa describe cluster --cluster <name|id> --output json
```

Full cluster detail: state, version, STS config, network CIDRs, node counts, upgrade schedule.

### describe dns-domain

```bash
rosa describe dns-domain --id <domain-id>
```

### describe external-auth-provider

```bash
rosa describe external-auth-provider --cluster <name|id> --name <provider-name>
```

### describe gates

```bash
rosa describe gates --version <version>
```

Lists version gate acknowledgments required before upgrading to a given version.

### describe iam-service-accounts

```bash
rosa describe iam-service-accounts --cluster <name|id>
```

### describe idp

```bash
rosa describe idp --cluster <name|id> --name <idp-name>
```

### describe image-mirror

```bash
rosa describe image-mirror --cluster <name|id>
```

### describe ingress

```bash
rosa describe ingress --cluster <name|id>
```

### describe instance-types

```bash
rosa describe instance-types
```

Lists available EC2 instance types for ROSA clusters.

### describe kubeletconfig

```bash
rosa describe kubeletconfig --cluster <name|id> --name <config-name>
```

### describe log-forwarder

```bash
rosa describe log-forwarder --cluster <name|id>
```

### describe machinepool

```bash
rosa describe machinepool --cluster <name|id> --machinepool <pool-name>
```

### describe ocm-roles

```bash
rosa describe ocm-roles
```

### describe oidc-config

```bash
rosa describe oidc-config --id <oidc-config-id>
```

### describe oidc-provider

```bash
rosa describe oidc-provider --cluster <name|id>
```

### describe operator-roles

```bash
rosa describe operator-roles --cluster <name|id>
```

### describe region

```bash
rosa describe region --region <region>
```

Shows ROSA availability and supported features for a given AWS region.

### describe rh-region

```bash
rosa describe rh-region
```

Shows the OCM API region (API endpoint geography).

### describe service

```bash
rosa describe service --id <service-id>
```

### describe tuning-config

```bash
rosa describe tuning-config --cluster <name|id> --name <config-name>
```

### describe upgrade

```bash
rosa describe upgrade --cluster <name|id>
```

Shows the current or scheduled upgrade for a cluster.

### describe user

```bash
rosa describe user --cluster <name|id>
```

### describe user-roles

```bash
rosa describe user-roles
```

### describe version

```bash
rosa describe version --version <version>
```

Shows release notes, channel group, and upgrade paths for a specific OCP version.

### docs

```bash
rosa docs
```

Opens the ROSA documentation in the default browser.

### download

```bash
rosa download rosa
rosa download kubectl
rosa download oc
rosa download rosa-client
```

Downloads the specified CLI binary to the current directory.

### edit autoscaler

```bash
rosa edit autoscaler --cluster <name|id> [flags]
```

Same flags as `create autoscaler`.

### edit cluster

```bash
rosa edit cluster --cluster <name|id> [flags]
```

| Flag | Purpose |
|---|---|
| `--private` | Toggle private API endpoint |
| `--enable-autoscaling` | Enable cluster autoscaler |
| `--min-replicas <int>` | Autoscaler min workers |
| `--max-replicas <int>` | Autoscaler max workers |
| `--node-drain-grace-period <duration>` | Grace period for node drain |
| `--audit-log-arn <arn>` | Enable audit logging to CloudWatch |

### edit image-mirror

```bash
rosa edit image-mirror --cluster <name|id> --id <mirror-id> [flags]
```

### edit ingress

```bash
rosa edit ingress --cluster <name|id> --id <ingress-id> [flags]
```

| Flag | Purpose |
|---|---|
| `--private` | Make ingress load balancer internal |
| `--lb-type <type>` | `nlb` or `classic` |
| `--excluded-namespaces <list>` | Namespaces excluded from this ingress |
| `--wildcard-policy <policy>` | `WildcardsAllowed` or `WildcardsDisallowed` |
| `--namespace-ownership-policy <policy>` | `Strict` or `InterNamespaceAllowed` |

### edit kubeletconfig

```bash
rosa edit kubeletconfig --cluster <name|id> --name <config-name> --pod-pids-limit <int>
```

### edit log-forwarder

```bash
rosa edit log-forwarder --cluster <name|id> --spec-path updated.yaml
```

### edit machinepool

```bash
rosa edit machinepool --cluster <name|id> --name <pool-name> [flags]
```

Same flags as `create machinepool` except instance type and AZ are immutable after creation.

### edit service

```bash
rosa edit service --id <service-id> [flags]
```

### edit tuning-config

```bash
rosa edit tuning-config --cluster <name|id> --name <config-name> --spec-path updated.yaml
```

### grant

```bash
rosa grant user <role> --cluster <name|id> --user <username>
```

Grants a cluster role (`cluster-admin`, `dedicated-admin`) to a user. Requires an IDP to be configured.

### hibernate

```bash
rosa hibernate cluster --cluster <name|id>
```

Hibernates a cluster. See Section 2 for context.

### initialize

```bash
rosa initialize [--region <region>]
```

Runs pre-flight checks and initializes the AWS account for ROSA: verifies AWS credentials, IAM permissions, service quotas, and ELB roles. Run once before creating the first cluster in an account.

### install / uninstall add-ons

```bash
# Install
rosa install addon <addon-id> --cluster <name|id> [addon-specific-flags]

# Check status
rosa describe addon --cluster <name|id> --addon-id <id>

# Uninstall
rosa uninstall addon <addon-id> --cluster <name|id>
```

Add-ons are managed Red Hat or partner services installed into clusters (e.g., RHODS, Compliance Operator, cost-management).

### link / unlink

```bash
rosa link ocm-role --role-arn <arn>
rosa unlink ocm-role --role-arn <arn>

rosa link user-role --role-arn <arn>
rosa unlink user-role --role-arn <arn>
```

Links or unlinks an AWS IAM role to the OCM organization or user identity. Required as part of the initial STS setup.

### list access-requests

```bash
rosa list access-requests
```

### list account-roles

```bash
rosa list account-roles --prefix ManagedOpenShift
```

### list addon

```bash
rosa list addon
rosa list addon --cluster <name|id>
```

Lists available add-ons (without `--cluster`) or installed add-ons (with `--cluster`).

### list autoscaler

```bash
rosa describe autoscaler --cluster <name|id>
```

(The autoscaler list is actually `describe` — there is only one autoscaler per cluster.)

### list break-glass-credentials

```bash
rosa list break-glass-credentials --cluster <name|id>
```

### list cluster

```bash
rosa list cluster
rosa list cluster --output json
```

Lists all clusters visible to the authenticated OCM user.

### list dns-domain

```bash
rosa list dns-domains
```

### list external-auth-provider

```bash
rosa list external-auth-provider --cluster <name|id>
```

### list iam-service-account

```bash
rosa list iam-service-account --cluster <name|id>
```

### list idp

```bash
rosa list idp --cluster <name|id>
```

### list image-mirror

```bash
rosa list image-mirror --cluster <name|id>
```

### list ingress

```bash
rosa list ingress --cluster <name|id>
```

### list installation

```bash
rosa list installation --cluster <name|id>
```

Lists installation history for a cluster.

### list kubeletconfig

```bash
rosa list kubeletconfig --cluster <name|id>
```

### list log-forwarder

```bash
rosa list log-forwarder --cluster <name|id>
```

### list machinepool

```bash
rosa list machinepool --cluster <name|id>
rosa list machinepool --cluster <name|id> --output json
```

### list ocm-roles

```bash
rosa list ocm-roles
```

### list oidc-config

```bash
rosa list oidc-config
```

Lists all OIDC configs in the OCM organization.

### list oidc-provider

```bash
rosa list oidc-provider
```

### list operator-roles

```bash
rosa list operator-roles --prefix ManagedOpenShift
```

### list region

```bash
rosa list region
rosa list region --multi-az
```

Lists AWS regions where ROSA is available. `--multi-az` limits to regions with 3+ AZs.

### list service

```bash
rosa list service --cluster <name|id>
```

### list tuning-config

```bash
rosa list tuning-config --cluster <name|id>
```

### list upgrade

```bash
rosa list upgrade --cluster <name|id>
```

Lists available upgrade versions for a cluster.

### list user-roles

```bash
rosa list user-roles
```

### list version

```bash
rosa list version
rosa list version --channel-group candidate
rosa list version --hosted-cp
```

Lists available OCP versions. `--hosted-cp` shows HCP-compatible versions.

### login

See Section 1.

### logout

See Section 1.

### logs

```bash
rosa logs install --cluster <name|id> [--watch] [--tail <n>]
rosa logs uninstall --cluster <name|id> [--watch]
```

Streams or tails cluster install or uninstall logs.

### register

```bash
rosa register cluster --cluster-id <id> [--domain-prefix <prefix>]
```

Registers an externally provisioned HCP cluster with OCM. Used for bring-your-own-cluster scenarios.

### resume

```bash
rosa resume cluster --cluster <name|id>
```

Resumes a hibernated cluster. See Section 2.

### revoke

```bash
rosa revoke user <role> --cluster <name|id> --user <username>
```

Revokes a cluster role from a user.

### token

See Section 1.

### upgrade account-roles

```bash
rosa upgrade account-roles --prefix ManagedOpenShift --mode auto --yes
```

Upgrades account-level IAM roles to the latest policy version. Run after an OCP version upgrade.

### upgrade cluster

See Section 2 (Classic) and Section 3 (HCP) for full scheduling syntax.

### upgrade machinepool

```bash
rosa upgrade machinepool \
  --cluster <name|id> \
  --machinepool <name> \
  --version <version> \
  --schedule-date <date> \
  --schedule-time <time> \
  --yes
```

Schedules an upgrade for a specific node pool (HCP) or machine pool.

### upgrade operator-roles

```bash
rosa upgrade operator-roles --cluster <name|id> --mode auto --yes
```

Upgrades operator role policies after a cluster OCP version upgrade.

### upgrade roles

```bash
rosa upgrade roles --cluster <name|id> --mode auto --yes
```

Alias for upgrading all cluster-associated roles (operator roles + account roles) in one step.

### verify

```bash
rosa verify openshift-client
rosa verify permissions
rosa verify quota [--region <region>]
```

| Subcommand | Purpose |
|---|---|
| `openshift-client` | Checks that `oc` is installed and accessible |
| `permissions` | Validates AWS IAM permissions required for ROSA |
| `quota` | Validates AWS service quotas for the target region |

### version

```bash
rosa version
```

Prints the installed ROSA CLI version. Compare against https://github.com/openshift/rosa/releases to determine if an upgrade is needed.

### whoami

See Section 1.

---

## Section 5: Self-Improvement Principle

When a command produces unexpected output or an error:

1. Check the ROSA CLI reference source at `references/rosa-cli/` (clone instructions in `AGENTS.md` alongside this skill).
2. Verify the installed CLI version with `rosa version` against the latest release.
3. For unknown flags or changed behavior, check `references/rosa-cli/CHANGELOG.md` for the relevant version range.
4. Update this skill if a discrepancy is confirmed — do not silently work around it.

---

## Implementation Notes

### SKILL.md Frontmatter

```yaml
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
```

### AGENTS.md Contents

```markdown
# rosa-cli Skill — Developer Reference

This skill was built from the ROSA CLI source. For major updates (new subcommands, API changes, flag changes), clone the reference first:

    git clone https://github.com/openshift/rosa references/rosa-cli

The reference is gitignored. Do not commit it.

## When to load the reference

- Adding coverage for a new `rosa` subcommand
- Reconciling the skill against a new ROSA CLI release
- Verifying exact flag names or output formats before updating SKILL.md

## Key paths in the reference

| Path | What to find there |
|---|---|
| `cmd/` | All subcommands — one directory per command group |
| `cmd/create/cluster/cmd.go` | Cluster creation flags (most complex command) |
| `cmd/create/machinepool/` | Machine pool / node pool flags |
| `cmd/login/cmd.go` | Login flow and token auth |
| `CHANGELOG.md` | Release history — scan this first for new versions |
| `pkg/arguments/` | Common flag definitions shared across commands |

## Checking the installed version

    rosa version

Compare against https://github.com/openshift/rosa/releases to determine whether the skill needs reconciliation.
```

### Plugin Changes

- Create `plugins/rosa/skills/rosa-cli/SKILL.md` (new file)
- Create `plugins/rosa/skills/rosa-cli/AGENTS.md` (new file)
- Bump `plugins/rosa/.claude-plugin/plugin.json` version (0.3.1 → 0.4.0)

### Lint / Update

After creating the skill files, run:

```bash
make lint    # validates structure
make update  # syncs docs and marketplace
```
