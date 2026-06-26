---
description: Describe a cluster in detail — basic info, identity providers, and machine/node pools.
argument-hint: <cluster-name-or-id>
---

## Name

ocm:cluster-describe

## Synopsis

```
/ocm:cluster-describe <cluster>
```

## Description

Provides a full description of a cluster: basic metadata, identity providers, and machine pools (Classic) or node pools (HCP). Works for ROSA Classic, ROSA HCP, and OSD clusters. For ARO and self-managed OCP clusters, only basic metadata is shown — pool and IDP data is not available via the OCM API for those types.

## Implementation

**Step 0: Profile setup**

Follow the profile resolution process from the ocm-cli skill.

**Step 1: Describe the cluster and detect type**

```bash
CLUSTER_JSON=$(ocm describe cluster "<CLUSTER>" --json)
INTERNAL_ID=$(echo "$CLUSTER_JSON" | jq -r '.id')
PRODUCT=$(echo "$CLUSTER_JSON" | jq -r '.product.id')
IS_HCP=$(echo "$CLUSTER_JSON" | jq -r '.hypershift.enabled // false')
CLOUD=$(echo "$CLUSTER_JSON" | jq -r '.cloud_provider.id')
MANAGED=$(echo "$CLUSTER_JSON" | jq -r '.managed')
STATE=$(echo "$CLUSTER_JSON" | jq -r '.state')
REGION=$(echo "$CLUSTER_JSON" | jq -r '.region.id // "—"')
VERSION=$(echo "$CLUSTER_JSON" | jq -r '.version.raw_id // .openshift_version // "unknown"')
NAME=$(echo "$CLUSTER_JSON" | jq -r '.name')
SUB_ID=$(echo "$CLUSTER_JSON" | jq -r '.subscription.id')
```

**Step 2: Resolve creator via subscription**

```bash
SUB_JSON=$(ocm get /api/accounts_mgmt/v1/subscriptions/"$SUB_ID")
CREATOR_ID=$(echo "$SUB_JSON" | jq -r '.creator.id // "—"')

# Attempt to resolve account to a name (only succeeds if creator == current user)
CREATOR_NAME=$(ocm get /api/accounts_mgmt/v1/accounts/"$CREATOR_ID" 2>/dev/null \
  | jq -r 'if .username then "\(.first_name) \(.last_name) (\(.username) / \(.email))" else empty end')
```

If `CREATOR_NAME` is empty (access denied — creator is a different user), use the account ID only.

**Step 3: Present basic cluster info (always)**

```
## Cluster: <NAME> (<INTERNAL_ID>)

Product:  <PRODUCT> / <CLOUD>   (managed: <MANAGED>)
Type:     <Classic | HCP>
State:    <STATE>
Region:   <REGION>
Version:  <VERSION>
Creator:  <CREATOR_NAME if resolved, else CREATOR_ID>
```

**Step 3: Branch on product type**

- If `PRODUCT` is `aro` or `ocp` → print the following notice and stop:

  ```
  ℹ ARO and self-managed OCP clusters are registered in OCM for subscription
    tracking only. Identity provider and pool data are not available via the
    OCM API for this cluster type.
  ```

- If `PRODUCT` is `rosa` or `osd` → continue to Steps 5 and 6.

**Step 5: Identity providers**

```bash
ocm list idp --cluster "$INTERNAL_ID"
```

Present as:

```
## Identity Providers
| Name | Type |
|---|---|
| htpasswd | HTPasswd |
```

If the list is empty, print: `No identity providers configured.`

**Step 6: Machine pools (Classic) or node pools (HCP)**

Determine which API to use from `IS_HCP`:

*Classic (`IS_HCP == false`):*

```bash
ocm get /api/clusters_mgmt/v1/clusters/"$INTERNAL_ID"/machine_pools \
  | jq -r '.items[] | [
      .id,
      .instance_type,
      (if .autoscaling then "\(.autoscaling.min_replicas)–\(.autoscaling.max_replicas) (autoscale)"
       else (.replicas | tostring) end),
      (.availability_zones // [] | join(", "))
    ] | @tsv'
```

*HCP (`IS_HCP == true`):*

```bash
ocm get /api/clusters_mgmt/v1/clusters/"$INTERNAL_ID"/node_pools \
  | jq -r '.items[] | [
      .id,
      .aws_node_pool.instance_type,
      (if .autoscaling then "\(.autoscaling.min_replica)–\(.autoscaling.max_replica) (autoscale)"
       else (.replicas | tostring) end),
      (.availability_zone // "—")
    ] | @tsv'
```

Present as:

```
## Machine Pools          (or Node Pools for HCP)
| Pool ID | Instance Type | Replicas / Range | AZ(s) |
|---|---|---|---|
| worker  | m5.xlarge     | 3                | us-east-1a, us-east-1b |
```

If the list is empty, print: `No pools found.`

## Notes

- `INTERNAL_ID` (from `ocm describe cluster --json | jq -r '.id'`) is required for all raw API calls; it differs from the external UUID shown in the console.
- OSD clusters are fully managed (`managed: true`) and support the same pool and IDP APIs as ROSA.
- For HCP node pools, autoscaling fields are `min_replica`/`max_replica` (singular), not `min_replicas`/`max_replicas` as in Classic machine pools.
- Creator account resolution requires `/api/accounts_mgmt/v1/accounts/<id>`. This succeeds only if the creator is the currently authenticated user — standard tokens cannot read other users' account details. The account ID is always shown regardless.
- If `ocm describe cluster` is ambiguous (multiple clusters share the name), run `ocm list clusters --parameter search="name='<name>'"` to find the correct ID first.
- See the ocm-cli skill's "Cluster Types in OCM" section for the full product/managed matrix.
