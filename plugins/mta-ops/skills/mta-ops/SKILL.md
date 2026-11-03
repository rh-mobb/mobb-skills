---
name: mta-ops
description: |
  Reference for the Migration Toolkit for Applications Ops CLI (`mta-ops`): namespace export, transform, manifest render, target-API validation, and PVC data transfer.

  Use when:
  - Migrating an OpenShift or Kubernetes namespace between clusters, including PVC data
  - Staging that migration (export, transform, render, validate) without writing to the target
  - Exporting live namespace objects, transforming them, or validating rendered manifests
  - Copying PVC data with `mta-ops transfer-pvc`
  - `mta-ops` is missing from PATH
  - Transform fails while scanning a local `plugins/` directory
  - Choosing transform plugins, stage order, registry replacement, or a destination StorageClass

  NOT for: source-code analysis or the `mta` analysis CLI. NOT for ROSA or ARO cluster lifecycle.
license: Apache-2.0
metadata:
  user_invocable: "false"
  model: inherit
  color: "#ee0000"
---

# MTA Ops CLI (`mta-ops`)

`mta-ops` is the Migration Toolkit for Applications Ops CLI. The binary is Konveyor Crane. It reconstructs redeployable manifests from a running namespace and can copy PVC bytes between kube contexts. It does not change the source cluster during export, transform, render, or validate.

Written against crane **8.3.0** (`mta-ops version`, transfer image `registry.redhat.io/mta/mta-rsync-transfer-rhel9:8.3.0`). When `mta-ops version` reports a different crane version, run `mta-ops <command> --help` and follow that text. Leave out flags that help does not list. Upstream Crane `main` has extra commands (`plugin-manager`, `convert`, `tunnel-api`, `skopeo-sync-gen`) and extra `transfer-pvc` flags (`--upload-only`, `--download-only`) that this 8.3.0 binary does not ship.

The analysis CLI is a different binary named `mta`. Do not substitute it.

## Install

```bash
command -v mta-ops || echo "MISSING"
mta-ops version
```

When `mta-ops` is not on `PATH`, stop and tell the user to download **Migration Toolkit Ops CLI** from https://developers.redhat.com/products/mta/download. That page also lists the analysis CLI (`Migration Toolkit CLI`, hundreds of MB). The Ops CLI archives are about 30 MB and are labeled **Migration Toolkit Ops CLI**. A Red Hat Developer login is required. After unpacking, the `mta-ops` binary has to be on `PATH`. Do not invent a `brew` formula or a GitHub release URL.

## Working directory

Run every `mta-ops` command from a dedicated migration directory, one namespace per directory:

```bash
mkdir -p "$HOME/mta-migrations/<namespace>"
cd "$HOME/mta-migrations/<namespace>"
```

Plugin discovery always walks `./plugins` under the current directory, then `--plugin-dir` (default `$HOME/.local/share/crane/plugins`), then `/usr/local/share/crane/plugins` and `/usr/share/crane/plugins`. Executable files under `./plugins` are launched as plugins. A repo whose `plugins/` tree holds scripts fails with `unable to run the plugin binary`. Built-in plugins do not need files on disk. Run `mta-ops transform list-plugins` from the migration directory, not from a checkout that contains `plugins/`.

Every invocation appends a JSON-lines audit log at `audit/.crane-audit.log` in the working directory (override with `--audit-log`). `export/`, `transform/`, `output/`, `validate/`, and `audit/` contain live cluster data, including Secret contents. Do not commit them.

## Pipeline

`/mta-ops:stage` stops after validate. `/mta-ops:migrate` continues through target apply, PVC byte copy, and scale-up. `/mta-ops:transfer-pvc` copies one volume on its own.

```text
export → transform → mta-ops apply → validate     ← /mta-ops:stage stops here
        → oc apply → transfer-pvc → scale up       ← /mta-ops:migrate continues
```

