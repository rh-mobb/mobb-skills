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
