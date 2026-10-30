# Migration notes: Classic `demo-single` → HCP `demo-single-hcp`

Operator runbook: **[README.md](README.md)**.

- Source cluster ID: `fedcba98-7654-3210-fedc-ba9876543210`
- IAM: new HCP account roles, OIDC, and operator roles with prefix `demo`

## Translations

- IAM prefix shortened from 'demo-single-hcp' to 'demo' for 64-char role name limit.
- Default pool: single AZ us-west-2a, 2 replica(s).
- Additional pool memory -> AZ us-west-2a (single private subnet).

## Unmapped / manual

- Classic subnet IDs (do not reuse): subnet-aaa
- Classic control plane / infra node counts: {"master": 1, "compute": 2} — HCP has no customer control plane.

Workloads targeting infra nodes need tolerations for `node-role.kubernetes.io/infra=reserved:NoSchedule` when infra pools were created.
