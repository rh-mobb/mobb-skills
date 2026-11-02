# Migration notes: Classic `demo-classic` → HCP `demo-classic-hcp`

- Source cluster ID: `01234567-89ab-cdef-0123-456789abcdef`
- IAM: new HCP account roles, OIDC, and operator roles with prefix `rosa`

## Translations

- IAM prefix shortened from 'demo-classic-hcp' to 'rosa' for 64-char role name limit.
- Default pool will materialize as worker-1 .. worker-3 with 1 replica(s) each (total 3).
- Synthesized infra machine pools from Classic nodes.infra (no infra MachinePool in ROSA API).

## Identity providers (Classic → HCP)

### `developer` (htpasswd)
- Replicated **1** htpasswd user(s) with **new** random passwords (Classic passwords are not exported from OCM).
### `admin` (htpasswd)
- Replicated **1** htpasswd user(s) with **new** random passwords (Classic passwords are not exported from OCM).
### `cluster-admin` (htpasswd)
- Replicated **1** htpasswd user(s) with **new** random passwords (Classic passwords are not exported from OCM).

## Unmapped / manual

- Classic subnet IDs (do not reuse): subnet-041b27bf8c76685eb, subnet-08388a612d5f23b98, subnet-0b8753db7e124d2d8, subnet-04a0c4ee61ea198e2, subnet-08a334b8972a53c88, subnet-0ee675543e89d0972
- Classic control plane / infra node counts: {"availability_zones": ["ap-southeast-2a", "ap-southeast-2b", "ap-southeast-2c"], "compute": 3, "compute_machine_type": {"href": "/api/clusters_mgmt/v1/machine_types/m5.xlarge", "id": "m5.xlarge", "kind": "MachineTypeLink"}, "compute_root_volume": {"aws": {"size": 300}}, "infra": 3, "infra_machine_type": {"href": "/api/clusters_mgmt/v1/machine_types/r5.xlarge", "id": "r5.xlarge", "kind": "MachineTypeLink"}, "master": 3} — HCP has no customer control plane.
- Do not reuse Classic machine CIDR 10.0.0.0/16 or pod CIDR 10.128.0.0/14 when routing overlaps.

Workloads targeting infra nodes need tolerations for `node-role.kubernetes.io/infra=reserved:NoSchedule` when infra pools were created.