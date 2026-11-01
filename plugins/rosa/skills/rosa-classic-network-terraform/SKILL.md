---
name: rosa-classic-network-terraform
description: |
  Use when generating Terraform for a ROSA Classic cluster's AWS network (VPC, subnets,
  IGW, NAT, endpoints, TGW, SGs, flow logs) from live inventory, with adopt (import) or
  copy (greenfield) modes. Merges subnet wiring into HCP terraform.tfvars from
  rosa-classic-to-hcp-terraform. Requires rosa login and AWS credentials for discovery.

  NOT for: applying Terraform by default, importing Classic IAM into HCP roles, or
  clusters already on HCP-only network automation without Classic source.
license: Apache-2.0
metadata:
  user_invocable: "false"
  model: inherit
  color: "#cc0000"
---

# ROSA Classic network Terraform

Discover AWS networking for a **ROSA Classic** cluster and emit opinionated Terraform plus optional `import` blocks. Pair with **rosa-classic-to-hcp-terraform** for a full Classic → HCP duplicate.

See [SPIKE.md](SPIKE.md) for tooling evaluation (Terraformer deprecated; Former2/aws2tf optional). Default path: **discover_cluster_network.py** + **network_to_tf.py**.

## Agent rules

1. **REQUIRED:** Follow the **rosa-cli** skill for OCM profile / `rosa login` before collecting JSON.
2. **REQUIRED:** Run the scripts in this skill for discovery and HCL; do not hand-write subnet order or CIDR layout.
3. **REQUIRED — confirmation gate:** After discovery, run **summarize_classic_inventory.py** and show the briefing to the operator. **Stop and wait for answers** before any `network_to_tf.py --write`, `classic_to_hcp.py --write`, or `combine_stack.py`. Never assume copy mode, a new VPC CIDR, or `--unique-cidrs` unless the operator chose them.
4. Do not run `terraform apply` unless the operator explicitly requests it outside the default stop point.
5. **Out of scope:** **Shared VPC** (`shared-vpc-resources`) — BYO VPC adopt/copy only.
6. **VPC endpoints:** If discovery lists **customer** (`adoptable`) endpoints, **ask** before **`network_to_tf.py --write`**. Use **`--skip-endpoints`** when the operator declines. **Never** adopt a **ROSA HCP control-plane VPCE** in `network/` (ROSA-managed; rare on Classic-only VPCs). **Private HCP** targets: wire **additional control-plane SGs** on the **cluster** stack (`additional-cp-sg` / inventory `rosa_hcp_control_plane_vpc_endpoint`) — not in the network VPCE resource.
7. Never write secrets or `RHCS_TOKEN` into generated files.
8. While Classic is **`ready`**, do not merge Classic subnet IDs into HCP tfvars without operator acknowledgment (merge script enforces this).

## Collect inputs

```bash
CLUSTER="<classic-name-or-id>"
rosa describe cluster --cluster "${CLUSTER}" --output json > /tmp/classic-cluster.json
rosa list machinepools --cluster "${CLUSTER}" --output json > /tmp/classic-machinepools.json
rosa list ingresses --cluster "${CLUSTER}" --output json > /tmp/classic-ingress.json
python3 "${SKILL_ROOT}/../rosa-classic-to-hcp-terraform/scripts/fetch_classic_idps.py" \
  --cluster "${CLUSTER}" \
  --output /tmp/classic-idps-inventory.json
```

## Workflow

**Step 1 — Discover**

```bash
SKILL_ROOT="plugins/rosa/skills/rosa-classic-network-terraform"

python3 "${SKILL_ROOT}/scripts/discover_cluster_network.py" \
  --cluster-json /tmp/classic-cluster.json \
  --machinepools-json /tmp/classic-machinepools.json \
  --ingress-json /tmp/classic-ingress.json \
  --output /tmp/network-inventory.json
```

**Step 2 — Inventory briefing (required)**

```bash
python3 "${SKILL_ROOT}/scripts/summarize_classic_inventory.py" \
  --cluster-json /tmp/classic-cluster.json \
  --machinepools-json /tmp/classic-machinepools.json \
  --ingress-json /tmp/classic-ingress.json \
  --network-inventory /tmp/network-inventory.json \
  --idps-inventory /tmp/classic-idps-inventory.json
```

