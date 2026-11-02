---
name: rosa-purge-cluster-resources
description: |
  Use when a ROSA cluster's associated AWS resources need full teardown — VPC,
  NAT gateways, EFS, S3 buckets, IAM roles, Secrets Manager, VPC endpoints,
  and more — especially after Terraform state is lost or a cluster was deleted
  without cleaning up infrastructure. Works whether the cluster is still live,
  mid-uninstall, or already gone. Discovers resources by naming convention and
  AWS tags, not by IaC state.

  NOT for: simple cluster deletion (use /rosa:delete-cluster). NOT for: clusters
  whose IaC state is intact (use the IaC tool's destroy workflow instead).
license: Apache-2.0
metadata:
  user_invocable: "false"
  model: inherit
  color: "#cc0000"
---

# ROSA Cluster Resource Purge

Systematic teardown of all AWS resources associated with a ROSA cluster. Designed for orphaned clusters where IaC state is missing or the cluster has already been deleted, leaving behind infrastructure.

## When to Use

- Terraform state (or other IaC state) is lost, empty, or from a different cluster
- Cluster was deleted but VPC, NAT gateways, EFS, S3, IAM roles remain
- Cluster still exists but normal IaC destroy is unavailable
- Operator wants to clean up a subset of resources (e.g., NAT gateways bleeding cost, but keep IAM roles)

## When NOT to Use

- IaC state is intact — use `terraform destroy` / `make destroy` / equivalent
- Only deleting the cluster itself — use `/rosa:delete-cluster`

## Agent Rules

1. **Operator confirmation required** before ANY destructive step. State the cluster name, region, and what will be deleted.
2. **Inventory first, delete nothing** — run the full discovery phase and present results before any deletion.
3. **Step-by-step** — complete each step's done-when gate before the next. On failure, diagnose and adapt.
4. **Long-running deletes** — use tmux; tee logs to a file the operator can review.
5. **IAM roles are opt-in** — default-named or potentially shared roles are SKIP by default. Only delete with explicit operator selection.
6. **Operator selects scope** — present grouped resources and let the operator choose which groups to delete.

## Variables

Collect these at session start:

```bash
CLUSTER_NAME="<name>"
REGION="<aws-region>"
export AWS_REGION="${REGION}"
```

## Phase 0 — Preflight

| Check | Command | Done when |
|-------|---------|-----------|
| AWS auth | `aws sts get-caller-identity` | Correct account |
| ROSA auth | `rosa whoami` | Succeeds (needed only if cluster is still live) |
| Operator approval | Ask explicitly | Operator confirms they want to inventory and potentially tear down resources |

## Phase 1 — Discovery (Read-Only)

Run ALL discovery steps before presenting results. Nothing is deleted in this phase.

### 1a. Cluster status

Attempt to get cluster details. If the cluster is already deleted, all discovery falls back to tag/name-based lookup.

```bash
CLUSTER_JSON=$(rosa describe cluster --cluster "${CLUSTER_NAME}" --output json 2>/dev/null) || CLUSTER_JSON=""
```

If the cluster exists, extract useful identifiers:

```bash
if [ -n "${CLUSTER_JSON}" ]; then
  CLUSTER_STATE=$(echo "$CLUSTER_JSON" | jq -r '.state')
  MACHINE_CIDR=$(echo "$CLUSTER_JSON" | jq -r '.network.machine_cidr // empty')
  OIDC_ENDPOINT=$(echo "$CLUSTER_JSON" | jq -r '.aws.sts.oidc_endpoint_url // empty')
  OIDC_CONFIG_ID=$(echo "${OIDC_ENDPOINT}" | grep -oP '(?<=oidc\.op1\.openshiftapps\.com/)[^/]+' || true)
  IS_HCP=$(echo "$CLUSTER_JSON" | jq -r '.hypershift.enabled // false')
fi
```

If the cluster is still running, suggest using `/rosa:delete-cluster` first, then returning here for infrastructure cleanup.

### 1b. VPC

```bash
# Primary: by Name tag
VPC_INFO=$(aws ec2 describe-vpcs --region "${REGION}" \
  --filters "Name=tag:Name,Values=${CLUSTER_NAME}-vpc" \
  --query 'Vpcs[].{VpcId:VpcId,Cidr:CidrBlock,Tags:Tags}' --output json)

# Fallback: by CIDR from rosa describe (only if cluster is live)
if [ "$(echo "$VPC_INFO" | jq 'length')" = "0" ] && [ -n "${MACHINE_CIDR:-}" ]; then
  VPC_INFO=$(aws ec2 describe-vpcs --region "${REGION}" \
    --filters "Name=cidr,Values=${MACHINE_CIDR}" \
    --query 'Vpcs[].{VpcId:VpcId,Cidr:CidrBlock,Tags:Tags}' --output json)
fi

VPC_ID=$(echo "$VPC_INFO" | jq -r '.[0].VpcId // empty')
```

If no VPC is found, many subsequent checks will be skipped. Note this in the inventory report.

### 1c. VPC-dependent resources (only if VPC_ID is set)

```bash
echo "=== NAT Gateways ==="
aws ec2 describe-nat-gateways --region "${REGION}" \
  --filter "Name=vpc-id,Values=${VPC_ID}" \
  --query 'NatGateways[?State!=`deleted`].{Id:NatGatewayId,Subnet:SubnetId,State:State}' --output table

echo "=== VPC Endpoints ==="
aws ec2 describe-vpc-endpoints --region "${REGION}" \
  --filters "Name=vpc-id,Values=${VPC_ID}" \
  --query 'VpcEndpoints[].{Id:VpcEndpointId,Service:ServiceName,Type:VpcEndpointType}' --output table

echo "=== Internet Gateway ==="
aws ec2 describe-internet-gateways --region "${REGION}" \
  --filters "Name=attachment.vpc-id,Values=${VPC_ID}" \
  --query 'InternetGateways[].InternetGatewayId' --output text

echo "=== Subnets ==="
aws ec2 describe-subnets --region "${REGION}" \
  --filters "Name=vpc-id,Values=${VPC_ID}" \
  --query 'Subnets[].{Id:SubnetId,AZ:AvailabilityZone,Cidr:CidrBlock}' --output table

echo "=== Security Groups (non-default) ==="
aws ec2 describe-security-groups --region "${REGION}" \
  --filters "Name=vpc-id,Values=${VPC_ID}" \
  --query 'SecurityGroups[?GroupName!=`default`].{Id:GroupId,Name:GroupName}' --output table

echo "=== Network Interfaces ==="
aws ec2 describe-network-interfaces --region "${REGION}" \
  --filters "Name=vpc-id,Values=${VPC_ID}" \
  --query 'NetworkInterfaces[].{Id:NetworkInterfaceId,Type:InterfaceType,Status:Status,Description:Description}' --output table

echo "=== Load Balancers ==="
aws elbv2 describe-load-balancers \
  --query "LoadBalancers[?VpcId=='${VPC_ID}'].{Arn:LoadBalancerArn,Name:LoadBalancerName,Type:Type}" --output table 2>/dev/null || true

echo "=== Route Server (if any) ==="
aws ec2 describe-route-servers --region "${REGION}" \
  --filters "Name=vpc-id,Values=${VPC_ID}" --output table 2>/dev/null || true

echo "=== Client VPN (if any) ==="
aws ec2 describe-client-vpn-endpoints --region "${REGION}" \
  --query "ClientVpnEndpoints[?contains(Description, '${CLUSTER_NAME}') || contains(Tags[?Key=='ClusterName'].Value | [0], '${CLUSTER_NAME}')]" --output table 2>/dev/null || true
```

### 1d. Non-VPC resources

```bash
echo "=== EFS ==="
aws efs describe-file-systems --region "${REGION}" \
  --query "FileSystems[?contains(Name, '${CLUSTER_NAME}')].{Id:FileSystemId,Name:Name,State:LifeCycleState}" --output table

echo "=== S3 Buckets ==="
aws s3api list-buckets \
  --query "Buckets[?contains(Name, '${CLUSTER_NAME}')].Name" --output text

echo "=== Secrets Manager ==="
aws secretsmanager list-secrets --region "${REGION}" \
  --filters Key=name,Values="${CLUSTER_NAME}" \
  --query 'SecretList[].{Name:Name,LastAccessed:LastAccessedDate}' --output table

echo "=== IAM Roles ==="
aws iam list-roles \
  --query "Roles[?starts_with(RoleName, \`${CLUSTER_NAME}\`)].{Name:RoleName,Created:CreateDate}" --output table

echo "=== IAM Policies (customer-managed) ==="
aws iam list-policies --scope Local \
  --query "Policies[?starts_with(PolicyName, \`${CLUSTER_NAME}\`)].{Name:PolicyName,Arn:Arn}" --output table

echo "=== KMS Key Aliases ==="
aws kms list-aliases \
  --query "Aliases[?contains(AliasName, '${CLUSTER_NAME}')].{Alias:AliasName,KeyId:TargetKeyId}" --output table

echo "=== EC2 Instances (bastion, metal) ==="
aws ec2 describe-instances --region "${REGION}" \
  --filters "Name=tag:Name,Values=*${CLUSTER_NAME}*" "Name=instance-state-name,Values=running,stopped" \
  --query 'Reservations[].Instances[].{Id:InstanceId,Type:InstanceType,Name:Tags[?Key==`Name`].Value|[0],State:State.Name}' --output table
```

### 1e. Provenance check (informational)

If a VPC was found, check tags for IaC provenance:

```bash
aws ec2 describe-vpcs --region "${REGION}" --vpc-ids "${VPC_ID}" \
  --query 'Vpcs[0].Tags' --output table
```

Look for `ManagedBy = Terraform` or similar. Note this in the report — if IaC state can be recovered, that's the preferred teardown path.

### 1f. Present inventory to operator

Group the discovered resources and present them as selectable categories:

```
## Resource Inventory for: <CLUSTER_NAME> (region: <REGION>)

### [A] ROSA Cluster
Status: <running | deleted | not found>
Action: <delete via /rosa:delete-cluster | already deleted | N/A>

### [B] VPC Networking                                    $$$ (NAT costs)
VPC:            <VPC_ID> (<CIDR>)
NAT Gateways:   <count> (active — accruing hourly cost)
VPC Endpoints:  <count>
Internet GW:    <id or none>
Subnets:        <count>
Security Groups: <count> (non-default)
Load Balancers: <count or none>

### [C] EFS
Filesystems: <list or none>

### [D] S3 Buckets
Buckets: <list or none>
Note: versioned buckets may take 60-90 min to empty

### [E] Secrets Manager
Secrets: <list or none>

### [F] IAM — Operator Roles + OIDC (ROSA-managed)
Operator roles prefix: <CLUSTER_NAME>
OIDC config ID: <id or unknown>
Action: cleaned up via rosa CLI

### [G] IAM — Infrastructure Roles            ⚠ potentially shared
Roles: <list>
Policies: <list>
⚠ These roles may be shared across clusters if using default naming.
   Default: SKIP. Only delete if operator confirms these are cluster-specific.

### [H] KMS Keys
Aliases: <list or none>
Note: minimum 7-day waiting period for deletion

### [I] Route Server (if found)
<details or "not present">

### [J] Client VPN (if found)
<details or "not present">

### [K] EC2 Instances (bastion, metal nodes)
<list or none>

---
Which groups should I delete? (e.g., "B, C, D, E, F" or "all except G")
```

**Done when:** Operator selects which groups to delete.

## Phase 2 — Delete ROSA Cluster (if still running)

Only if the operator selected group [A] and the cluster is still live.

Follow the `/rosa:delete-cluster` command workflow. Return here after the cluster is fully deleted and operator roles / OIDC are cleaned up.

## Phase 3 — Delete Selected Resource Groups

Process groups in dependency order. Ask for confirmation before each group. Within networking, delete in strict dependency order.

### Group C — EFS

Delete mount targets first, then the filesystem:

```bash
FS_ID="<fs-id>"
for MT in $(aws efs describe-mount-targets --region "${REGION}" --file-system-id "${FS_ID}" \
  --query 'MountTargets[].MountTargetId' --output text); do
  aws efs delete-mount-target --region "${REGION}" --mount-target-id "${MT}"
done
# Poll until mount targets are gone
aws efs delete-file-system --region "${REGION}" --file-system-id "${FS_ID}"
```

**Done when:** `aws efs describe-file-systems --file-system-id "${FS_ID}"` returns not found.

### Group D — S3 Buckets

Control-plane log buckets use versioning. `aws s3 rb --force` stalls on versioned buckets — use batched version-aware deletion. Run in tmux for large buckets (2M+ versions = 60-90 min).

```bash
for BUCKET in $(aws s3api list-buckets --query "Buckets[?contains(Name, '${CLUSTER_NAME}')].Name" --output text); do
  export BUCKET
  python3 <<'PY'
import boto3, os
bucket = os.environ["BUCKET"]
region = os.environ.get("AWS_REGION", "ap-southeast-2")
s3 = boto3.client("s3", region_name=region)
paginator = s3.get_paginator("list_object_versions")
deleted = 0
for page in paginator.paginate(Bucket=bucket):
    objs = [
        {"Key": v["Key"], "VersionId": v["VersionId"]}
        for v in page.get("Versions", []) + page.get("DeleteMarkers", [])
    ]
    for i in range(0, len(objs), 1000):
        batch = objs[i:i+1000]
        if batch:
            s3.delete_objects(Bucket=bucket, Delete={"Objects": batch, "Quiet": True})
            deleted += len(batch)
print(f"deleted {deleted} versions from {bucket}")
s3.delete_bucket(Bucket=bucket)
print("bucket deleted")
PY
done
```

**Done when:** No buckets matching `${CLUSTER_NAME}` remain.

### Group E — Secrets Manager

```bash
for SECRET in $(aws secretsmanager list-secrets --region "${REGION}" \
  --filters Key=name,Values="${CLUSTER_NAME}" \
  --query 'SecretList[].Name' --output text); do
  aws secretsmanager delete-secret --region "${REGION}" \
    --secret-id "${SECRET}" --force-delete-without-recovery
done
```

**Done when:** No secrets matching `${CLUSTER_NAME}` remain.

### Group F — ROSA Operator Roles + OIDC

```bash
rosa delete operator-roles --prefix "${CLUSTER_NAME}" --mode auto -y
rosa delete oidc-provider --oidc-config-id "${OIDC_CONFIG_ID}" --mode auto -y
```

If `OIDC_CONFIG_ID` is unknown (cluster already deleted, no saved describe output), try:

```bash
# Search OIDC providers by URL containing the cluster name or infra ID
aws iam list-open-id-connect-providers --query 'OpenIDConnectProviderList[].Arn' --output text
# Then describe each and match by URL
```

**Done when:** Operator roles with prefix `${CLUSTER_NAME}` are gone and OIDC provider is removed.

### Group K — EC2 Instances

Terminate bastion hosts or other tagged instances before VPC teardown (they hold ENIs):

```bash
for INSTANCE_ID in $(aws ec2 describe-instances --region "${REGION}" \
  --filters "Name=tag:Name,Values=*${CLUSTER_NAME}*" "Name=instance-state-name,Values=running,stopped" \
  --query 'Reservations[].Instances[].InstanceId' --output text); do
  aws ec2 terminate-instances --region "${REGION}" --instance-ids "${INSTANCE_ID}"
done
# Wait for termination
```

**Done when:** No instances with the cluster name tag are running or stopped.

### Group I — Route Server (if selected)

1. Delete route server endpoints for all subnets
2. Disassociate and delete route server VPC association
3. Delete the route server itself

**Done when:** `aws ec2 describe-route-servers --filters Name=vpc-id,Values=${VPC_ID}` returns empty.

### Group J — Client VPN (if selected)

1. Disassociate target networks
2. Delete authorization rules
3. Delete the Client VPN endpoint
4. Delete associated ACM certs / CloudWatch log group if tagged for this cluster

**Done when:** No Client VPN endpoint remains for this cluster.

### Group B — VPC Networking

Delete in strict dependency order. VPC deletion fails if any dependent resource remains.

**B1. Load balancers** (if any were found in the VPC):

```bash
for ARN in $(aws elbv2 describe-load-balancers \
  --query "LoadBalancers[?VpcId=='${VPC_ID}'].LoadBalancerArn" --output text 2>/dev/null); do
  aws elbv2 delete-load-balancer --load-balancer-arn "${ARN}"
done
```

**B2. NAT gateways** (highest cost leak if forgotten):

```bash
for NAT in $(aws ec2 describe-nat-gateways --region "${REGION}" \
  --filter "Name=vpc-id,Values=${VPC_ID}" \
  --query 'NatGateways[?State!=`deleted`].NatGatewayId' --output text); do
  aws ec2 delete-nat-gateway --region "${REGION}" --nat-gateway-id "${NAT}"
done
# Poll every 30s until all show State=deleted
```

**B3. Release Elastic IPs** tied to the NAT gateways:

```bash
aws ec2 describe-nat-gateways --region "${REGION}" \
  --filter "Name=vpc-id,Values=${VPC_ID}" \
  --query 'NatGateways[].NatGatewayAddresses[].AllocationId' --output text | while read -r ALLOC; do
  [ -n "${ALLOC}" ] && aws ec2 release-address --region "${REGION}" --allocation-id "${ALLOC}" 2>/dev/null || true
done
```

**B4. VPC endpoints** (ENIs linger in "deleting" state — must wait):

```bash
for VPCE in $(aws ec2 describe-vpc-endpoints --region "${REGION}" \
  --filters "Name=vpc-id,Values=${VPC_ID}" \
  --query 'VpcEndpoints[].VpcEndpointId' --output text); do
  aws ec2 delete-vpc-endpoints --region "${REGION}" --vpc-endpoint-ids "${VPCE}"
done
# Poll every 15s until describe-vpc-endpoints returns zero
```

Do NOT proceed to VPC deletion until all VPC endpoints are fully deleted — otherwise `delete-vpc` fails with `DependencyViolation`.

**B5. Internet gateway:**

```bash
IGW=$(aws ec2 describe-internet-gateways --region "${REGION}" \
  --filters "Name=attachment.vpc-id,Values=${VPC_ID}" \
  --query 'InternetGateways[0].InternetGatewayId' --output text)
if [ "${IGW}" != "None" ] && [ -n "${IGW}" ]; then
  aws ec2 detach-internet-gateway --region "${REGION}" --internet-gateway-id "${IGW}" --vpc-id "${VPC_ID}"
  aws ec2 delete-internet-gateway --region "${REGION}" --internet-gateway-id "${IGW}"
fi
```

**B6. Security groups** (non-default):

```bash
for SG in $(aws ec2 describe-security-groups --region "${REGION}" \
  --filters "Name=vpc-id,Values=${VPC_ID}" \
  --query 'SecurityGroups[?GroupName!=`default`].GroupId' --output text); do
  aws ec2 delete-security-group --region "${REGION}" --group-id "${SG}" 2>/dev/null || true
done
```

**B7. Lingering network interfaces:**

```bash
for ENI in $(aws ec2 describe-network-interfaces --region "${REGION}" \
  --filters "Name=vpc-id,Values=${VPC_ID}" \
  --query 'NetworkInterfaces[].NetworkInterfaceId' --output text); do
  aws ec2 detach-network-interface --region "${REGION}" \
    --attachment-id "$(aws ec2 describe-network-interfaces --region "${REGION}" \
      --network-interface-ids "${ENI}" --query 'NetworkInterfaces[0].Attachment.AttachmentId' --output text)" \
    --force 2>/dev/null || true
  aws ec2 delete-network-interface --region "${REGION}" --network-interface-id "${ENI}" 2>/dev/null || true
done
```

**B8. Subnets, then VPC:**

```bash
for SUB in $(aws ec2 describe-subnets --region "${REGION}" \
  --filters "Name=vpc-id,Values=${VPC_ID}" \
  --query 'Subnets[].SubnetId' --output text); do
  aws ec2 delete-subnet --region "${REGION}" --subnet-id "${SUB}" 2>/dev/null || true
done
aws ec2 delete-vpc --region "${REGION}" --vpc-id "${VPC_ID}"
```

If `delete-vpc` fails, check for remaining ENIs, security groups, or load balancers and retry.

**Done when:** `aws ec2 describe-vpcs --vpc-ids "${VPC_ID}"` returns invalid VPC ID.

### Group G — Infrastructure IAM Roles (only if explicitly selected)

These roles may use default naming and be shared across clusters. Only proceed if the operator explicitly confirmed these are cluster-specific.

```bash
for ROLE in $(aws iam list-roles \
  --query "Roles[?starts_with(RoleName, \`${CLUSTER_NAME}\`)].RoleName" --output text); do
  echo "Deleting role: ${ROLE}"
  for POLICY_ARN in $(aws iam list-attached-role-policies --role-name "${ROLE}" \
    --query 'AttachedPolicies[].PolicyArn' --output text); do
    aws iam detach-role-policy --role-name "${ROLE}" --policy-arn "${POLICY_ARN}"
  done
  for INLINE in $(aws iam list-role-policies --role-name "${ROLE}" \
    --query 'PolicyNames[]' --output text); do
    aws iam delete-role-policy --role-name "${ROLE}" --policy-name "${INLINE}"
  done
  aws iam delete-role --role-name "${ROLE}" 2>/dev/null || echo "WARN: could not delete ${ROLE}"
done
```

Customer-managed policies:

```bash
for POLICY_ARN in $(aws iam list-policies --scope Local \
  --query "Policies[?starts_with(PolicyName, \`${CLUSTER_NAME}\`)].Arn" --output text); do
  aws iam delete-policy --policy-arn "${POLICY_ARN}" 2>/dev/null || true
done
```

**Done when:** `aws iam list-roles --query "Roles[?starts_with(RoleName, \`${CLUSTER_NAME}\`)]"` returns empty.

### Group H — KMS Keys (if selected)

KMS keys have a minimum 7-day deletion waiting period:

```bash
for ALIAS_INFO in $(aws kms list-aliases \
  --query "Aliases[?contains(AliasName, '${CLUSTER_NAME}')].{Alias:AliasName,KeyId:TargetKeyId}" --output json | jq -c '.[]'); do
  KEY_ID=$(echo "$ALIAS_INFO" | jq -r '.KeyId')
  ALIAS=$(echo "$ALIAS_INFO" | jq -r '.Alias')
  aws kms delete-alias --alias-name "${ALIAS}"
  aws kms schedule-key-deletion --key-id "${KEY_ID}" --pending-window-in-days 7
  echo "Scheduled deletion for key ${KEY_ID} (alias: ${ALIAS}) — 7-day wait"
done
```

**Done when:** All matching aliases deleted and keys scheduled for deletion.

## Phase 4 — Final Verification

Run a sweep across all resource types:

```bash
echo "=== ROSA ===" 
rosa list clusters 2>/dev/null | grep -w "${CLUSTER_NAME}" || echo "  (not listed)"

echo "=== VPC ==="
aws ec2 describe-vpcs --region "${REGION}" \
  --filters "Name=tag:Name,Values=${CLUSTER_NAME}-vpc" \
  --query 'Vpcs[].VpcId' --output text || echo "  (none)"

echo "=== EFS ==="
aws efs describe-file-systems --region "${REGION}" \
  --query "FileSystems[?contains(Name, '${CLUSTER_NAME}')].FileSystemId" --output text

echo "=== S3 ==="
aws s3api list-buckets \
  --query "Buckets[?contains(Name, '${CLUSTER_NAME}')].Name" --output text

echo "=== IAM Roles ==="
aws iam list-roles \
  --query "Roles[?starts_with(RoleName, \`${CLUSTER_NAME}\`)].RoleName" --output text

echo "=== Secrets Manager ==="
aws secretsmanager list-secrets --region "${REGION}" \
  --filters Key=name,Values="${CLUSTER_NAME}" \
  --query 'SecretList[].Name' --output text

echo "=== EC2 Instances ==="
aws ec2 describe-instances --region "${REGION}" \
  --filters "Name=tag:Name,Values=*${CLUSTER_NAME}*" "Name=instance-state-name,Values=running,stopped" \
  --query 'Reservations[].Instances[].InstanceId' --output text
```

Present results. All selected groups should show empty. Any remaining resources should be flagged with suggested manual action.

Recommend the operator spot-check the AWS console: **VPC > NAT gateways**, **EFS**, **EC2 > Instances** (metal/GPU), **IAM > Roles**.

## Common Resource Naming Patterns

Use during discovery when the cluster name alone doesn't find everything.

| Resource type | Naming pattern |
|---------------|---------------|
| VPC | `${CLUSTER_NAME}-vpc` |
| Subnets | `${CLUSTER_NAME}-public-*`, `${CLUSTER_NAME}-private-*` |
| IAM account roles | `${CLUSTER_NAME}-HCP-ROSA-*` |
| IAM operator roles | `${CLUSTER_NAME}-openshift-*`, `${CLUSTER_NAME}-*-operator-*` |
| IAM feature roles | `${CLUSTER_NAME}-rosa-cert-manager`, `${CLUSTER_NAME}-rosa-cloudwatch-*`, `${CLUSTER_NAME}-rosa-secretsmanager-*`, `${CLUSTER_NAME}-rosa-efs-*` |
| IAM bastion/autonode | `${CLUSTER_NAME}-bastion`, `${CLUSTER_NAME}-autonode-*` |
| EFS | `${CLUSTER_NAME}-rosa-efs` |
| S3 | `${CLUSTER_NAME}-control-plane-logs-*` |
| Secrets Manager | `${CLUSTER_NAME}-credentials`, `${CLUSTER_NAME}-bgp-config` |
| KMS aliases | `alias/${CLUSTER_NAME}-*` |
| EC2 instances | `${CLUSTER_NAME}-bastion` |
| Route server BGP | `${CLUSTER_NAME}-bgp-*` |

## Troubleshooting

### VPC deletion fails with DependencyViolation

Check for lingering ENIs, load balancers, or VPC endpoints still in "deleting" state:

```bash
aws ec2 describe-network-interfaces --region "${REGION}" \
  --filters "Name=vpc-id,Values=${VPC_ID}" --output table
aws elbv2 describe-load-balancers \
  --query "LoadBalancers[?VpcId=='${VPC_ID}']" --output table
```

Delete the blocking resources and retry.

### ROSA delete stalls

Read the tail of the delete log. Common blockers: PVCs with finalizers, load balancer services, webhook configurations. With operator approval, retry with `--best-effort`.

### S3 bucket deletion appears stuck

Versioned buckets with millions of versions take time. Use the Python batch-delete script (not `aws s3 rb --force`). Run in tmux and monitor progress.

### Cannot find OIDC config ID for a deleted cluster

Search all OIDC providers and match by URL:

```bash
for ARN in $(aws iam list-open-id-connect-providers \
  --query 'OpenIDConnectProviderList[].Arn' --output text); do
  URL=$(aws iam get-open-id-connect-provider --open-id-connect-provider-arn "${ARN}" \
    --query 'Url' --output text)
  echo "${ARN} → ${URL}"
done
```

Match against the cluster's infra ID or name in the OIDC URL.