| Step | Command | Cluster effect |
|---|---|---|
| 1 | `mta-ops export` | Read-only API list. Writes `export/`. |
| 2 | `mta-ops transform` | Local only. Writes `transform/<priority>_<Plugin>/`. |
| 3 | `mta-ops apply` | Local only. Embedded kustomize writes `output/`. Does not contact a cluster. |
| 4 | `mta-ops validate` | Reads the target API, or an offline API-surface file. Does not create objects. |
| 5 | `oc apply` / `kubectl apply` | Creates objects on the target. `/mta-ops:migrate` runs this after validate exits 0. |
| 6 | `mta-ops transfer-pvc` | Copies each PVC's bytes onto the target. Creates rsync Pods and a Route or Ingress. |
| 7 | `oc scale` | Restores replica counts recorded during transform. |

`mta-ops apply` is a local render. The name does not mean `kubectl apply`. When source context, target context, or namespace was inferred, repeat the three values and wait for a yes before step 5. When the user passed all three, print them and continue. Do not apply to the source context. A failing validate report stops the migrate before step 5.

Global flags on every command:

| Flag | Default | Role |
|---|---|---|
| `--debug` | false | Print more logs on stderr |
| `-f, --flags-file` | | YAML of flag names. Explicit flags override the file. |
| `--audit-log` | `audit/.crane-audit.log` | Audit log path |

Standard kube client flags (`--kubeconfig`, `--context`, `-n/--namespace`, `--as`, `--token`, `--insecure-skip-tls-verify`, and the rest of the kubectl set) are on `export` and `validate`.

## Export

```bash
mta-ops export --context "$SOURCE_CONTEXT" -n "$NAMESPACE" --export-dir export
```

Namespace is required. Empty namespace returns `namespace must be set (use -n/--namespace or your kubeconfig context default)`. A missing namespace returns `namespaces "<name>" not found`. A Forbidden `get` on the Namespace is a warning; export continues.

Layout:

```text
export/resources/<namespace>/*.yaml
export/resources/<namespace>/_cluster/    # related ClusterRole, ClusterRoleBinding, SCC, CRD
export/failures/<namespace>/              # list errors
```

Filenames look like `Kind_group_version_namespace_name.yaml`. Core group has an empty group segment (`Service__v1_<ns>_<name>.yaml`).

| Flag | Default | Role |
|---|---|---|
| `-e, --export-dir` | `export` | Output directory. Refuses to overwrite unless `--overwrite`. |
| `-l, --label-selector` | | Limit namespace objects. |
| `--include-gk` | | Repeatable `Kind` or `Group/Kind`. Kind alone matches every group. |
| `--exclude-gk` | | Same format. Mutually exclusive with `--include-gk`. |
| `--crd-skip-group` | | Repeatable API group to omit when collecting CRDs. |
| `--crd-include-group` | | Repeatable API group to collect even when Crane treats it as built-in. |
| `-q, --qps` / `-b, --burst` | 100 / 1000 | API client rate. |
| `--as-extras` | | `key=a,b;key2=c`. Requires `--as` or `--as-group`. |
| `--overwrite` | false | Replace an existing export directory. |

Export records related cluster-scoped objects (CRDs for custom resources in the namespace, ClusterRoles bound to ServiceAccounts in the namespace, SCCs the workload uses). A CRD is left out of the export when it is OLM-managed, labeled `app.kubernetes.io/managed-by`, annotated `operators.operatorframework.io/*`, or has an owner reference. Install that operator on the target instead of copying the CRD. Forbidden list calls are recorded and skipped. Export exits non-zero when every namespace list returns Forbidden.

PVCs are exported as manifests. Volume bytes stay on the source disk until `transfer-pvc`.

## Transform

```bash
mta-ops transform \
  --export-dir export \
  --transform-dir transform \
  10_KubernetesPlugin \
  20_OpenShiftPlugin
```

