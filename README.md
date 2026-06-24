# mobb-skills

[![skillsaw grade](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Frh-mobb%2Fmobb-skills%2Fmain%2F.skillsaw-badge.json)](https://skillsaw.org/)

Claude Code plugin marketplace for the MOBB (Managed OpenShift Black Belt) team.

[Discover available plugins](https://rh-mobb.github.io/mobb-skills/)

## Installation

### Add the Marketplace

```bash
/plugin marketplace add rh-mobb/mobb-skills
```

### Install a Plugin

```bash
/plugin install ocm@mobb-skills
```

### Use Commands

```bash
/ocm:whoami
```

## Updating Plugins

```bash
/plugin marketplace update mobb-skills
/plugin install ocm@mobb-skills
```

### Auto-Sync on Session Start

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

See [AGENTS.md](AGENTS.md) for plugin development guidelines.

Before opening a PR, run `make lint` locally.
