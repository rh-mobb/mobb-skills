---
description: List all clusters belonging to a given Red Hat organization.
argument-hint: <org-id>
---

## Name

ocm:org-clusters

## Synopsis

```
/ocm:org-clusters <org-id>
```

## Description

Lists every cluster in a Red Hat organization, identified by org ID. Combine with `/ocm:cluster-owner` to go from a cluster → org → full fleet.

## Implementation

**Step 0: Profile setup**

Follow the profile resolution process from the ocm-cli skill.

**Step 1: Resolve org name**

```bash
ORG_NAME=$(ocm get /api/accounts_mgmt/v1/organizations/"<ORG_ID>" | jq -r '.name')
echo "Organization: $ORG_NAME"
```

**Step 2: List all clusters**

Use the raw API so that `product.id`, `cloud_provider.id`, and `hypershift.enabled` are all available:

```bash
ocm get /api/clusters_mgmt/v1/clusters \
  --parameter "search=organization.id='<ORG_ID>'" \
  --parameter "size=100" \
  | jq -r '.items[] | [
      .id,
      .name,
      .product.id,
      .cloud_provider.id,
      (if .hypershift.enabled then "HCP" else "Classic" end),
      .state,
      (.region.id // "—")
    ] | @tsv'
```

If the org has more than 100 clusters, paginate with `--parameter "page=2"` until `.size` in the response is less than 100.

**Step 3: Present results**

Split the output into two sections — ROSA clusters first, then non-ROSA:

```
## Clusters — <ORG_NAME>

### ROSA (AWS)
| Cluster ID | Name | Type | State | Region |
|---|---|---|---|---|
| abc123 | my-cluster | Classic | ready | ap-southeast-1 |
| def456 | my-hcp | HCP | ready | ap-southeast-1 |

### Other (ARO / OCP / OSD)
| Cluster ID | Name | Product | Cloud | State |
|---|---|---|---|---|
| ghi789 | 4272bb00-… | aro | azure | ready |
```

Finish with a one-line summary per group. ARO/OCP clusters have limited OCM data: no region, UUID-style names (Azure resource IDs), and no worker node details available via the OCM API.

## Notes

- Org IDs are returned by `/ocm:cluster-owner`.
- `size=100` covers most customer orgs in a single page.
- ARO clusters (`product.id = aro`, `cloud_provider.id = azure`, `managed = false`) register in OCM for subscription tracking only — Red Hat does not manage their control plane or workers.
- Self-managed OCP clusters (`product.id = ocp`) are similarly limited.
- `region.id` is null for ARO/OCP clusters (the region is an Azure/cloud concept not tracked in clusters_mgmt).
- See the ocm-cli skill's "Cluster Types in OCM" section for the full product/managed matrix.