`export-dir` must already exist. Each stage is `<priority>_<Name>`. A name ending in `Plugin` runs that plugin. Any other name copies resources through for hand edits and refuses to overwrite those edits unless `--overwrite`.

A bare `mta-ops transform` with an empty transform directory creates one stage per discovered plugin, sorted by plugin name, priorities 10, 15, 20, …. On this binary that order is `10_BuildConfigToBuildsPlugin`, `15_KubernetesPlugin`, `20_OpenShiftPlugin`. Pass stages explicitly so `KubernetesPlugin` runs first, and omit `BuildConfigToBuildsPlugin` unless the user asked to convert BuildConfigs into Shipwright Builds.

| Flag | Default | Role |
|---|---|---|
| `-e, --export-dir` | `export` | Exported manifests. |
| `-t, --transform-dir` | `transform` | Stage directories. |
| `--instructions-file` | | YAML stage list. Mutually exclusive with positional stages and with `--stage-optionals`. |
| `--optional-flags` | | JSON object passed to every plugin. |
| `--stage-optionals` | | Repeatable `StageName={"flag":"value"}`. |
| `--kustomize-args` | | Extra args for embedded kustomize, for example `--enable-helm --helm-command=helm3`. |
| `--overwrite` | false | Rewrite a stage that has user edits. |
| `-p, --plugin-dir` | `$HOME/.local/share/crane/plugins` | Extra plugin binaries. Persistent on `list-plugins` and `optionals`. |
| `-s, --skip-plugins` | | Comma-separated plugin names to drop from discovery. |

Instructions file (single YAML document, only key `stages`):

```yaml
stages:
  - 10_KubernetesPlugin
  - name: 20_OpenShiftPlugin
    optionals:
      registry-replacement: "docker-registry.default.svc:5000=image-registry.openshift-image-registry.svc:5000"
```

Each stage directory holds `input/` (grouped manifests), `patches/`, `new/` (resources the plugin created), `output/` (input to the next stage), and `kustomization.yaml`. Whiteouts are resources excluded from later stages. In `kustomization.yaml` they are commented lines under a `# Whiteout` header (`# - input/...`). Owned Pods are whiteouts by default. PVCs with an owner reference are whiteouts. Review those comments before render, because a whiteout resource will be absent from `output/`.

Renaming a namespace does not rewrite ClusterRoleBinding subjects or NetworkPolicy `namespaceSelector` entries that match the old namespace label (`kubernetes.io/metadata.name`). Edit those in a pass-through stage before render.

### Bundled plugins

`mta-ops transform list-plugins` from a clean directory:

| Plugin | Version | Run it when |
|---|---|---|
| `KubernetesPlugin` | v0.0.10 | Always. Strips `uid`, `resourceVersion`, `creationTimestamp`, `managedFields`, and `status`. |
| `OpenShiftPlugin` | v0.1.0 | Source is OpenShift. Routes, ImageStreams, default ServiceAccounts, pull secrets. |
| `BuildConfigToBuildsPlugin` | v0.11.0 | User asked to convert BuildConfigs to Shipwright Builds. Otherwise leave it out. |

Refresh optionals with `mta-ops transform optionals` after a version change. Values below are from crane 8.3.0.

**KubernetesPlugin**

| Optional | Example | Effect |
|---|---|---|
| `add-annotations` | `ann=value,ann2=value2` | Annotations added to each resource |
| `remove-annotations` | `ann1,ann2` | Annotations removed |
| `registry-replacement` | `docker.io/foo=quay.io/bar` | Image registry prefix swap |
| `pvc-rename-map` | `old:new,old2:new2` | PVC renames |
| `pvc-storage-class-map` | `gp2:gp3-csi` | StorageClass on PVCs and StatefulSet `volumeClaimTemplates` |
| `whiteout-pvc` | `true` | Drop PVCs that have no owner reference. Owned PVCs are already whiteouts. |
| `downscale-workloads` | `true` | Scale PVC-consuming workloads to zero and store the old replica count in annotations |
| `extra-whiteouts` | `Deployment.apps,Service` | Additional GroupKinds to exclude |
| `include-only` | `Deployment.apps,Service` | Everything else becomes a whiteout. Ignores `extra-whiteouts`. |
| `strip-default-rbac` | `true` (default) | Drop default ServiceAccount RBAC |
| `strip-default-cabundle` | `true` (default) | Drop the default CA bundle |
| `disable-whiteout-owned` | `true` | Keep owned Pods and pod templates |