Present the full output in chat. Also run **classic_to_hcp.py --dry-run** (see **rosa-classic-to-hcp-terraform**) so the operator sees the proposed HCP mapping.

**Step 3 — Operator choices (wait for explicit answers)**

Ask whether to **keep Classic values** or **change** each item:

| Topic | Classic source | Typical HCP / network choice |
|-------|----------------|------------------------------|
| Target name | `<classic>-hcp` default | Custom name |
| Network mode | N/A | `adopt` vs `copy` |
| VPC CIDR | Discovered VPC CIDR | Same (adopt) or **new** CIDR (copy while Classic is up) |
| Machine / pod CIDR | Cluster `network` object | `--reuse-cidrs` vs `--unique-cidrs` (+ fill new values) |
| Private vs public | API + default ingress | Usually match Classic; changing requires tfvars edits |
| Multi-AZ vs single-AZ | Worker pool AZ list | Usually match; fewer AZs may need manual network/HCP edits |
| Infra pools | Classic `nodes.infra` | `--include-infra` / `--no-infra` |
| **Shared VPC** | N/A | **Skip** — not supported |
| **Customer VPC endpoints** | `adoptable` in inventory | **Ask** — include in `network/` or **`network_to_tf.py --skip-endpoints`** |
| **ROSA HCP control-plane VPCE** | `rosa_hcp_control_plane` in inventory | **Never** in `network/`; additional CP SGs on **cluster** stack when private |
| Network scope | Full discovery | Skip TGW / SGs / flow logs if requested |

Do not proceed to `--write` until the operator confirms or specifies overrides.

**Step 4 — Generate network stack**

```bash
OUTPUT_DIR="./<target-dir>/network"

python3 "${SKILL_ROOT}/scripts/network_to_tf.py" --dry-run \
  --inventory /tmp/network-inventory.json \
  --mode adopt   # or copy

python3 "${SKILL_ROOT}/scripts/network_to_tf.py" --write \
  --inventory /tmp/network-inventory.json \
  --mode copy \
  --vpc-cidr "10.1.0.0/16" \
  --output-dir "${OUTPUT_DIR}"
# Customer VPC endpoints: omit --skip-endpoints only after operator confirms adopt.
# ROSA HCP control-plane VPCE is never written to network/ (discovery excludes it).
```

**Step 5 — Validate**

```bash
cd "${OUTPUT_DIR}"
terraform fmt
terraform init -backend=false
terraform validate
# adopt: after operator runs import/apply, terraform plan should show minimal drift
```

**Step 6 — Merge into HCP tfvars** (after cluster stack from **rosa-classic-to-hcp-terraform**)

```bash
python3 "${SKILL_ROOT}/scripts/merge_hcp_stack.py" \
  --network-outputs "${OUTPUT_DIR}/network-outputs.json" \
  --hcp-tfvars "./<target-dir>/terraform.tfvars" \
  --output "./<target-dir>/terraform.tfvars"
```

Use `--allow-subnet-reuse` only when Classic is decommissioned and HCP will reuse the same subnets.

## Output files

| File | Purpose |
|------|---------|
| `network-inventory.json` | Discovery snapshot (schema v1) |
| `main.tf`, `variables.tf`, `versions.tf` | Network resources |
| `imports.tf` | Adopt mode import blocks |
| `network-outputs.json` | Wiring for merge_hcp_stack.py |
| `INVENTORY.md` | Human summary and follow-ups |
| `Makefile` | Split-stack **`make plan` / `apply` / `destroy`** when cluster root exists alongside `network/` |
| `README.md` | Operator runbook (prerequisites, Makefile, manual Terraform, links) |
| `.mobb-stack.json` | Generated metadata used to refresh README when `network/` is added |
| `transit_gateway_optional.tf` | Commented TGW attachment/routes when Classic used a shared TGW (network-team coordination) |

Field mapping: [references/mapping.md](references/mapping.md).

## Optional tools

- **Former2** — browser export when discovery misses a resource type.
- **aws2tf** — bootstrap import by ID; normalize into this layout manually.
- **Terraformer** — deprecated; do not add as a dependency.
