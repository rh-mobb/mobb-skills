# ocm-cli Skill — Developer Reference

This skill was built from the OpenShift Cluster Manager CLI source. For major updates (new subcommands, API changes, flag changes), clone the reference first:

```bash
git clone https://github.com/openshift-online/ocm-cli references/ocm-cli
```

The reference is gitignored. Do not commit it.

## When to load the reference

- Adding coverage for a new `ocm` subcommand
- Reconciling the skill against a new OCM CLI release
- Verifying exact flag names or output formats before updating SKILL.md

## Key paths in the reference

| Path | What to find there |
|---|---|
| `cmd/ocm/` | All subcommands — one directory per command group |
| `cmd/ocm/cluster/` | Cluster lifecycle commands (create, describe, hibernate, etc.) |
| `cmd/ocm/login/` | Login flow, token and client-credentials auth |
| `pkg/config/` | Config file location logic (`OCM_CONFIG` env var, default path) |
| `pkg/output/` | Output formatting — JSON vs table, YAML table definitions |
| `CHANGES.md` | Release history — scan this first to see what changed in a new version |

## Checking the installed version

```bash
ocm version
```

Compare against the latest release tag at https://github.com/openshift-online/ocm-cli/releases to determine whether the skill needs reconciliation.