**OpenShiftPlugin**

| Optional | Example | Effect |
|---|---|---|
| `registry-replacement` | `docker-registry.default.svc:5000=image-registry.openshift-image-registry.svc:5000` | Image prefix swap |
| `pull-secret-replacement` | `default-dockercfg-OLD=default-dockercfg-NEW` | Pod and BuildConfig pull-secret names |
| `pvc-rename-map` | `old:new` | PVC renames |
| `strip-default-rbac` | `true` (default) | Drop builder/deployer ServiceAccounts and the default admin, builder, and deployer bindings |
| `strip-default-cabundle` | `true` (default) | Drop the default CA bundle |
| `strip-default-pull-secrets` | `true` (default) | Drop `builder-dockercfg-*`, `default-dockercfg-*`, and `deployer-dockercfg-*` secrets that `pull-secret-replacement` does not map |

**BuildConfigToBuildsPlugin**

| Optional | Example | Effect |
|---|---|---|
| `registry-mapping` | `image-registry.openshift-image-registry.svc:5000=quay.io/myorg` | Registry prefix on generated Builds |
| `imagestream-mapping` | `myns/mystream:latest=quay.io/myorg/myimage:latest` | ImageStreamTag, ImageStreamImage, or local lookupPolicy names to concrete image URLs |
| `default-build-strategy` | `docker=buildah-with-volumes,s2i=source-to-image-with-volumes` | ClusterBuildStrategy copies |
| `search-registries` | `docker.io,quay.io` | Buildah search registries |
| `insecure-registries` | `my-registry.local:5000` | HTTP or self-signed registries |
| `block-registries` | `docker.io` | Buildah blocked registries |

Set `registry-replacement` and `pvc-storage-class-map` from values the user supplies. Read the source image prefixes from the export and the destination StorageClasses with `oc --context "$TARGET_CONTEXT" get storageclass`. Do not invent either map.

## Apply (local render)

```bash
mta-ops apply --transform-dir transform --output-dir output --ordered
```

| Flag | Default | Role |
|---|---|---|
| `-t, --transform-dir` | `transform` | Stage directories |
| `-o, --output-dir` | `output` | Rendered manifests. Refuses to overwrite unless `--overwrite`. |
| `--skip-cluster-scoped` | false | Omit ClusterRole, ClusterRoleBinding, CRD, and other cluster-scoped objects. Use when the target identity is not cluster-admin. |
| `--ordered` | false | Prefix files with `300_Role_`, `310_RoleBinding_`, and similar so `oc apply -f` on the directory respects dependencies. |
| `--kustomize-args` | | Same form as transform |
| `--overwrite` | false | Replace `output/` |

Output:

```text
output/output.yaml                         # one multi-doc file
output/resources/<namespace>/*.yaml
output/resources/_cluster/*.yaml           # omitted with --skip-cluster-scoped
```

Positional args limit which stages render (`mta-ops apply 10_KubernetesPlugin`). With no args, every discovered stage renders in priority order.

## Validate

```bash
mta-ops validate --context "$TARGET_CONTEXT" --input-dir output --validate-dir validate
```

Checks each manifest `apiVersion` + `kind` against the target API (strict GVK). Exit 0 means every GVK is served. Exit 1 means a mismatch or another error. Mismatches land in `validate/failures/`. The report is `validate/report.json` (or `report.yaml` with `--output yaml`).

