---
description: Generate Terraform to adopt an existing ROSA HCP cluster (terraform-redhat/rosa-hcp module + import blocks); optional VPC adopt via network skill.
argument-hint: <hcp-cluster-name-or-id> [output-directory]
---

## Name

rosa:hcp-adopt

## Synopsis

```
/rosa:hcp-adopt <hcp-cluster> [output-dir]
```

## Description

Import a **running ROSA HCP** cluster into Terraform using the supported **`terraform-redhat/rosa-hcp/rhcs`** module. Writes **`imports.tf`**, tfvars aligned with live STS/OIDC ARNs, and optional **`network/`** adopt stack when the operator wants VPC under Terraform too.

Does not run **`terraform apply`** by default.

## Implementation

**The agent runs every step below** (rosa/ocm, Python generators, `terraform fmt`/`validate`). Do not tell the operator to run skill scripts unless they explicitly want offline copy-paste.

1. Follow **rosa-cli** for auth.
2. Collect HCP cluster, machine pool (node pool), and ingress JSON; optional **`ocm get .../autoscaler`** when cluster-level autoscaler may apply.
3. Run **`discover_cluster_network.py`** (HCP-compatible) → keep **`network-inventory.json`** for subnet wiring and an optional network stack. Summarize VPC/subnets/TGW highlights in chat (briefing or dry-run context).
4. Run **`hcp_adopt_to_tf.py --dry-run`** (pass **`--network-inventory`**) — present summary.
5. **Stop and ask:** adopt **cluster only** or **cluster + network**? **Shared VPC** is out of scope — BYO VPC adopt only. If inventory lists **customer** VPC endpoints (`adoptable`), ask whether to include them in **`network/`** (`network_to_tf.py` without `--skip-endpoints`). **Never** adopt the **ROSA HCP control-plane VPCE** in `network/` — ROSA-managed; **do** wire **additional control-plane SGs** on the **cluster** stack when discovery finds them (private clusters). **Do not run `--write`** until they answer.
6. **`hcp_adopt_to_tf.py --write`** cluster stack to `[output-dir]`.
7. **If cluster + network:** **`network_to_tf.py --mode adopt --write`** (respect endpoint choice via `--skip-endpoints` when operator declines). **Private clusters:** additional CP SG associations import via root **`additional-cp-sg`** module when discovery finds them.
8. **`terraform fmt`** + **`terraform validate`** (+ **`terraform plan`**) on each root; document in **`ADOPT.md`**.

Set `OUTPUT_DIR` from the optional second argument (e.g. `./my-hcp-adopt`). To publish an anonymized copy for docs, use `plugins/rosa/scripts/publish_example_stack.py` (see repo `examples/rosa/`).

## Notes

- Not for ROSA Classic — use **classic-to-hcp** / **classic-to-hcp-full** instead.
- Shared **Transit Gateway** / hub routes: use commented **`transit_gateway_optional.tf`** from network generation; coordinate with network team.
