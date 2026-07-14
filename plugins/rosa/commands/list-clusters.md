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
