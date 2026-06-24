# OCM Plugin

Claude Code plugin for OpenShift Cluster Manager (OCM) operations.

## Features

- Key Authentication — Login, logout, and profile management
- Search Cluster Management — List, describe, create, and delete clusters
- Robot AI Reference — Full OCM CLI reference skill for AI-assisted operations

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
