# Migration notes: Classic `demo-multi` → HCP `demo-multi-hcp`

Operator runbook: **[README.md](README.md)**.

- Source cluster ID: `01234567-89ab-cdef-0123-456789abcdef`
- IAM: new HCP account roles, OIDC, and operator roles with prefix `demo`

## Translations

- IAM prefix shortened from 'demo-multi-hcp' to 'demo' for 64-char role name limit.
- Default pool will materialize as worker-1 .. worker-3 with 2 replica(s) each (total 6).
- Additional pool gpu-1 -> AZ us-east-1a (private subnet for worker-1).
- Additional pool gpu-2 -> AZ us-east-1b (private subnet for worker-2).
- Additional pool gpu-3 -> AZ us-east-1c (private subnet for worker-3).
- Pool gpu autoscaling on Classic — verify HCP pool autoscaling limits after apply.
- Synthesized infra machine pools from Classic nodes.infra (no infra MachinePool in ROSA API).

## Unmapped / manual

- Classic subnet IDs (do not reuse): subnet-private-a, subnet-private-b, subnet-private-c
- Classic control plane / infra node counts: {"master": 3, "infra": 3, "compute": 6} — HCP has no customer control plane.

Workloads targeting infra nodes need tolerations for `node-role.kubernetes.io/infra=reserved:NoSchedule` when infra pools were created.
