---
description: Show the Red Hat organization that owns a given cluster.
argument-hint: <cluster-name-or-id>
---

## Name

ocm:cluster-owner

## Synopsis

```
/ocm:cluster-owner <cluster>
```

## Description

Given a cluster name or ID, resolves and displays the Red Hat organization that owns it. Outputs the org name and org ID — the org ID can be passed directly to `/ocm:org-clusters`.

## Implementation

**Step 0: Profile setup**

Follow the profile resolution process from the ocm-cli skill.

**Step 1: Describe the cluster**

```bash
CLUSTER_JSON=$(ocm describe cluster "<CLUSTER>" --json)
echo "$CLUSTER_JSON" | jq '{cluster_id: .id, cluster_name: .name, product: .product.id, cloud: .cloud_provider.id, managed: .managed, sub_id: .subscription.id}'
```

If `managed` is `false` and `product` is `aro` or `ocp`, OCM has limited data for this cluster (no region, no worker pool details). See the ocm-cli skill's "Cluster Types in OCM" section.

**Step 2: Resolve org via subscription**

`organization.id` is null on the cluster object in practice; use the subscription:

```bash
SUB_ID=$(echo "$CLUSTER_JSON" | jq -r '.subscription.id')
ORG_ID=$(ocm get /api/accounts_mgmt/v1/subscriptions/"$SUB_ID" | jq -r '.organization_id')
```

**Step 3: Resolve org name**

```bash
ORG_NAME=$(ocm get /api/accounts_mgmt/v1/organizations/"$ORG_ID" | jq -r '.name')
```

**Step 4: Present result**

```
Cluster:      <cluster_name> (<cluster_id>)
Product:      <product.id> / <cloud_provider.id>  (managed: true|false)
Organization: <ORG_NAME>
Org ID:       <ORG_ID>
```

Then suggest the follow-up: "Run `/ocm:org-clusters <ORG_ID>` to list all clusters in this organization."

## Notes

- `organization.id` on the cluster object is always null; the subscription → accounts_mgmt path is required.
- The org ID is an opaque alphanumeric string (e.g. `1ZqJNlPOWDeJpX6gVoYXaSGobZ0`), not a UUID.
- If `ocm describe cluster` is ambiguous (multiple clusters with the same name), run `ocm list clusters --parameter search="name='<name>'"` to find the correct ID.
