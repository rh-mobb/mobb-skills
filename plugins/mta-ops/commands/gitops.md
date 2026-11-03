---
description: Write rendered mta-ops manifests into a new or existing Git repository as Kustomize, plus an Application or ApplicationSet.
argument-hint: "<namespace> [migration-directory]"
---

## Name

mta-ops:gitops

## Synopsis

```
/mta-ops:gitops [namespace] [migration-directory]
```

## Description

Packages one migrated namespace for OpenShift GitOps or another Argo CD. Asks whether the Git repository already exists. A new repository is `git init`. An existing repository is cloned by the user. Writes Kustomize for the app and either an Application or an ApplicationSet.

Follow the `mta-ops-gitops` skill for the layout, the Secret exclusion, and the Application versus ApplicationSet choice. Follow the `mta-ops` skill when the render is missing.

## Implementation

**Step 1: Rendered manifests**

Resolve the migration directory. The default is `$HOME/mta-migrations/<namespace>`. Require `output/resources/` there. When it is missing, stop and tell the user to run `/mta-ops:stage` first.

**Step 2: Repository**

Ask whether to use an existing Git repository or create a new one. Wait for the answer.

New: ask for a directory, `mkdir -p` it, and `git init -b main` it. Do not add a remote.

Existing: tell the user to clone the repository and send the path. Wait. Do not clone unless they ask you to run `git clone`. Continue only after `git rev-parse --is-inside-work-tree` succeeds in that directory. Read `origin` and the current branch for `repoURL` and `targetRevision`.

**Step 3: Destinations**

Ask for the app name when it differs from the namespace, the Argo CD namespace, and each destination cluster. One destination writes an Application. More than one writes an ApplicationSet. When the repository already has an ApplicationSet for this app, add an element to it.

**Step 4: Write**

Copy namespace manifests into `apps/<app>/namespace/` and cluster-scoped manifests into `apps/<app>/cluster/`. Skip Secrets and list them. Write `kustomization.yaml`. Write `gitops/applications/<app>.yaml` or `gitops/applicationsets/<app>.yaml`. Follow an existing `apps/` or `gitops/` layout when the repository already has one.

```bash
oc kustomize apps/<app>
```

**Step 5: Stop**

Show the tree, the skipped Secrets, and which Argo CD object was written. Do not commit, push, or apply the Application unless the user asks.