| Flag | Default | Role |
|---|---|---|
| `-i, --input-dir` | `output` | Rendered manifests |
| `--validate-dir` | `validate` | Report and failures. Refuses to overwrite unless `--overwrite`. |
| `-o, --output` | `json` | `json` or `yaml` |
| `--api-resources` | | Offline API surface file. Mutually exclusive with `--context`, `--kubeconfig`, `--server`, `--token`, `--cluster`, and `--user`. |
| `--overwrite` | false | Replace `validate/` |

Offline capture from a machine that can reach the target:

```bash
kubectl api-versions --context "$TARGET_CONTEXT" | while read gv; do
  endpoint="/apis/$gv"
  [ "$gv" = "v1" ] && endpoint="/api/v1"
  kubectl get --raw "$endpoint" --context "$TARGET_CONTEXT" 2>/dev/null || true
done | jq -s '{"apiResourceLists":.}' > api-surface.json

mta-ops validate --api-resources api-surface.json --input-dir output
```

A failed GVK means the target is missing that CRD or operator, or the manifest still uses an API version the target removed. Fix the target or add a transform stage. Do not `oc apply` over a failing report unless the user accepts the specific failures.

## GitOps

To put the rendered manifests in a Git repository and add an Argo CD Application or ApplicationSet, use the `mta-ops-gitops` skill (`/mta-ops:gitops`). That skill writes files in git. It does not apply them to a cluster.

## Deploy and copy

`/mta-ops:stage` ends at validate. `/mta-ops:migrate` then:

1. Creates the target namespace when it is missing.
2. Applies `output/output.yaml` to the target context.
3. Runs `transfer-pvc` once per PersistentVolumeClaim in `output/resources/`.
4. Scales those workloads back to `crane.konveyor.io/original-replicas`.

For that sequence, transform with `downscale-workloads` so PVC-consuming Deployments, StatefulSets, ReplicaSets, and ReplicationControllers render at 0 replicas. The annotation stores the previous count. This changes the rendered YAML only. It does not scale the source cluster.

```bash
mta-ops transform \
  --export-dir export \
  --transform-dir transform \
  --stage-optionals 'KubernetesPlugin={"downscale-workloads":"true"}' \
  10_KubernetesPlugin \
  20_OpenShiftPlugin
```

DeploymentConfigs are outside that plugin. Before `oc apply`, set `spec.replicas` to 0 on any rendered DeploymentConfig that mounts a migrated PVC and store the old count in the same annotation.

Apply the manifests, then copy bytes. An existing destination PVC is reused when it is not mounted and its StorageClass matches `--dest-storage-class`. Omit `--dest-storage-class` when the rendered PVC already has the destination class, including after `pvc-storage-class-map`. A mounted destination PVC fails with `destination PVC ... is in use by pod`.

```bash
oc --context "$TARGET_CONTEXT" apply -f output/output.yaml
```

Use `--context` on the target, never the source. For a non-admin target, render with `--skip-cluster-scoped` and apply the namespace objects the user can create.

After each transfer, scale the workload back:

```bash
oc --context "$TARGET_CONTEXT" -n "$NAMESPACE" scale deploy/"$NAME" --replicas "$REPLICAS"
```

Use `deploy`, `statefulset`, or `dc` to match the object. Read `$REPLICAS` from `crane.konveyor.io/original-replicas`.

The source keeps serving during the copy, so the result is crash-consistent. Scale source writers to zero only when the user asks for a quiesced copy.

## Transfer PVC data

Manifest migration does not copy volume data. `transfer-pvc` creates the destination PVC (unless it already exists), an rsync daemon Pod, an endpoint, and a source rsync client Pod. The link uses a self-signed certificate the command generates.

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

`--pvc-name` is required. Mapping form is `<source>:<destination>`. A single name uses that name on both sides. Same rule for `--pvc-namespace`. When `--pvc-namespace` is set, namespaces on the kube contexts are ignored. Same context and same namespace require different PVC names.

