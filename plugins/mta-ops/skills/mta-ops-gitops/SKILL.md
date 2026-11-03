---
name: mta-ops-gitops
description: |
  Package mta-ops rendered manifests into a Git repository as Kustomize, with an Argo CD Application or ApplicationSet.

  Use when:
  - Putting a migrated namespace into OpenShift GitOps or another Argo CD
  - Creating a new Git repository for an application, or adding the app to a repository the user already has
  - Choosing an Application versus an ApplicationSet for one or many destinations
  - The rendered manifests are in an mta-ops output directory and need a GitOps layout

  NOT for: running export, transform, or transfer-pvc (use the mta-ops skill). NOT for applying manifests with oc or kubectl.
license: Apache-2.0
metadata:
  user_invocable: "false"
  model: inherit
  color: "#ee0000"
---

# MTA Ops GitOps

Take the rendered manifests from an `mta-ops` migration directory and write them into a Git repository as a Kustomize app, plus the Argo CD object that syncs that app. This skill writes files. It does not `oc apply`, `git commit`, or `git push` unless the user asks for that step.

Manifests come from `<migration-dir>/output/resources/`, produced by `/mta-ops:stage` or the staging half of `/mta-ops:migrate`. When that directory is missing, stop and run `/mta-ops:stage` first.

## Ask which repository

Ask this before creating directories or writing files. One question, then wait:

> Use an existing Git repository, or create a new one?

**New repository.** Ask for the directory path. Then:

```bash
mkdir -p "$REPO_DIR"
git init -b main "$REPO_DIR"
```

Do not add a remote, create a GitHub repository, or push. `targetRevision` is `main`.

**Existing repository.** Tell the user to clone it and reply with the directory path. Wait. Do not clone unless the user tells you to run `git clone`. When they hand back a path, require all of these:

```bash
git -C "$REPO_DIR" rev-parse --is-inside-work-tree
git -C "$REPO_DIR" remote get-url origin
git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD
```

Use that `origin` URL as `repoURL` and that branch as `targetRevision`. When `origin` is missing, ask for the URL the Application will sync. Do not invent an org or a repository name.

When `apps/` or `gitops/applications/` already exists, put the new app in that layout. When several app roots exist, ask which one to use. When `apps/<app>` already exists, stop and ask before replacing files.

## What gets written

Default layout when the repository has no app layout yet:

```text
apps/<app>/
  kustomization.yaml
  namespace/          # namespace-scoped manifests
  cluster/            # only when output/resources/_cluster/ has files
gitops/applications/<app>.yaml
gitops/applicationsets/<app>.yaml   # only for an ApplicationSet
```

`<app>` defaults to the namespace name. Ask before using a different name.

Copy YAML from `output/resources/<namespace>/` into `apps/<app>/namespace/`, and from `output/resources/_cluster/` into `apps/<app>/cluster/`. Skip every `Secret`, including dockercfg and ServiceAccount token secrets. List the skipped Secret names for the user and leave them out of `kustomization.yaml`. Do not commit those files. Point the user at Sealed Secrets or External Secrets for that data.

`kustomization.yaml` lists the copied files and nothing else:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - namespace/Deployment_apps_v1_guestbook_frontend.yaml
  - namespace/Service__v1_guestbook_frontend.yaml
```

Build it and confirm the objects match `output/output.yaml` except for the skipped Secrets:

```bash
oc kustomize apps/<app>
```

`kubectl kustomize` is the same build when `oc` is absent.

## Application or ApplicationSet

| Situation | Write |
|---|---|
| One destination cluster and one namespace | `Application` |
| Two or more destination clusters, or the same app in two or more namespaces | `ApplicationSet` with a list generator, one element per destination |
| The repository already syncs this app through an ApplicationSet | Add an element to that ApplicationSet. Do not add a second Application for the same app. |

OpenShift GitOps watches `openshift-gitops`. Use another namespace only when the user names one.

One destination, Argo CD running on that cluster:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: guestbook
  namespace: openshift-gitops
spec:
  project: default
  source:
    repoURL: https://github.com/example/guestbook.git
    targetRevision: main
    path: apps/guestbook
  destination:
    server: https://kubernetes.default.svc
    namespace: guestbook
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

`destination.server` is the URL Argo CD has registered for the cluster. `https://kubernetes.default.svc` means the cluster where that Argo CD is installed. For any other cluster, ask the user for the server URL stored on the Argo CD cluster secret. Do not paste the kubeconfig API URL in unless the user says Argo CD uses that same URL.

Several destinations:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: guestbook
  namespace: openshift-gitops
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]
  generators:
    - list:
        elements:
          - cluster: east
            url: https://kubernetes.default.svc
            namespace: guestbook
          - cluster: west
            url: https://api.west.example.com:6443
            namespace: guestbook
  template:
    metadata:
      name: guestbook-{{.cluster}}
    spec:
      project: default
      source:
        repoURL: https://github.com/example/guestbook.git
        targetRevision: main
        path: apps/guestbook
      destination:
        server: "{{.url}}"
        namespace: "{{.namespace}}"
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
```

Cluster-scoped objects in `cluster/` sync only when the Argo CD project allows cluster resources. Say so when that directory is non-empty. A non-admin stage that used `--skip-cluster-scoped` has no `cluster/` directory. Leave it out.

Show the tree, the skipped Secrets, and whether the object is an Application or an ApplicationSet. Stop. Commit and push only when the user asks. Apply the Application to the cluster only when the user asks.
