---
description: Delete a ROSA cluster and clean up its operator roles and OIDC provider.
argument-hint: <cluster-name-or-id>
---

## Name

rosa:delete-cluster

## Synopsis

```
/rosa:delete-cluster <cluster>
```

## Description

Deletes a ROSA cluster and performs standard post-delete cleanup (operator roles, OIDC provider). Does NOT remove infrastructure resources like VPCs, NAT gateways, EFS, S3 buckets, or IAM account roles. For full infrastructure teardown, use the `rosa-purge-cluster-resources` skill.

## Implementation

**Step 0: Auth / profile setup**

Follow the profile resolution process from the rosa-cli skill.

**Step 1: Describe the cluster and confirm identity**

```bash
CLUSTER="<CLUSTER>"
CLUSTER_JSON=$(rosa describe cluster --cluster "${CLUSTER}" --output json)
NAME=$(echo "$CLUSTER_JSON" | jq -r '.name')
ID=$(echo "$CLUSTER_JSON" | jq -r '.id')
STATE=$(echo "$CLUSTER_JSON" | jq -r '.state')
REGION=$(echo "$CLUSTER_JSON" | jq -r '.region.id')
IS_HCP=$(echo "$CLUSTER_JSON" | jq -r '.hypershift.enabled // false')
OIDC_ENDPOINT=$(echo "$CLUSTER_JSON" | jq -r '.aws.sts.oidc_endpoint_url // empty')
OIDC_CONFIG_ID=$(echo "${OIDC_ENDPOINT}" | grep -oP '(?<=oidc\.op1\.openshiftapps\.com/)[^/]+' || true)
INFRA_ID=$(echo "$CLUSTER_JSON" | jq -r '.infra_id // empty')
```

If `rosa describe` fails, the cluster may already be deleted. Inform the operator and suggest `rosa-purge-cluster-resources` if orphaned AWS resources need cleanup.

**Step 2: Confirm with operator**

Present cluster details and ask for explicit confirmation before proceeding:

```
## About to delete cluster: <NAME> (<ID>)

State:    <STATE>
Region:   <REGION>
Type:     <HCP if IS_HCP == true, else Classic>
OIDC ID:  <OIDC_CONFIG_ID>

This will delete the cluster and its control plane. Operator roles and
OIDC provider will be removed after the cluster is fully uninstalled.

Proceed? (requires explicit yes)
```

Do NOT proceed without explicit operator confirmation.

**Step 3: Delete the cluster**

Use tmux for this long-running operation (20–45 min; longer with bare-metal nodes).

```bash
rosa delete cluster --cluster "${NAME}" -y --watch 2>&1 | tee "${HOME}/${NAME}-rosa-delete.log"
```

Save the full output — it contains the OIDC config ID and operator role prefix needed for Step 4.

If delete fails or stalls:
1. Read the log tail for the blocking resource.
2. Retry once without flags.
3. Only with operator approval: `rosa delete cluster --cluster "${NAME}" -y --best-effort --watch`

**Step 4: Verify cluster is gone**

```bash
rosa list clusters | grep -w "${NAME}" || echo "Cluster deleted successfully"
```

Wait until the cluster no longer appears or shows a terminal state.

**Step 5: Clean up operator roles and OIDC provider**

Use `--mode auto` to avoid interactive prompts.

```bash
rosa delete operator-roles --prefix "${NAME}" --mode auto -y
rosa delete oidc-provider --oidc-config-id "${OIDC_CONFIG_ID}" --mode auto -y
```

If `OIDC_CONFIG_ID` was not captured, check the delete log from Step 3 — ROSA prints cleanup commands at deletion time. The OIDC config ID is the path segment after `oidc.op1.openshiftapps.com/`.

**Step 6: Report**

```
## Cluster deletion complete: <NAME>

- Cluster:        deleted
- Operator roles: deleted (prefix: <NAME>)
- OIDC provider:  deleted (id: <OIDC_CONFIG_ID>)

Note: VPC, NAT gateways, EFS, S3 buckets, IAM account roles, and other
infrastructure resources were NOT removed. If these need cleanup, use
the rosa-purge-cluster-resources skill.
```

## Notes

- This command only handles the ROSA cluster and its directly associated STS artifacts. It mirrors `rosa delete cluster` + the cleanup commands ROSA prints at deletion time.
- Account-level IAM roles (installer, support, worker, control-plane) are intentionally NOT deleted — they are typically shared across clusters.
- If the cluster was provisioned with Terraform or another IaC tool, prefer that tool's destroy workflow when state is available.
- For full infrastructure teardown (VPC, NAT, EFS, S3, Secrets Manager, etc.), use the `rosa-purge-cluster-resources` skill after this command completes.
