# OCM Plugin

Claude Code plugin for OpenShift Cluster Manager (OCM) operations.

## Features

- 🔑 **Authentication** — Login, logout, and profile management
- 🔍 **Cluster Management** — List, describe, create, and delete clusters
- 🤖 **AI Reference** — Full OCM CLI reference skill for AI-assisted operations

## Prerequisites

- `ocm` CLI installed: `brew install ocm` (macOS) or [GitHub releases](https://github.com/openshift-online/ocm-cli/releases)
- OCM token from https://console.redhat.com/openshift/token

## Installation

```bash
/plugin marketplace add rh-mobb/mobb-skills
/plugin install ocm@mobb-skills
```

## Commands

| Command | Description |
|---------|-------------|
| `/ocm:whoami` | Show current OCM user and environment |

## Skills

- **ocm-cli** — Comprehensive OCM CLI reference, automatically loaded when you work with OCM/clusters

## Cursor Install

Skills work in Cursor as-is — commands are Claude Code only.

```bash
mkdir -p ~/.cursor/skills/ocm-cli
cp plugins/ocm/skills/ocm-cli/SKILL.md ~/.cursor/skills/ocm-cli/
```

Restart Cursor. The `ocm-cli` skill auto-invokes whenever you work with OCM or clusters.
