---
name: rosa-classic-to-hcp-terraform
description: |
  Use when generating Terraform for a new ROSA HCP cluster from an existing ROSA Classic
  cluster: hosted-cp module, tfvars, machine pool shape, private vs public, cluster-specific
  IAM roles, or Classic-to-HCP migration Terraform. Requires a running Classic cluster and
  rosa login.

  NOT for: applying Terraform, creating VPCs, or clusters that are already HCP.
license: Apache-2.0
metadata:
  user_invocable: "false"
  model: inherit
  color: "#cc0000"
---

# ROSA Classic → HCP Terraform

Generate a pinned [`terraform-redhat/rosa-hcp/rhcs`](https://registry.terraform.io/modules/terraform-redhat/rosa-hcp/rhcs/latest) stack from live Classic cluster JSON. **Do not hand-write HCL** — run the mapper script.

## Agent rules

1. **REQUIRED:** Follow the `rosa-cli` skill for OCM profile / `rosa login` before collecting JSON.
2. **REQUIRED:** Run `scripts/classic_to_hcp.py` for all mapping. Do not recompute replicas, pool names, CIDRs, `private`, or IAM prefixes in prose.
3. **REQUIRED — confirmation gate:** Do not run `--write` until the operator has seen the **Classic inventory briefing** and **dry-run** (including the **OpenShift version** section), and has confirmed target name, CIDR reuse, infra pools, and **`--openshift-version`** when multiple hosted-cp minor lines are offered.
4. Do not run `terraform apply`. Stop after `terraform fmt` and `terraform validate` when Terraform is installed.
5. Never write `RHCS_TOKEN` or admin passwords into generated files.

## Collect inputs

Save four JSON files (paths passed to the script):

```bash
CLUSTER="<classic-name-or-id>"
rosa describe cluster --cluster "${CLUSTER}" --output json > /tmp/classic-cluster.json
rosa list machinepools --cluster "${CLUSTER}" --output json > /tmp/classic-machinepools.json
rosa list ingresses --cluster "${CLUSTER}" --output json > /tmp/classic-ingress.json
rosa list versions --hosted-cp --output json > /tmp/hosted-cp-versions.json
python3 "${SKILL_ROOT}/scripts/fetch_classic_idps.py" \
  --cluster "${CLUSTER}" \
  --output /tmp/classic-idps-inventory.json
```

Resolve the current module version from the Terraform Registry (pin in `--module-version`).

## Workflow

**Step 1 — Dry run**

```bash
SKILL_ROOT="plugins/rosa/skills/rosa-classic-to-hcp-terraform"  # adjust to repo path

python3 "${SKILL_ROOT}/scripts/classic_to_hcp.py" --dry-run \
  --cluster-json /tmp/classic-cluster.json \
  --machinepools-json /tmp/classic-machinepools.json \
  --ingress-json /tmp/classic-ingress.json \
  --versions-json /tmp/hosted-cp-versions.json \
  --module-version "<registry-version>"
```

If the cluster is already HCP, the script exits non-zero — stop.

**Step 1b — Inventory briefing**

If not already done in the full workflow, run **summarize_classic_inventory.py** (network skill) after AWS discovery so the operator sees Classic topology, VPC CIDR, and CIDR table before choosing reuse vs new ranges.

**Step 2 — Operator choices**

Show the dry-run output **and** the inventory briefing. **Wait for explicit answers** before `--write`. Ask whether to **keep Classic values** or **change**:

1. **Target cluster name** (default `<classic-name>-hcp`, sanitized).
2. **OpenShift version** — the dry-run **OpenShift version (hosted-cp)** block lists Classic vs proposed HCP version:
   - Same **minor** as Classic: auto-pick the **exact** hosted-cp release if present, otherwise the **nearest newer patch** on that minor (e.g. Classic `4.22.0` → HCP `4.22.20`).
   - If hosted-cp also lists **newer minor lines** (Classic `4.20.x`, HCP offers `4.21.x` and `4.22.x`): **stop and ask**. Show the **latest patch per minor line** from dry-run; operator picks one; pass **`--openshift-version`** on `--write`.
3. **Infra pools** — create HCP `machine_pools` mirroring Classic infra (per-AZ on multi-AZ; `infra-1` ×2 on single-AZ)?
4. **CIDR reuse** — will this HCP VPC share routing with the Classic cluster (or other networks using the same machine/pod CIDRs)?
   - Yes → `--reuse-cidrs` (only when VPC/subnet strategy allows; usually **adopt** or Classic decommissioned)
   - No → `--unique-cidrs` (operator supplies new machine/pod CIDRs in tfvars; for **copy** VPC, set `machine_cidr` to fit inside the **new** VPC CIDR)
5. **Private vs public** — match Classic unless the operator wants different ingress/API (`private`, `default_ingress_listening_method` in tfvars).
6. **Multi-AZ vs single-AZ** — match Classic worker AZs unless the operator accepts manual network/HCP edits.
7. **Identity providers** — review Classic IdP inventory; confirm htpasswd replication (new passwords) and whether to enable commented OAuth/OIDC stubs after IdP admin work.
8. **Customer VPC endpoints** (when using **rosa-classic-network-terraform** or **classic-to-hcp-full**) — if inventory lists `adoptable` endpoints, confirm include vs **`--skip-endpoints`**. Never adopt ROSA HCP **control-plane VPCE** in `network/`. **Shared VPC** is out of scope.

Optional: if the operator already knows the target VPC CIDR, pass `--vpc-cidr` on dry-run to validate `machine_cidr ⊆ vpc_cidr`.

**Step 3 — Write stack**

```bash
OUTPUT_DIR="./<target-cluster-name>"
python3 "${SKILL_ROOT}/scripts/classic_to_hcp.py" --write \
  --include-infra   # or --no-infra \
  --reuse-cidrs     # or --unique-cidrs \
  --cluster-name "<target-name>" \
  --output-dir "${OUTPUT_DIR}" \
  --cluster-json /tmp/classic-cluster.json \
  --machinepools-json /tmp/classic-machinepools.json \
  --ingress-json /tmp/classic-ingress.json \
  --versions-json /tmp/hosted-cp-versions.json \
  --module-version "<registry-version>" \
  --openshift-version "<hosted-cp-version>" \
  --idps-json /tmp/classic-idps-inventory.json
```

**Step 4 — Validate**

```bash
cd "${OUTPUT_DIR}"
terraform fmt
terraform init -backend=false
terraform validate
```

Tell the operator to **review `terraform.tfvars`** (especially admin credentials and CIDRs) before apply. Generated stacks default to `admin` with a placeholder password (RHCS requires length ≥ 14); replace before apply.

## Identity providers

- Run **`fetch_classic_idps.py`** (`rosa list idps` + `ocm get` per IdP + htpasswd user list).
- **`--idps-json`** on **`classic_to_hcp.py --write`**:
  - **htpasswd** → active `identity_providers` in tfvars + `random_password` per user (`idp_htpasswd.tf`). Classic password hashes are **not** exported; usernames are copied with new passwords.
  - **openid / github / gitlab / google / ldap** → commented entries in **`identity_providers_optional.tf`** with non-secret fields from Classic. Guide the operator: register redirect URI `https://oauth-openshift.apps.<domain>/oauth2callback/<idp-name>`, new client secret, then uncomment and merge into `var.identity_providers`.

## Output files

| File | Purpose |
|------|---------|
| `versions.tf` | Providers; AWS region from Classic |
| `main.tf` | `module "rosa_hcp"` |
| `variables.tf` | Inputs + `machine_cidr` ⊆ `vpc_cidr` validation when set |
| `terraform.tfvars` | Operator-editable values |
| `README.md` | Operator runbook (prerequisites, Makefile, migration pointers) |
| `Makefile` | Split-stack targets when `network/` is added later |
| `MIGRATION.md` | Translations, unmapped Classic settings, CIDR notes (see **README.md**) |
| `identity_providers_optional.tf` | Commented OAuth/OIDC/LDAP IdPs (when `--idps-json` set) |
| `idp_htpasswd.tf` | `random_password` resources for replicated htpasswd users |

## Reference

Field-level Classic → module mapping: see **rosa-classic-to-hcp-terraform** skill. Network/subnet wiring: **rosa-classic-network-terraform** `references/mapping.md`.

Mapper tests: `bash scripts/run_fixture_tests.sh` from this skill directory (includes **`fixtures/idp-mix/`** → golden **`single-az-public-with-idps`**: htpasswd + commented OIDC/GitHub).
