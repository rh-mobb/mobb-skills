---
name: ocm-cli
description: |
  Reference for using the `ocm` CLI to interact with Red Hat OpenShift Cluster Manager (api.openshift.com).

  Use when:
  - Logging in or out of OCM / obtaining tokens
  - Listing, describing, creating, editing, or deleting clusters via CLI
  - Managing managed service clusters (ROSA, ARO, OSD) from the terminal
  - Running raw OCM API queries (get/post/patch/delete)
  - Managing machine pools, add-ons, IDPs, ingresses, or upgrade policies
  - Scripting or automating OCM operations outside of MCP contexts
  - Juggling multiple OCM environments (production, staging)

  NOT for: MCP-based cluster management → use the cluster-inventory or cluster-creator skills.
license: Apache-2.0
metadata:
  user_invocable: "true"
  model: inherit
  color: "#cc0000"
---

# OCM CLI Reference

`ocm` is the command-line interface for the Red Hat OpenShift Cluster Manager API (`api.openshift.com`). It covers both high-level cluster operations and raw REST API access.

**Config file**: `~/.config/ocm/ocm.json` (macOS: `~/Library/Application Support/ocm/ocm.json`)

**Install**: `brew install ocm` (macOS) or from [GitHub releases](https://github.com/openshift-online/ocm-cli/releases)

## Authentication

```bash
# Login — get your token at https://console.redhat.com/openshift/token
ocm login --token=eyJ...

# Login to a specific environment
ocm login --token=eyJ... --url=https://api.stage.openshift.com

ocm whoami      # show current user
ocm token       # print raw OpenID access token (for use with curl/other tools)
ocm token --payload  # token details as JSON
ocm logout      # remove config file
```

### Multiple Environments / Profiles

Each profile is a separate config file in the default OCM config directory:

| OS | Default config directory |
|----|--------------------------|
| macOS | `$HOME/Library/Application Support/ocm/` |
| Linux | `$HOME/.config/ocm/` |

A profile named `ocm-rh` corresponds to `ocm-rh.json` in that directory.

**Resolving a profile name to a path** — when the user says "use my `ocm-rh` profile":

1. Detect the OS: `uname` returns `Darwin` on macOS, `Linux` on Linux.
2. Build the config directory path from the table above.
3. Append `<profile-name>.json` to get the full path.
4. Set `OCM_CONFIG` to that path for the remainder of the session.

```bash
# macOS — detect and set for the session
export OCM_CONFIG="$HOME/Library/Application Support/ocm/ocm-rh.json"
ocm whoami   # confirm the correct account is active

# Linux
export OCM_CONFIG="$HOME/.config/ocm/ocm-rh.json"
ocm whoami
```

**Switching profiles mid-session**: re-export `OCM_CONFIG` to a different profile path. All subsequent `ocm` commands in that shell will use the new profile.

**Listing available profiles**: profile files are all `*.json` files in the config directory (excluding the default `ocm.json`):
```bash
# macOS
ls "$HOME/Library/Application Support/ocm/"*.json

# Linux
ls ~/.config/ocm/*.json
```

**Keyring storage**: set `OCM_KEYRING=keychain` (macOS), `secret-service` (Linux), or `pass` to store credentials in the OS keyring instead of plain-text.

## Cluster Operations

```bash
ocm list clusters                          # list all clusters
ocm list clusters --parameter search="state='ready'"
ocm describe cluster <NAME|ID>             # show details
ocm describe cluster <NAME|ID> --json      # full JSON output
ocm describe cluster <NAME|ID> --output   # save to cluster-<id>.json

ocm create cluster <name>                  # interactive wizard
ocm create cluster <name> --interactive
ocm create cluster <name> --dry-run        # validate without creating

ocm edit cluster <NAME|ID> --private
ocm edit cluster <NAME|ID> --expiration-time=2h

ocm hibernate cluster <NAME|ID>
ocm resume cluster <NAME|ID>
```

## Self-Improvement Principle

When an OCM command fails or produces unexpected output, **stop and investigate before retrying**:

1. Check the command's help: `ocm <command> --help`
2. Test alternative forms (flags, subcommands, raw API paths)
3. Update this skill with the correct approach
4. Then proceed with the corrected command

Do not guess at flags or retry with minor variations. The fix belongs in the skill so future sessions start with the right command.

## Cluster Types in OCM

OCM tracks several cluster types under the same API. Always check `product.id` and `managed` before assuming a cluster is ROSA:

| `product.id` | `cloud_provider.id` | `managed` | What it is |
|---|---|---|---|
| `rosa` | `aws` | `true` | ROSA Classic — fully managed by Red Hat |
| `rosa` + `hypershift.enabled` | `aws` | `true` | ROSA HCP — managed, hosted control plane |
| `osd` | `aws` / `gcp` | `true` | OpenShift Dedicated |
| `aro` | `azure` | `false` | Azure Red Hat OpenShift — registered in OCM but managed by Microsoft |
| `ocp` | `azure` / `aws` / other | `false` | Self-managed OCP — registered for subscription tracking only |

**ARO and self-managed OCP have very limited OCM data:**
- `region.id` is null (region lives in Azure/cloud, not tracked in clusters_mgmt)
- Cluster name defaults to the Azure resource UUID — no human-readable name
- Machine pools and node pools return no data (Red Hat does not manage the workers)
- `managed: false` — Red Hat does not manage the control plane

When listing an org's clusters (e.g. via `/ocm:org-clusters`), ARO and OCP clusters will appear alongside ROSA clusters. Always filter or flag them separately:

```bash
# ROSA only
ocm get /api/clusters_mgmt/v1/clusters \
  --parameter "search=organization.id='<ORG_ID>' and product.id='rosa'" \
  --parameter "size=100"

# Separate ROSA from non-ROSA in jq
ocm get /api/clusters_mgmt/v1/clusters \
  --parameter "search=organization.id='<ORG_ID>'" \
  --parameter "size=100" \
  | jq -r '.items[] | [.product.id, .cloud_provider.id, .name, .state] | @tsv'
```

## Classic vs HCP Detection

Always use JSON output for cluster describe — it is machine-parseable and avoids fragile text grep:

```bash
# Get internal OCM ID and HCP flag in one call
ocm describe cluster <NAME|EXTERNAL_UUID> --json | jq '{id: .id, hcp: .hypershift.enabled, name: .name}'
```

The `id` field is the **internal OCM ID** — required for all raw API calls below. The external UUID (from telemetry or the console) is what you pass to `ocm describe`; the internal ID is what you pass to the API.

```bash
CLUSTER_JSON=$(ocm describe cluster "$EXTERNAL_UUID" --json)
INTERNAL_ID=$(echo "$CLUSTER_JSON" | jq -r '.id')
IS_HCP=$(echo "$CLUSTER_JSON" | jq -r '.hypershift.enabled // false')
PRODUCT=$(echo "$CLUSTER_JSON" | jq -r '.product.id')
```

- If `PRODUCT != rosa` → ARO, OCP, or OSD; machine/node pool APIs will be empty
- If `IS_HCP == true` → use **NodePool** API (see below)
- Otherwise → use **MachinePool** API

## Resource Management

All resource subcommands take `--cluster <NAME|ID>`:

### Internal vs external cluster ID — IMPORTANT

The `/clusters_mgmt/v1/clusters/<ID>/...` API path requires the **internal OCM ID** — an
opaque alphanumeric string (e.g. `1l5o4lkqqv7qab54gt6imbr225m57efl`). This is **not** the
external UUID shown in `ocm list clusters` output (e.g. `39395241-xxxx-xxxx-xxxx-xxxxxxxxxxxx`).

Passing the external UUID to the API path returns an empty result with no error — it looks
like a permissions problem but is simply the wrong ID. Always resolve the internal ID first:

```bash
# Step 1: resolve internal ID (required before any /clusters/<ID>/... API call)
INTERNAL_ID=$(ocm describe cluster <NAME_OR_EXTERNAL_ID> --json | jq -r '.id')

# Step 2: use internal ID in API path
ocm get /api/clusters_mgmt/v1/clusters/$INTERNAL_ID/machine_pools
```

The `ocm list machinepools --cluster <name>` CLI command does this resolution automatically
(searches subscriptions by name/external_id, then fetches by internal ID). Use it when you
don't need JSON output; use the raw API when you do.

```bash
# Machine pools (Classic clusters only)
# CLI — works with name or external ID, no --json support:
ocm list machinepools --cluster <NAME|EXTERNAL_ID>

# API — JSON output, requires internal ID (see above):
INTERNAL_ID=$(ocm describe cluster <NAME> --json | jq -r '.id')
ocm get /api/clusters_mgmt/v1/clusters/$INTERNAL_ID/machine_pools

# Parse summary (id, instance_type, replicas/autoscaling range):
ocm get /api/clusters_mgmt/v1/clusters/$INTERNAL_ID/machine_pools | \
  jq -r '.items[] | [.id, .instance_type,
    (if .autoscaling then "\(.autoscaling.min_replicas)-\(.autoscaling.max_replicas)"
     else (.replicas | tostring) end)] | @tsv'

# Mutating operations (still use the ocm subcommand):
ocm create machinepool --cluster <NAME> --instance-type=m5.xlarge --replicas=3
ocm edit machinepool --cluster <NAME> <POOL_ID> --replicas=5

# Node pools (HCP clusters only)
# ocm list nodepool does not support --cluster; raw API required.
# Requires internal ID (see above).
INTERNAL_ID=$(ocm describe cluster <NAME> --json | jq -r '.id')
ocm get /api/clusters_mgmt/v1/clusters/$INTERNAL_ID/node_pools
ocm get /api/clusters_mgmt/v1/clusters/$INTERNAL_ID/node_pools/<POOL_ID>

# Parse node pool summary (id, instance_type, replicas/autoscaling, AZ):
# Note: autoscaling fields are min_replica/max_replica (singular) for node pools,
#       vs min_replicas/max_replicas (plural) for machine pools.
ocm get /api/clusters_mgmt/v1/clusters/$INTERNAL_ID/node_pools | \
  jq -r '.items[] | [.id, .aws_node_pool.instance_type,
    (if .autoscaling then "\(.autoscaling.min_replica)-\(.autoscaling.max_replica)"
     else (.replicas | tostring) end),
    .availability_zone] | @tsv'

# Add-ons
ocm list addon --cluster <CLUSTER_ID>

# Identity providers
ocm list idp --cluster <CLUSTER_ID>
ocm create idp --cluster <CLUSTER_ID>

# Ingresses
ocm list ingress --cluster <CLUSTER_ID>

# Upgrade policies
ocm list upgradepolicy --cluster <CLUSTER_ID>
ocm create upgradepolicy --cluster <CLUSTER_ID>
```

## Account & Org Management

```bash
ocm account orgs
ocm account users
ocm account roles
ocm account quota
ocm account status
```

## Raw API Access

Direct access to any endpoint at `api.openshift.com`:

```bash
# GET
ocm get /api/clusters_mgmt/v1/clusters
ocm get /api/clusters_mgmt/v1/clusters/123/credentials

# POST
ocm post /api/clusters_mgmt/v1/clusters < cluster.json
ocm post /api/clusters_mgmt/v1/clusters --body=cluster.json

# PATCH
ocm patch /api/clusters_mgmt/v1/clusters/123 < patch.json

# DELETE
ocm delete /api/clusters_mgmt/v1/clusters/123
ocm delete /api/clusters_mgmt/v1/clusters/123 --parameter "deprovision=false"
```

## Search Syntax

SQL-like `search` parameter on any collection endpoint:

```bash
# By state
ocm get /api/clusters_mgmt/v1/clusters \
  --parameter search="state in ('ready', 'installing')"

# By name pattern
ocm get /api/clusters_mgmt/v1/clusters \
  --parameter search="name like 'prod%'"

# By creation date
ocm get /api/clusters_mgmt/v1/clusters \
  --parameter search="creation_timestamp >= '2024-01-01'"

# Combined conditions
ocm get /api/clusters_mgmt/v1/clusters \
  --parameter search="name like 'prod%' and cloud_provider.id = 'aws'"

# Works on list commands too
ocm list clusters --parameter search="state='ready'"
```

## Common Patterns

```bash
# Extract cluster IDs with jq
ocm get /api/clusters_mgmt/v1/clusters | jq -r '.items[].id'

# Get kubeconfig for a cluster
ocm get /api/clusters_mgmt/v1/clusters/123/credentials \
  | jq -r .kubeconfig > cluster.kubeconfig

# Use token with curl
curl -H "Authorization: Bearer $(ocm token)" \
  https://api.openshift.com/api/clusters_mgmt/v1/clusters

# Custom columns in list output
ocm list clusters --columns "id,name,state,region.id,cloud_provider.id"

# Suppress header row (useful in scripts)
ocm list clusters --no-headers
```

## Configuration

```bash
ocm config get url             # read a config value
ocm config set url https://api.openshift.com  # write a config value
ocm config set pager less      # enable pager for list output
```

## Key Flags

| Flag | Applies to | Purpose |
|------|-----------|---------|
| `--parameter key=value` | any | Query parameters (search, filter, pagination) |
| `--header key=value` | get/post/patch/delete | Custom HTTP headers |
| `--debug` | any | Show raw HTTP requests and responses |
| `--insecure` | login | Disable TLS verification (dev/testing only) |
| `--interactive` | create cluster | Prompt for all options |
| `--dry-run` | create cluster | Validate without creating |
| `--json` | describe cluster | Full JSON output |
| `--no-headers` | list commands | Suppress header row |

## Discovering the API

Before constructing non-trivial API calls, consult the OpenAPI spec — do not guess at endpoint paths or schema fields.

```bash
# List all available services
ocm get /api | jq -r '.services[].id'

# Download a service's OpenAPI spec
ocm get /api/clusters_mgmt/v1/openapi > clusters_mgmt.json

# Check what fields a schema has
jq '.components.schemas.MachinePool.properties | keys' clusters_mgmt.json

# List all paths in a spec
jq -r '.paths | keys[]' clusters_mgmt.json
```

Available services (as of 2026-06): `clusters_mgmt`, `accounts_mgmt`, `service_logs`, `authorizations`, `access_transparency`, `upgrades_info`, `assisted-install`, `connector_mgmt`, `osd_fleet_mgmt`, `rhacs`.

Each exposes its spec at `/api/<service>/v1/openapi` (not all services have an active endpoint).

## Key API Paths

| Path | Purpose |
|------|---------|
| `/api/clusters_mgmt/v1/clusters` | Cluster management (ROSA, ARO, OSD, OCP) |
| `/api/accounts_mgmt/v1/` | Account, org, subscription management |
| `/api/clusters_mgmt/v1/cloud_providers` | Cloud provider and region discovery |
| `/api/service_logs/v1/` | Service logs |

Full API reference: https://api.openshift.com
