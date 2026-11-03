---
description: Stage a namespace, apply it to the target cluster, copy every PVC, and scale workloads back up.
argument-hint: <namespace> [source-context] [target-context]
---

## Name

mta-ops:migrate

## Synopsis

```
/mta-ops:migrate <namespace> [source-context] [target-context]
```

## Description

Full namespace cutover. Runs the `/mta-ops:stage` pipeline, applies the rendered manifests to the target, copies every PersistentVolumeClaim with `transfer-pvc`, then restores replica counts. Source workloads stay at their current scale.

Follow the `mta-ops` skill for flags, plugin optionals, and the `plugins/` working-directory rule.

## Implementation

**Step 1: Stage, with workloads held at zero on the target**

Run the `/mta-ops:stage` procedure through validate, with this transform in place of the stage transform when `export/` contains PersistentVolumeClaims:

```bash
mta-ops transform \
  --export-dir export \
  --transform-dir transform \
  --stage-optionals 'KubernetesPlugin={"downscale-workloads":"true"}' \
  10_KubernetesPlugin \
  20_OpenShiftPlugin
```

`downscale-workloads` sets Deployments, StatefulSets, ReplicaSets, and ReplicationControllers that mount a PVC to 0 replicas and stores the old count in `crane.konveyor.io/original-replicas`. It edits the rendered YAML only. Merge any user `registry-replacement` or `pvc-storage-class-map` into that same JSON object.

Before render, set `spec.replicas` to 0 on rendered DeploymentConfigs that mount a migrated PVC and write the old count to that same annotation. DeploymentConfigs are not covered by the plugin.

On validate exit 1, summarize `validate/report.json` and stop. Do not apply and do not transfer.

**Step 2: Cutover checkpoint**

Print source context, target context, namespace, PVC names, and that target PVC workloads will apply at 0 replicas and scale back after the copy. The source stays up, so the copy is crash-consistent.

When the user supplied the namespace and both contexts, continue. When any of the three was inferred, wait for a yes before the next step.

**Step 3: Apply to the target**

```bash
oc --context "$TARGET_CONTEXT" get ns "$NAMESPACE" \
  || oc --context "$TARGET_CONTEXT" create ns "$NAMESPACE"
oc --context "$TARGET_CONTEXT" apply -f output/output.yaml
```

Use the target context. Add nothing to the source cluster.

**Step 4: Copy every PVC**

For each PersistentVolumeClaim file under `output/resources/`:

```bash
mta-ops transfer-pvc \
  --source-context "$SOURCE_CONTEXT" \
  --destination-context "$TARGET_CONTEXT" \
  --pvc-name "$PVC" \
  --pvc-namespace "$NAMESPACE" \
  --endpoint route \
  --verify
```

Run from the migration directory. On OpenShift and ROSA the endpoint is `route`. Omit `--dest-storage-class` when the rendered PVC already names the destination class. Pass it only when the applied claim would otherwise use a class that does not exist on the target. One failure stops the remaining copies. A claim mounted by a pod returns `destination PVC ... is in use by pod`. Scale that workload to 0 and rerun that PVC.

**Step 5: Scale the target back up**

For each workload annotated with `crane.konveyor.io/original-replicas`, scale it to that value on the target context. Use `deploy`, `statefulset`, `rs`, `rc`, or `dc` to match the object.

```bash
oc --context "$TARGET_CONTEXT" -n "$NAMESPACE" scale deploy/"$NAME" --replicas "$REPLICAS"
```

**Step 6: Report**

State the target context, namespace, validation result, which PVCs copied, and which workloads were scaled back. Say that the source was left running. When a StatefulSet StorageClass changed, say `volumeClaimTemplates` must match the new class before scale-up. The transform map `pvc-storage-class-map` does that when it was set before render.
