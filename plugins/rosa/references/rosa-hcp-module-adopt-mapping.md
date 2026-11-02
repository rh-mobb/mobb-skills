# ROSA HCP module vs adopt / discovery mapping

Cross-reference between **[terraform-redhat/terraform-rhcs-rosa-hcp](https://github.com/terraform-redhat/terraform-rhcs-rosa-hcp)** (local clone: `references/terraform-rhcs-rosa-hcp`) and what MOBB skills can **import**, **generate**, or **leave to the operator**.

Upstream layout is the source of truth for variable names and submodule graphs. Our skills use the **registry root** `terraform-redhat/rosa-hcp/rhcs` for cluster adopt/create; **network adopt** uses opinionated raw AWS resources in `network_to_tf.py` (similar resources to `modules/vpc/`, not that submodule verbatim).

## Reference clone

```bash
git clone https://github.com/terraform-redhat/terraform-rhcs-rosa-hcp references/terraform-rhcs-rosa-hcp
```

(`references/` is gitignored in mobb-skills; clone locally for lookups.)

---

## Network & VPC

| Upstream | Purpose | OCM / `rosa` / AWS discovery | MOBB skill today | Adopt notes |
|----------|---------|------------------------------|------------------|-------------|
| **`modules/vpc/`** | Greenfield BYO VPC (subnets, IGW, NAT, routes, **S3 gateway endpoint**, route-table assoc) | N/A for adopt | **Partial overlap** with `network_to_tf.py` (adopt/copy) | Adopt stack uses **split** `network/` + `imports.tf`, not the vpc submodule. Align subnet order with `examples/rosa-hcp-public` (`concat(public, private)` for public clusters). |
| **`network_to_tf.py`** | Classic/HCP VPC adopt or copy | `discover_cluster_network.py` → `network-inventory.json` | **Yes** | Route table association imports use `subnet-id/route-table-id` (AWS provider). TGW: commented **`transit_gateway_optional.tf`**. Optional skips: endpoints, SGs, flow logs. |
| **`modules/shared-vpc-resources/`** | Shared VPC account | `shared_vpc` on cluster | **Out of scope** | MOBB skills do not generate shared-VPC stacks. |
| **ROSA HCP control-plane VPCE** | PrivateLink endpoint for HCP API | Tagged `api.openshift.com/id` / cluster name | **Never adopt in `network/`** | Discovery marks `rosa_hcp_control_plane: true`. ROSA lifecycle owns the VPCE. |
| **Customer VPC endpoints** | S3 gateway, interface endpoints, etc. | `discover_cluster_network.py` → `adoptable: true` | **`vpc_endpoints_adopt.tf`** when operator confirms (else `--skip-endpoints`) | Agent **asks** before write. |
| **`modules/additional-cp-sg/`** | Extra SGs on control-plane VPCE | `rosa_hcp_control_plane_vpc_endpoint.additional_control_plane_security_group_ids` | **`hcp_adopt_to_tf.py`** (private only) | Imports `aws_vpc_endpoint_security_group_association` on root module; **not** the VPCE itself. |
| **`aws_additional_compute_security_group_ids`** (root → cluster) | Extra SGs on workers | Not always visible in `rosa describe`; AWS EC2/ENI/SG on worker subnets | **`discover_cluster_network.py`** optional SG list | Map to tfvars if SGs are customer-managed; ROSA default worker SGs often **should not** be duplicated in TF. |

### Lab reference (anonymized in repo)

See committed example **[../../../examples/rosa/hcp-adopt-split-stack/](../../../examples/rosa/hcp-adopt-split-stack/)** (`demo-hcp-public`):

- **Public** API/ingress (`api.listening: external`, `private_link: false`).
- **BYO VPC** in cluster account: adopt via **`network/`** split stack.
- **No shared VPC** path in typical describe JSON.
- **No** `additional-cp-sg` module instance (public cluster).
- **Node pool autoscaling** only — no `rhcs_hcp_cluster_autoscaler` in adopt tfvars.

---

## Cluster module graph (root `terraform-redhat/rosa-hcp/rhcs`)

| Submodule / resource | Adopt (`create_* = false`) | Data source | MOBB generator |
|------------------------|----------------------------|-------------|----------------|
| **`modules/rosa-cluster-hcp/`** | `rhcs_cluster_rosa_hcp`, default ingress, optional cluster autoscaler | `rosa describe cluster`, ingress | **`hcp_adopt_to_tf.py`** + **`classic_to_hcp.py`** (create) |
| **`modules/machine-pool/`** | `rhcs_hcp_machine_pool` | `rosa list machinepools` | Both mappers |
| **`modules/account-iam-resources/`** | Reference ARNs / `account_role_prefix` only | STS block on cluster JSON | Adopt: prefix + `oidc_config_id`; no IAM import |
| **`modules/oidc-config-and-provider/`** | `oidc_config_id` only | STS OIDC id | Adopt tfvars |
| **`modules/operator-roles/`** | `operator_role_prefix` only | STS operator roles list | Adopt tfvars |
| **`modules/idp/`** | Optional post-adopt | `rosa list idps` + OCM get | **classic_to_hcp** only (`fetch_classic_idps.py`) |
| **`modules/kubelet-configs/`** | Manual / future | OCM kubelet configs API | Not v1 |
| **`modules/image-mirrors/`** | Manual / future | OCM registry config | Not v1 |
| **`modules/log-forwarder/`** | Manual / future | `control_plane.log_forwarders` | Not v1 |
| **`modules/additional-cp-sg/`** | Private + extra CP SG associations | Inventory + **`hcp_adopt_to_tf.py`** | **Yes** (private) |

---

## OCM / ROSA fields → root module variables (adopt-relevant)

| Live signal | Module variable(s) | Handled by |
|-------------|---------------------|------------|
| `hypershift.enabled` | (must be true) | Gate in mappers |
| `aws.subnet_ids`, AZs | `aws_subnet_ids`, `aws_availability_zones` | describe + optional inventory order |
| `network.machine_cidr`, pod/service, host_prefix | same on cluster resource | describe |
| `aws.sts.*`, `oidc_config.id` | `account_role_prefix`, `oidc_config_id`, `operator_role_prefix` | describe |
| `aws.ec2_metadata_http_tokens` | `ec2_metadata_http_tokens` | **`hcp_adopt_to_tf.py`** |
| `aws.billing_account_id` | `aws_billing_account_id` | **`hcp_adopt_to_tf.py`** |
| `properties` (non-reserved) | `properties` | adopt (omit `rosa_tf_*`) |
| Node pool autoscaling | `machine_pools[].autoscaling` | **`hcp_adopt_to_tf.py`**; **not** cluster autoscaler |
| `nodes.autoscale_compute` | ~~`cluster_autoscaler_enabled`~~ | **Ignore** when pools autoscale (HCP) |
| Default ingress listening | `default_ingress_listening_method` | ingress list + private flag |
| `shared_vpc` / shared roles | `shared_vpc`, operator/account shared role ARNs | **Future**; see shared-vpc example |
| `aws.private_link` | implicit in ROSA-managed AWS | Do not adopt as standalone TF in v1 |
| Classic IdPs | `identity_providers` map | **classic_to_hcp** only |

---

## Recommended roadmap (adopt coverage)

1. **Done / maintain:** VPC core adopt, rtb assoc import format, cluster adopt, pool tags, **exclude ROSA CP VPCE**, **ask + optional customer endpoint file**, **additional-cp-sg** on private adopt.
2. **Next:** Richer **`vpc_endpoints_adopt.tf`** (route tables, interface endpoint attributes) after operator confirms.
3. **Out of scope:** **Shared VPC** (`shared-vpc-resources`).
4. **Post-adopt:** IdPs, log forwarders, kubelet configs, image mirrors.

See also **[../terraform.md](../terraform.md)** and this document for operator commands.
