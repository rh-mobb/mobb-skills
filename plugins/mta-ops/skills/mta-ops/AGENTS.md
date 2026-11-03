# mta-ops Skill — Developer Reference

This skill was built from the installed `mta-ops` binary (Konveyor Crane, shipped as the Migration Toolkit for Applications Ops CLI) and the Crane source tree. For major updates (new subcommands, flag changes, plugin optionals), clone the reference first:

```bash
git clone https://github.com/konveyor/crane references/crane
```

The reference is gitignored. Do not commit it.

The product binary is `mta-ops`. Upstream Crane's command name is `crane` (`Use` is `filepath.Base(os.Args[0])`). Document the installed binary, not every command on Crane `main`.

## When to load the reference

- Adding coverage for a new `mta-ops` subcommand
- Reconciling the skill against a new MTA Ops CLI release
- Verifying behavior that `--help` does not state (directory layout, plugin discovery, whiteouts)

## Key paths in the reference

| Path | What to find there |
|---|---|
| `main.go` | Commands wired into the binary. MTA 8.3.0 ships export, transform, apply, validate, transfer-pvc, and version. `main` also wires convert, tunnel-api, skopeo-sync-gen, and plugin-manager; leave those out until `mta-ops --help` lists them. |
| `cmd/export/export.go` | Export flags, namespace check, Forbidden handling |
| `cmd/export/gk_filter.go` | `--include-gk` / `--exclude-gk` format. The two flags are mutually exclusive. |
| `cmd/transform/transform.go` | Stage selection, default priority assignment (alphabetical, start at 10, step 5) |
| `internal/plugin/plugin_helper.go` | Plugin search order. `./plugins` (cwd) is always scanned, then `--plugin-dir`, then the system plugin dirs. |
| `cmd/transfer-pvc/transfer-pvc.go` | PVC transfer flags. Compare each flag to `mta-ops transfer-pvc --help` before documenting it. |
| `cmd/validate/validate.go` | Live vs `--api-resources` offline validation |
| `docs/commands/` | Narrative for directory layout and pipeline order |

## Checking the installed version

```bash
mta-ops version
```

This skill was written against crane 8.3.0 (`registry.redhat.io/mta/mta-rsync-transfer-rhel9:8.3.0` as the transfer image default). Plugin optionals were captured with `mta-ops transform optionals` run from a directory that does not contain a `plugins/` folder.

If `mta-ops version` reports a different crane version, re-run `--help` and `mta-ops transform optionals` before editing flag tables. Crane `main` is ahead of the 8.3.0 product binary.
