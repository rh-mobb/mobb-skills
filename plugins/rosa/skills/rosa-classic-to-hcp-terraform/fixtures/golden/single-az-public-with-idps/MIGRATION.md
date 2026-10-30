# Migration notes: Classic `demo-single` → HCP `demo-idp-hcp`

Operator runbook: **[README.md](README.md)**.

- Source cluster ID: `fedcba98-7654-3210-fedc-ba9876543210`
- IAM: new HCP account roles, OIDC, and operator roles with prefix `demo`

## Translations

- IAM prefix shortened from 'demo-idp-hcp' to 'demo' for 64-char role name limit.
- Default pool: single AZ us-west-2a, 2 replica(s).
- Additional pool memory -> AZ us-west-2a (single private subnet).

## Identity providers (Classic → HCP)

### `developer` (htpasswd)
- Replicated **2** htpasswd user(s) with **new** random passwords (Classic passwords are not exported from OCM).
### `corp-oidc` (openid)
- Generated commented Terraform stub in `identity_providers_optional.tf`. Register a **new** OAuth/OIDC client for the HCP cluster callback URL before enabling.
### `github-org` (github)
- Generated commented Terraform stub in `identity_providers_optional.tf`. Register a **new** OAuth/OIDC client for the HCP cluster callback URL before enabling.

## Unmapped / manual

- Classic subnet IDs (do not reuse): subnet-aaa
- Classic control plane / infra node counts: {"master": 1, "compute": 2} — HCP has no customer control plane.

Workloads targeting infra nodes need tolerations for `node-role.kubernetes.io/infra=reserved:NoSchedule` when infra pools were created.
