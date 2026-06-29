# rosa-cli Skill — Developer Reference

This skill was built from the ROSA CLI source. For major updates (new subcommands, API changes, flag changes), clone the reference first:

```bash
git clone https://github.com/openshift/rosa references/rosa-cli
```

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

```bash
rosa version
```

Compare against https://github.com/openshift/rosa/releases to determine whether the skill needs reconciliation.
