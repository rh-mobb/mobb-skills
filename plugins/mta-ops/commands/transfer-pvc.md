---
description: Copy one PVC's data from a source kube context to a destination kube context.
argument-hint: <pvc-name> [source-namespace] [source-context] [destination-context]
---

## Name

mta-ops:transfer-pvc

## Synopsis

```
/mta-ops:transfer-pvc <pvc-name> [source-namespace] [source-context] [destination-context]
```

## Description

Copies volume data for one PersistentVolumeClaim with `mta-ops transfer-pvc`. Creates a destination PVC, an rsync daemon, a Route or Ingress, and a source rsync client. Does not edit workload manifests.

Follow the `mta-ops` skill for the flag table, indirect cloud transfer, and StatefulSet StorageClass limits.

## Implementation

**Step 1: Binary**

```bash
command -v mta-ops
mta-ops version
```

When `mta-ops` is missing, stop. Tell the user to download **Migration Toolkit Ops CLI** from https://developers.redhat.com/products/mta/download and put `mta-ops` on `PATH`.

**Step 2: Identify the volume**

Collect source context, destination context, source PVC name, destination PVC name, source namespace, destination namespace, and destination StorageClass. When a value is missing, ask. List classes before choosing one:

```bash
oc --context "$TARGET_CONTEXT" get storageclass
oc --context "$SOURCE_CONTEXT" -n "$SRC_NS" get pvc "$SRC_PVC" \
  -o jsonpath='{.spec.storageClassName}{"\n"}{.spec.resources.requests.storage}{"\n"}'
```

When the source StorageClass name is absent on the destination, `--dest-storage-class` is required. On OpenShift and ROSA the endpoint is `route`.

**Step 3: Confirm**

Repeat the contexts, PVC mapping, namespace mapping, StorageClass, and endpoint. State that the command creates Pods and a Route or Ingress on the destination, and reads the source volume. Wait for an explicit yes. Ask whether writers on the source PVC are scaled to zero. Do not scale workloads unless the user asks for that.

Run from a directory that does not contain a `plugins/` tree. The directory from `/mta-ops:stage` or `/mta-ops:migrate` is the right place.

**Step 4: Transfer**

```bash
mta-ops transfer-pvc \
  --source-context "$SOURCE_CONTEXT" \
  --destination-context "$TARGET_CONTEXT" \
  --pvc-name "$SRC_PVC:$DEST_PVC" \
  --pvc-namespace "$SRC_NS:$DEST_NS" \
  --dest-storage-class "$DEST_STORAGE_CLASS" \
  --endpoint route \
  --verify
```

Use a single PVC name when the destination name matches the source. Pass `--cloud-storage` and an rclone config when the clusters have no route to each other. Do not pass `--upload-only` or `--download-only` unless `mta-ops transfer-pvc --help` lists them.

**Step 5: Report**

Report success or the Pod and Route errors. When the StorageClass changed and a StatefulSet owns the PVC, say that `volumeClaimTemplates` were not updated and that the StatefulSet has to be recreated with `--cascade=orphan` before scale-up.
