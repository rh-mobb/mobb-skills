---
description: Orchestrate Classic network Terraform plus HCP cluster Terraform from one Classic cluster (discover, adopt or copy VPC, map cluster, merge tfvars).
argument-hint: <classic-cluster-name-or-id> [output-directory]
---

## Name

rosa:classic-to-hcp-full

## Synopsis

```
/rosa:classic-to-hcp-full <classic-cluster> [output-dir]
```

## Description

End-to-end **learn and duplicate** workflow: discover the Classic cluster's AWS network, generate network Terraform (adopt or copy), generate the HCP cluster stack via **rosa-classic-to-hcp-terraform**, merge subnet wiring into `terraform.tfvars`, and validate both stacks. Does not run `terraform apply` by default.

## Implementation

**The agent runs every step below** (rosa/ocm, Python generators, `terraform fmt`/`validate`). Do not tell the operator to run skill scripts unless they explicitly want offline copy-paste.

1. Follow **rosa-cli** for auth.
2. Collect Classic JSON (cluster, machine pools, ingress, hosted-cp versions) as in **rosa-classic-to-hcp-terraform**.
3. Run **fetch_classic_idps.py** → `classic-idps-inventory.json` (list + OCM describe per IdP; htpasswd usernames when OCM exposes them).
4. Run **discover_cluster_network.py** → **summarize_classic_inventory.py** with **`--idps-inventory`** — present network + IdP briefing in chat.
5. Run **classic_to_hcp.py --dry-run** — present mapping preview (include IdP summary when inventory is present).
6. **Stop and ask** the operator to confirm or change: network mode, VPC CIDR, machine/pod CIDRs, private vs public, AZ layout, target cluster name, infra pools, optional network scope (TGW / SGs / flow logs), **customer VPC endpoints** (include in `network/` or `--skip-endpoints`; **never** adopt ROSA HCP **control-plane VPCE** in `network/`), whether to replicate htpasswd IdPs. **Shared VPC** is out of scope. **Do not run any `--write` or `combine_stack.py` until they answer.**
7. Write `network/` under `[output-dir]` using confirmed flags (pass **`--skip-endpoints`** on **`network_to_tf.py`** when the operator declines customer endpoint adopt).
8. Run **classic_to_hcp.py --write** into the same `[output-dir]` with confirmed flags and **`--idps-json`** when IdPs should be mapped.
9. Run **merge_hcp_stack.py** (split apply) or **combine_stack.py** (copy + single apply) as appropriate.
10. `terraform fmt` + `terraform validate` at the stack root or split directories.
11. Write or update `MIGRATION-FULL.md` (includes IdP section from generator when `--idps-json` was used).

**IdP behavior after `--write`:**

- **htpasswd** — active `identity_providers` in tfvars, `idp_htpasswd.tf` with `random_password` per user (Classic password hashes are not available from OCM).
- **openid / github / gitlab / google / ldap** — commented stubs in `identity_providers_optional.tf`; offer to walk the operator through IdP admin steps (new client/secret, redirect URI `https://oauth-openshift.apps.<apps-domain>/oauth2callback/<idp-name>` once the HCP apps domain is known).

Set `OUTPUT_DIR` from the optional second argument.

## Notes

- Adopt mode + active Classic: network Terraform documents existing VPC; HCP must use **copy** network or wait until Classic is gone before subnet reuse.
- **Shared VPC** and **ROSA HCP control-plane VPCE** adopt are out of scope; **customer** VPC endpoints require an explicit operator choice before network **`--write`**.
- IAM for HCP remains module-managed; Classic IAM is not adopted in v1.
- Anonymized sample output: repo `examples/rosa/classic-to-hcp-full-combined/` (see `examples/README.md`).
