---
description: Discover and selectively delete ALL AWS resources associated with a ROSA cluster — VPC, NAT, EFS, S3, IAM, Secrets Manager, and more. For orphaned clusters or post-delete cleanup.
argument-hint: <cluster-name> <aws-region>
---

## Name

rosa:purge-cluster-resources

## Synopsis

```
/rosa:purge-cluster-resources <cluster-name> <aws-region>
```

## Description

Inventories all AWS resources associated with a ROSA cluster by name and tags, then lets the operator select which resource groups to delete. Works whether the cluster is still running, mid-uninstall, or already deleted.

This is the nuclear option — use `/rosa:delete-cluster` if you only need to delete the cluster itself.

## Implementation

Follow the `rosa-purge-cluster-resources` skill. It defines the full workflow: preflight, read-only discovery, grouped inventory presentation, operator selection, and dependency-ordered deletion with per-group confirmation gates.

Set variables from the command arguments:

```bash
CLUSTER_NAME="<cluster-name>"
REGION="<aws-region>"
export AWS_REGION="${REGION}"
```

Then proceed with Phase 0 (Preflight) of the skill.

## Notes

- Both arguments are required. The region cannot be inferred if the cluster is already deleted.
- The skill presents discovered resources as selectable groups — the operator chooses what to delete.
- IAM infrastructure roles are flagged as potentially shared and skipped by default.
- VPC networking is deleted in strict dependency order to avoid `DependencyViolation` errors.