| Flag | Default | Role |
|---|---|---|
| `--source-context` / `--destination-context` | | Kubeconfig context names |
| `--pvc-name` | required | `<source>` or `<source>:<destination>` |
| `--pvc-namespace` | context namespace | `<source>` or `<source>:<destination>` |
| `--dest-storage-class` | source PVC's class | Class that exists on the destination. Required when the source class name is absent there. |
| `--dest-storage-requests` | source capacity | Destination request, for example `20Gi` |
| `--endpoint` | `nginx-ingress` | `route` on OpenShift. `nginx-ingress` requires `--subdomain` and `--ingress-class`. |
| `--source-image` / `--destination-image` | `registry.redhat.io/mta/mta-rsync-transfer-rhel9:8.3.0` | Rsync transfer image. Read the default from `--help` when the crane version is not 8.3.0. |
| `--verify` | false | Checksum verification |
| `--output` | | Write transfer stats to this file |
| `--cloud-storage` | | Indirect transfer through an S3-compatible rclone path (`remote:bucket`) when the clusters cannot reach each other |
| `--rclone-config-file` | | Local `rclone.conf`. The command creates temporary Secrets. |
| `--rclone-config-secret` | | Existing Secret name that holds `rclone.conf` |
| `--encrypt` | false | Client-side encryption for indirect transfer |
| `--keep-cloud-data` | false | Leave the object in cloud storage after the transfer |

On OpenShift and ROSA use `--endpoint route`. List destination classes before choosing one:

```bash
oc --context "$TARGET_CONTEXT" get storageclass
oc --context "$SOURCE_CONTEXT" -n "$SRC_NS" get pvc "$SRC_PVC" -o jsonpath='{.spec.storageClassName}{"\n"}'
```

`transfer-pvc` does not edit a StatefulSet `volumeClaimTemplates`. After a StorageClass change, delete the StatefulSet with `--cascade=orphan` and recreate it with the new `storageClassName` before scaling up. New replicas otherwise keep the old class.

`/mta-ops:migrate` renders PVC-consuming Deployments and StatefulSets at 0 replicas via `downscale-workloads` and scales them up after the copy. The annotation is `crane.konveyor.io/original-replicas`. Source workloads stay at their current replica count unless the user asks to quiesce them.

Indirect mode (`--cloud-storage`) uploads from the source and downloads to the destination in one invocation, so this process needs credentials for both contexts. This 8.3.0 binary has no `--upload-only` or `--download-only`.

## Failures

| Message | What to do |
|---|---|
| `command not found: mta-ops` | Send the user to https://developers.redhat.com/products/mta/download for **Migration Toolkit Ops CLI**. |
| `unable to run the plugin binary` | The cwd `plugins/` directory is not a Crane plugin dir. `cd` to the migration directory and rerun. |
| `namespace must be set` | Pass `-n`. |
| `namespaces "<name>" not found` | Fix the name or the `--context`. |
| `export directory "..." already exists` | Pass `--overwrite` or pick a new `--export-dir`. Same pattern for `output/` and `validate/`. |
| `cannot use both --include-gk and --exclude-gk` | Pass one of them. |
| `export-dir "..." does not exist` | Run export first. |
| `contains user modifications` | Keep the edits, or rerun that stage with `--overwrite`. |
| validate exit 1 | Read `validate/report.json` and `validate/failures/`. Install the missing CRD or operator, or change the manifest API version. |
| `destination PVC ... is in use by pod` | A target pod has the claim mounted. Scale that workload to 0, rerun `transfer-pvc`, then restore replicas from `crane.konveyor.io/original-replicas`. |
| transfer Pod pending | Check image pull of `mta-rsync-transfer-rhel9`, Route admission, and that the destination StorageClass exists. |

## When a flag is rejected

Stop. Run `mta-ops <command> --help`. Use the flag names printed there. Update this skill with the correction before retrying a guessed flag.
