# mobb-skills

[![skillsaw grade](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Frh-mobb%2Fmobb-skills%2Fmain%2F.skillsaw-badge.json)](https://skillsaw.org/)

AI agent skills for the MOBB (Managed OpenShift Black Belt) team — covering OCM, ROSA, and GitHub workflow.

Works with **Claude Code** (via plugin marketplace) and **any other agent** (Cursor, Windsurf, Codex, etc.) via `npx skills`.

[Discover available plugins](https://rh-mobb.github.io/mobb-skills/)

## Installation

### Any agent (Cursor, Windsurf, Codex, …)

```bash
# All skills, project-level
npx skills add rh-mobb/mobb-skills

# All skills, global
npx skills add -g rh-mobb/mobb-skills

# Single skill
npx skills add rh-mobb/mobb-skills --skill ocm-cli

# List available skills without installing
npx skills add rh-mobb/mobb-skills --list
```

### Claude Code

```bash
/plugin marketplace add rh-mobb/mobb-skills
/plugin install ocm@mobb-skills
```

Claude Code also gets slash commands not available via `npx skills`:

```bash
/ocm:whoami
/rosa:cost
```

## Updating

```bash
# npx skills
npx skills update

# Claude Code
/plugin marketplace update mobb-skills
/plugin install ocm@mobb-skills
```

### Claude Code — Auto-Sync on Session Start

Add to your project's `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "command": "claude plugin marketplace update mobb-skills",
        "timeout": 30000
      }
    ]
  }
}
```

## Contributing

See [AGENTS.md](AGENTS.md) for development guidelines.

Before opening a PR, run `make lint` locally.
