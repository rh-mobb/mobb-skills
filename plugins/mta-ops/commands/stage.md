---
description: Export a namespace, transform it, render manifests, and validate them against the target cluster.
argument-hint: <namespace> [source-context] [target-context]
---

## Name

mta-ops:stage

## Synopsis

```
/mta-ops:stage <namespace> [source-context] [target-context]
```

## Description

Prepares one namespace for migration and stops before anything is created on the target. Runs export, transform, local render, and validation. To apply the manifests and copy PVC data, use `/mta-ops:migrate`.

Follow the `mta-ops` skill for flags, plugin optionals, and the `plugins/` working-directory rule.

## Implementation

**Step 1: Binary**

```bash
command -v mta-ops
mta-ops version
```

When `mta-ops` is missing, stop. Tell the user to download **Migration Toolkit Ops CLI** from https://developers.redhat.com/products/mta/download and put `mta-ops` on `PATH`. Do not use the analysis CLI named `mta`.

**Step 2: Contexts and namespace**

```bash
oc config get-contexts
```

Use the namespace and contexts from the arguments. When either context is omitted, ask the user which context is the source and which is the target.

**Step 3: Working directory**

```bash
mkdir -p "$HOME/mta-migrations/<namespace>"
cd "$HOME/mta-migrations/<namespace>"
```

Do not run `mta-ops` from a checkout that contains a `plugins/` directory.

**Step 4: Export**

```bash
mta-ops export --context "$SOURCE_CONTEXT" -n "$NAMESPACE" --export-dir export
```

Report resource counts and anything under `export/failures/`. Export is a read-only API list.

**Step 5: Transform**

For an OpenShift source, pass stages so Kubernetes cleanup runs first and BuildConfig conversion stays out:

```bash
mta-ops transform \
  --export-dir export \
  --transform-dir transform \
  10_KubernetesPlugin \
  20_OpenShiftPlugin
```

For a plain Kubernetes source, pass only `10_KubernetesPlugin`. Add `30_BuildConfigToBuildsPlugin` only when the user asked to convert BuildConfigs to Shipwright Builds.

Add `--optional-flags` or `--stage-optionals` for registry prefixes and StorageClass names the user provided. Read source image prefixes from the export. List destination StorageClasses before writing `pvc-storage-class-map`.

Show whiteout comments (`# Whiteout` in each stage `kustomization.yaml`) and say which kinds were dropped.

**Step 6: Render**

```bash
mta-ops apply --transform-dir transform --output-dir output --ordered
```

`mta-ops apply` writes files under `output/`. It does not contact a cluster. Add `--skip-cluster-scoped` when the target identity is not cluster-admin.

**Step 7: Validate**

```bash
mta-ops validate --context "$TARGET_CONTEXT" --input-dir output --validate-dir validate
```

Exit 0 means every GVK is served by the target. On exit 1, summarize `validate/report.json`.

**Step 8: Stop**

Summarize the migration directory, both contexts, the namespace, validation, and how many PersistentVolumeClaims are in `output/resources/`. Do not `oc apply` and do not `transfer-pvc`. Tell the user `/mta-ops:migrate` applies the manifests and copies the volume data.
