# ROSA CLI Commands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three ROSA-native commands (`rosa:whoami`, `rosa:list-clusters`, `rosa:cluster-describe`) to the `rosa` plugin so customers using only the `rosa` CLI can describe and list their clusters.

**Architecture:** Each command is a standalone Markdown file in `plugins/rosa/commands/` following the established pattern — YAML frontmatter, Name/Synopsis/Description/Implementation/Notes sections. Commands reference the `rosa-cli` skill for auth/profile setup. No new skills or MCP servers are needed.

**Tech Stack:** Markdown command files, `rosa` CLI, `jq`

## Global Constraints

- All files go in `plugins/rosa/commands/`
- Frontmatter must have `description:` and `argument-hint:` fields
- Commands reference the `rosa-cli` skill for auth — do not re-document auth inline beyond a "Step 0" pointer
- Classic vs HCP branching required in `cluster-describe` (machine pools vs node pools; upgrade-policies vs upgrades)
- Empty sections show "None" — never silently omit
- `make lint` must pass after each task
- Bump `version` in `plugins/rosa/.claude-plugin/plugin.json` in the final task

---

### Task 1: `rosa:whoami`

**Files:**
- Create: `plugins/rosa/commands/whoami.md`

- [ ] **Step 1: Create the command file**

Write `plugins/rosa/commands/whoami.md` with this exact content:

```markdown
---
description: Show the currently authenticated ROSA user and account details.
argument-hint: ""
---

## Name

rosa:whoami

## Synopsis

```
/rosa:whoami
```

## Description

Displays the identity of the currently authenticated ROSA user: username, organization, account ID, and API endpoint. Useful to confirm which account is active before running cluster operations.

## Implementation

**Step 0: Auth / profile setup**

Follow the profile resolution process from the rosa-cli skill. The `rosa` CLI reads credentials from `$OCM_CONFIG` (default: `~/.config/ocm/ocm.json`). To use a non-default profile:

```bash
export OCM_CONFIG="$HOME/.config/ocm/<profile-name>.json"
```

**Step 1: Run whoami**

```bash
rosa whoami
```

**Step 2: Present**

Pass the output through as-is — `rosa whoami` output is already human-readable. Append the active `OCM_CONFIG` path so the user knows which profile is in use:

```
<rosa whoami output>

Active profile: /Users/<user>/.config/ocm/ocm.json
```

If `rosa whoami` fails with a credentials error, instruct the user to log in:

```bash
rosa login --token <token>
# Get token at: https://console.redhat.com/openshift/token
```
```

- [ ] **Step 2: Run lint**

```bash
make lint
```

Expected: no errors on the new file.

- [ ] **Step 3: Commit**

```bash
git add plugins/rosa/commands/whoami.md
git commit -m "feat(rosa): add rosa:whoami command"
```

---

### Task 2: `rosa:list-clusters`

**Files:**
- Create: `plugins/rosa/commands/list-clusters.md`

- [ ] **Step 1: Create the command file**

Write `plugins/rosa/commands/list-clusters.md` with this exact content:

