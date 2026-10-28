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
3. Do not run `terraform apply`. Stop after `terraform fmt` and `terraform validate` when Terraform is installed.
4. Never write `RHCS_TOKEN` or admin passwords into generated files.

## Collect inputs

Save four JSON files (paths passed to the script):

```bash
CLUSTER="<classic-name-or-id>"
rosa describe cluster --cluster "${CLUSTER}" --output json > /tmp/classic-cluster.json
rosa list machinepools --cluster "${CLUSTER}" --output json > /tmp/classic-machinepools.json
rosa list ingresses --cluster "${CLUSTER}" --output json > /tmp/classic-ingress.json
rosa list versions --hosted-cp --output json > /tmp/hosted-cp-versions.json
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

**Step 2 — Operator choices**

Show the dry-run output. Ask:

1. **Target cluster name** (default `<classic-name>-hcp`, sanitized).
2. **Infra pools** — create HCP `machine_pools` mirroring Classic infra (per-AZ on multi-AZ; `infra-1` ×2 on single-AZ)?
3. **CIDR reuse** — will this HCP VPC share routing with the Classic cluster (or other networks using the same machine/pod CIDRs)?
   - Yes → `--reuse-cidrs`
   - No → `--unique-cidrs` (leave machine/pod/host_prefix empty; operator fills new ranges)

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
  --module-version "<registry-version>"
```

**Step 4 — Validate**

```bash
cd "${OUTPUT_DIR}"
export RHCS_TOKEN=$(rosa token)  # do not commit; do not echo in chat
terraform fmt
terraform init -backend=false
terraform validate
```

Tell the operator to fill `vpc_cidr`, `aws_subnet_ids`, subnet IDs on each `machine_pools` entry, and admin credentials in `terraform.tfvars`, then read `MIGRATION.md`.

## Output files

| File | Purpose |
|------|---------|
| `versions.tf` | Providers; AWS region from Classic |
| `main.tf` | `module "rosa_hcp"` |
| `variables.tf` | Inputs + `machine_cidr` ⊆ `vpc_cidr` validation when set |
| `terraform.tfvars` | Operator-editable values |
| `MIGRATION.md` | Translations, unmapped Classic settings, CIDR notes |

## Reference

Field-level Classic → module mapping: [references/mapping.md](references/mapping.md).

Mapper tests: `bash scripts/run_fixture_tests.sh` from this skill directory.
