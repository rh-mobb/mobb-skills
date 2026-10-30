---
name: rosa-hcp-adopt-terraform
description: |
  Use when importing an existing ROSA HCP cluster into Terraform using the
  supported terraform-redhat/rosa-hcp/rhcs registry module (create_* disabled,
  import blocks). Optionally pair with rosa-classic-network-terraform adopt mode
  for the VPC. Requires rosa login, RHCS_TOKEN for plan/apply, and AWS creds
  for network discovery.

  NOT for: ROSA Classic clusters, greenfield HCP create (use rosa-classic-to-hcp-terraform),
  or importing IAM/OIDC resources created outside the module graph.
license: Apache-2.0
metadata:
  user_invocable: "false"
  model: inherit
  color: "#cc0000"
---

# ROSA HCP adopt Terraform

Generate an **adopt** stack for a live **ROSA HCP** cluster: pinned [`terraform-redhat/rosa-hcp/rhcs`](https://registry.terraform.io/modules/terraform-redhat/rosa-hcp/rhcs/latest), matching tfvars, and **`imports.tf`** for cluster, default ingress, and node pools.

Upstream module source: [terraform-redhat/terraform-rhcs-rosa-hcp](https://github.com/terraform-redhat/terraform-rhcs-rosa-hcp). Module ↔ adopt coverage: [references/rosa-hcp-module-adopt-mapping.md](../../references/rosa-hcp-module-adopt-mapping.md).

## Agent rules

1. **REQUIRED:** You run this workflow end-to-end; the operator invokes **`/rosa:hcp-adopt`** or asks in chat — do not hand them a DIY script checklist.
2. **REQUIRED:** Follow **rosa-cli** for auth before collecting JSON.
3. **REQUIRED:** Run **`hcp_adopt_to_tf.py`** — do not hand-write module blocks or import IDs.
4. **REQUIRED — confirmation gate:** Show **`--dry-run`** output and a short network discovery summary. **Ask explicitly:** adopt **cluster only** or **cluster + network** (VPC adopt under **`network/`**). Wait for the operator’s answer before **`--write`** or any **`network_to_tf.py --write`**.
5. Do not run **`terraform apply`** unless the operator explicitly requests it.
6. **Out of scope:** **Shared VPC** — do not generate adopt for `shared-vpc-resources`; BYO VPC only.
7. **VPC endpoints:** **Ask** on customer (`adoptable`) endpoints; **`--skip-endpoints`** when declined. **Never** adopt ROSA HCP **control-plane VPCE** in `network/`. **Do** import **additional CP SGs** on the **cluster** root (`additional-cp-sg`) when inventory lists them.
8. Never write **`RHCS_TOKEN`** or admin passwords into generated files.
9. Tell the operator that **shared TGW / hub routing** is not auto-imported — use **`transit_gateway_optional.tf`** when relevant.

## Modes

| Mode | Network | Cluster |
|------|---------|---------|
| **Cluster only** | Subnet IDs from `rosa describe cluster` | `hcp_adopt_to_tf.py --write` |
| **Cluster + network** | `network_to_tf.py --mode adopt` → **`network/`** (split stack) | Same cluster generator; pass **`--network-inventory`** |
| **Shared VPC** | **Skip** — not supported by MOBB adopt | N/A |
| **Customer VPC endpoints** | **Ask** operator; **`--skip-endpoints`** to omit | **Never** adopt ROSA HCP **control-plane VPCE** in `network/` |
| **Additional CP SGs** | N/A (VPCE stays ROSA-managed) | **Private:** import via root **`additional-cp-sg`** from `rosa_hcp_control_plane_vpc_endpoint` |

For **cluster + network**, run **`network_to_tf.py --mode adopt`** after cluster **`--write`**. Use a **split stack** (`network/` + cluster root). **`combine_stack.py`** is only for **classic-to-hcp-full** copy VPC workflows, not HCP adopt.

## Collect inputs

```bash
CLUSTER="<hcp-name-or-id>"
rosa describe cluster --cluster "${CLUSTER}" --output json > /tmp/hcp-cluster.json
rosa list machinepools --cluster "${CLUSTER}" --output json > /tmp/hcp-machinepools.json
rosa list ingresses --cluster "${CLUSTER}" --output json > /tmp/hcp-ingress.json
```

Optional (recommended for adopt + VPC):

```bash
NET_SKILL="plugins/rosa/skills/rosa-classic-network-terraform"
python3 "${NET_SKILL}/scripts/discover_cluster_network.py" \
  --cluster-json /tmp/hcp-cluster.json \
  --machinepools-json /tmp/hcp-machinepools.json \
  --ingress-json /tmp/hcp-ingress.json \
  --output /tmp/network-inventory.json
```

Run discovery for every adopt invocation so dry-run subnet wiring is accurate and the operator can choose **cluster + network** with full context. If they choose **cluster only**, skip **`network_to_tf.py --write`** (inventory is still used for **`--network-inventory`** on the cluster generator).

## Workflow

```bash
SKILL_ROOT="plugins/rosa/skills/rosa-hcp-adopt-terraform"

python3 "${SKILL_ROOT}/scripts/hcp_adopt_to_tf.py" --dry-run \
  --cluster-json /tmp/hcp-cluster.json \
  --machinepools-json /tmp/hcp-machinepools.json \
  --ingress-json /tmp/hcp-ingress.json \
  --network-inventory /tmp/network-inventory.json \
  --module-version "<registry-version>"

python3 "${SKILL_ROOT}/scripts/hcp_adopt_to_tf.py" --write \
  ...same args... \
  --output-dir ./<cluster-name>-adopt
```

**After dry-run, ask:** cluster only, or cluster + network? Then write cluster; if network, run **`network_to_tf.py --mode adopt --write`** into `./<cluster-name>-adopt/network`.

Then **`terraform fmt`**, **`terraform init`**, **`terraform plan`** (imports + drift review).

## Generated files

| File | Purpose |
|------|---------|
| `main.tf` | `module "rosa_hcp"` with `create_account_roles/oidc/operator_roles = false` |
| `imports.tf` | Import blocks for cluster, ingress, node pools |
| `terraform.tfvars` | Live ARNs, `oidc_config_id`, subnets, pools |
| `README.md` | Operator runbook (prerequisites, Makefile, apply/destroy order) |
| `Makefile` | Optional split-stack targets when `network/` exists |
| `ADOPT.md` | Short pointer to **README.md** |

## Limits

- **IAM roles, OIDC config, operator roles** stay in AWS/OCM — Terraform references them by ARN/id only.
- **HCP autoscaling** is modeled on **node pools** (`machine_pools`). Do not enable **`cluster_autoscaler_enabled`** when pools autoscale; OCM’s cluster `/autoscaler` object is not the same mechanism.
- **Import IDs** for node pools use `{cluster_id},{pool_name}` — verify on first plan (see **README.md**).
- **`properties`**: only non-reserved keys (e.g. `rosa_creator_arn`). `rosa_tf_version` / `rosa_tf_commit` are provider-managed and omitted from tfvars.
- **IdPs, image mirrors, log forwarders** not discovered in v1 — add manually to module variables after adopt.
- Module version should match how the cluster was created when possible (pin **`--module-version`**).

## Tests

```bash
bash scripts/run_fixture_tests.sh
```

Fixture: **`fixtures/demo-hcp-public/`** → golden **`fixtures/golden/demo-hcp-adopt/`**.