```markdown
---
description: List all ROSA clusters for the logged-in user.
argument-hint: ""
---

## Name

rosa:list-clusters

## Synopsis

```
/rosa:list-clusters
```

## Description

Lists all ROSA clusters accessible to the currently authenticated user. Scope is limited to clusters within your OCM organization's subscription — this command cannot list clusters across other organizations. For cross-organization listing, use the `ocm` CLI with a privileged Red Hat account.

## Implementation

**Step 0: Auth / profile setup**

Follow the profile resolution process from the rosa-cli skill.

**Step 1: List clusters**

```bash
rosa list clusters --output json
```

**Step 2: Parse and present**

Extract and display as a sorted table:

```bash
echo "$CLUSTERS_JSON" | jq -r '
  .items // [] |
  sort_by(.name) |
  .[] |
  [
    .name,
    .id,
    .state,
    (.version.raw_id // .openshift_version // "—"),
    (.region.id // "—"),
    (if .hypershift.enabled then "HCP" else "Classic" end)
  ] | @tsv
'
```

Present as:

```
## ROSA Clusters

| Name | ID | State | Version | Region | Type |
|---|---|---|---|---|---|
| my-cluster | abc123… | ready | 4.16.12 | us-east-1 | Classic |
| my-hcp     | def456… | ready | 4.17.3  | us-east-1 | HCP    |

Total: 2 clusters
```

If no clusters are returned, say: `No ROSA clusters found for the active account.`

## Notes

- `rosa list clusters` is scoped to clusters within your OCM organization's subscription. It does not use the cross-organization visibility available to privileged Red Hat accounts via the `ocm` CLI.
- To filter by state, pipe through `jq 'select(.state == "ready")'`.
```

- [ ] **Step 2: Run lint**

```bash
make lint
```

Expected: no errors on the new file.

- [ ] **Step 3: Commit**

```bash
git add plugins/rosa/commands/list-clusters.md
git commit -m "feat(rosa): add rosa:list-clusters command"
```

---

### Task 3: `rosa:cluster-describe`

**Files:**
- Create: `plugins/rosa/commands/cluster-describe.md`

- [ ] **Step 1: Create the command file**

Write `plugins/rosa/commands/cluster-describe.md` with this exact content:

```markdown
---
description: Describe a ROSA cluster in detail — metadata, machine/node pools, IDPs, ingresses, and upgrade policies.
argument-hint: <cluster-name-or-id>
---

## Name

rosa:cluster-describe

## Synopsis

```
/rosa:cluster-describe <cluster>
```

## Description

Provides a comprehensive description of a ROSA cluster using only the `rosa` CLI: basic metadata, identity providers, machine pools (Classic) or node pools (HCP), ingresses, and upgrade policies. Works for ROSA Classic and ROSA HCP clusters.

## Implementation

**Step 0: Auth / profile setup**

Follow the profile resolution process from the rosa-cli skill.

**Step 1: Describe the cluster and detect type**

```bash
CLUSTER_JSON=$(rosa describe cluster --cluster "<CLUSTER>" --output json)
NAME=$(echo "$CLUSTER_JSON" | jq -r '.name')
ID=$(echo "$CLUSTER_JSON" | jq -r '.id')
STATE=$(echo "$CLUSTER_JSON" | jq -r '.state')
VERSION=$(echo "$CLUSTER_JSON" | jq -r '.version.raw_id // .openshift_version // "—"')
REGION=$(echo "$CLUSTER_JSON" | jq -r '.region.id // "—"')
CLOUD=$(echo "$CLUSTER_JSON" | jq -r '.cloud_provider.id // "—"')
NETWORK=$(echo "$CLUSTER_JSON" | jq -r '.network.type // "—"')
IS_HCP=$(echo "$CLUSTER_JSON" | jq -r '.hypershift.enabled // false')
```

**Step 2: Present basic cluster info**

```
## Cluster: <NAME> (<ID>)

State:    <STATE>
Version:  <VERSION>
Region:   <REGION>
Cloud:    <CLOUD>
Network:  <NETWORK>
Type:     <HCP if IS_HCP == true, else Classic>
```

**Step 3: Pools (branch on type)**

*Classic (`IS_HCP == false`):*

```bash
rosa list machinepools --cluster "<CLUSTER>" --output json
```

Parse and present:

```
## Machine Pools

| ID | Instance Type | Replicas | Autoscale | AZ(s) |
|---|---|---|---|---|
| worker | m5.xlarge | 3 | No | us-east-1a, us-east-1b |
```

*HCP (`IS_HCP == true`):*

```bash
rosa list nodepools --cluster "<CLUSTER>" --output json
```

Parse and present:

```
## Node Pools

| ID | Instance Type | Replicas | Autoscale | AZ |
|---|---|---|---|---|
| workers | m5.xlarge | 2 | No | us-east-1a |
```

For autoscaling pools, show the min–max range in the Replicas column (e.g., `2–5`) and `Yes` in Autoscale.

If no pools are found: `None`

**Step 4: Identity providers**

```bash
rosa list idps --cluster "<CLUSTER>"
```

Present as:

```
## Identity Providers

| Name | Type |
|---|---|
| htpasswd | HTPasswd |
```

If none: `None`

**Step 5: Ingresses**

```bash
rosa list ingresses --cluster "<CLUSTER>"
```

Present as:

```
## Ingresses

| ID | DNS Name | Default | Private |
|---|---|---|---|
| apps | *.apps.my-cluster.example.com | Yes | No |
```

If none: `None`

**Step 6: Upgrade policies / scheduled upgrades (branch on type)**

*Classic (`IS_HCP == false`):*

```bash
rosa list upgrade-policies --cluster "<CLUSTER>"
```

*HCP (`IS_HCP == true`):*

```bash
rosa list upgrades --cluster "<CLUSTER>"
```

Present available or scheduled upgrades. If none: `None`

## Notes

- If `rosa describe cluster` is ambiguous (multiple clusters share the name), `rosa` will prompt for disambiguation. Prefer passing the cluster ID to avoid this.
- Machine pool autoscaling fields: Classic uses `min_replicas`/`max_replicas`; HCP uses `min_replica`/`max_replica` (singular).
- `rosa list upgrade-policies` shows scheduled automatic upgrades for Classic; `rosa list upgrades` shows available upgrade versions for HCP.
- This command only works for ROSA Classic and ROSA HCP. It does not support OSD, ARO, or self-managed OCP clusters.
```

- [ ] **Step 2: Run lint**

```bash
make lint
```

Expected: no errors on the new file.

- [ ] **Step 3: Commit**

```bash
git add plugins/rosa/commands/cluster-describe.md
git commit -m "feat(rosa): add rosa:cluster-describe command"
```

---

### Task 4: Bump plugin version and update description

**Files:**
- Modify: `plugins/rosa/.claude-plugin/plugin.json`

- [ ] **Step 1: Update plugin.json**

Current content:
```json
{
  "name": "rosa",
  "description": "ROSA cost estimation, comparison, and optimization for Classic and HCP clusters.",
  "version": "0.5.0",
  "author": {
    "name": "github.com/rh-mobb"
  }
}
```

Update to:
```json
{
  "name": "rosa",
  "description": "ROSA cluster management, cost estimation, comparison, and optimization for Classic and HCP clusters.",
  "version": "0.6.0",
  "author": {
    "name": "github.com/rh-mobb"
  }
}
```

- [ ] **Step 2: Run lint and update docs**

```bash
make lint
make update
```

Expected: lint passes, docs regenerated.

- [ ] **Step 3: Commit**

```bash
git add plugins/rosa/.claude-plugin/plugin.json
git commit -m "chore(rosa): bump version to 0.6.0, broaden plugin description"
```

- [ ] **Step 4: Push**

```bash
git push origin main
```
