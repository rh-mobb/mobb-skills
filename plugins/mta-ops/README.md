# MTA Ops Plugin

Claude Code plugin for the Migration Toolkit for Applications Ops CLI (`mta-ops`). It migrates a namespace from one Kubernetes or OpenShift cluster to another: export live objects, transform them, render manifests, validate them against the target API, and copy PVC data.

This is the Ops CLI (about 30 MB). The separate Migration Toolkit CLI (`mta`, about 700 MB) analyzes source code. This plugin does not cover `mta`.

## Prerequisites

`mta-ops` on `PATH`. If `command -v mta-ops` fails, download **Migration Toolkit Ops CLI** from https://developers.redhat.com/products/mta/download (Red Hat Developer login). Pick the archive for this OS and architecture, unpack it, and put the `mta-ops` binary on `PATH`.

A kubeconfig with a context for the source cluster and a context for the target cluster.

## Installation

```bash
/plugin marketplace add rh-mobb/mobb-skills
/plugin install mta-ops@mobb-skills
```

## Commands

| Command | Description |
|---------|-------------|
| `/mta-ops:stage` | Export, transform, render, and validate one namespace. Writes nothing to the target. |
| `/mta-ops:migrate` | Stage the namespace, apply it to the target, copy every PVC, and scale workloads back up. |
| `/mta-ops:transfer-pvc` | Copy one PVC's data from a source context to a destination context. |

## Skills

- **mta-ops** — Command reference for the installed Ops CLI, including bundled transform plugins and the `plugins/` working-directory trap.
