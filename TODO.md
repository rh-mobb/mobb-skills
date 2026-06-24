# TODO

Minor items from initial scaffold review — none are blockers.

## Workflows

- [ ] Add `'.claude-plugin/**'` to `update-docs.yml` path filter so docs regenerate when `marketplace.json` changes without a plugin file change
- [ ] Add a step to the lint workflow that updates `.skillsaw-badge.json` with the actual grade and commits it back (currently requires manual update)

## Plugin Metadata

- [ ] Change `plugins/ocm/.claude-plugin/plugin.json` `author.name` from `"github.com/rh-mobb"` to a friendlier string like `"Red Hat MOBB"`

## skillsaw Config

- [ ] Remove `tmux` from the `mcp-prohibited` allowlist in `.skillsaw.yaml` until a plugin actually bundles it

## Governance

- [ ] Add more team members to `plugins/ocm/OWNERS` to reduce bus-factor (currently only `pczarkow`)
