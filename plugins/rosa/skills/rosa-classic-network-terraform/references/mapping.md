# network-inventory.json → Terraform (adopt / copy)

Maps **`network-inventory.json`** (from `discover_cluster_network.py`) to resources emitted by **`network_to_tf.py`**. Import IDs follow the AWS provider (not AWS console association IDs).

| Inventory key | Terraform resource | Adopt (`imports.tf`) | Notes |
|---------------|-------------------|----------------------|-------|
| `vpc` | `aws_vpc.main` | VPC id | CIDR from live VPC |
| `internet_gateway` | `aws_internet_gateway.main` | IGW id | |
| `subnets[]` | `aws_subnet.*` | Subnet id | Public vs private from tags / `MapPublicIpOnLaunch` |
| `nat_gateways[]` | `aws_nat_gateway.*`, `aws_eip.*` | NAT id, allocation id | One NAT per public subnet (typical) |
| `route_tables[]` | `aws_route_table.*` | Route table id | Public vs private routes (IGW, NAT, S3 gateway) |
| `route_tables[].associations` | `aws_route_table_association.*` | **`subnet-id/route-table-id`** | Required format for provider import |
| `vpc_endpoints[]` (customer) | `vpc_endpoints_adopt.tf` | Endpoint id | Optional; operator confirms before write |
| `rosa_hcp_control_plane_vpc_endpoint` | *(none in network/)* | — | ROSA-managed; never adopt in `network/` |
| `security_groups[]` | Partial / inventory only | SG id | ROSA cluster SGs often documented, not duplicated |
| `transit_gateway_attachments[]` | `transit_gateway_optional.tf` | Attachment id | Commented template; network-team coordination |

**HCP subnet order** for `aws_subnet_ids`: private subnets by AZ, then public (public clusters). See `merge_hcp_stack.py` and **`../../../references/rosa-hcp-module-adopt-mapping.md`**.

**Upstream alignment:** route layout follows ideas in [terraform-rosa-networking/route.tf](https://github.com/rh-mobb/terraform-rosa/blob/main/modules/terraform-rosa-networking/route.tf); adopt stacks use raw `aws_*` resources, not `terraform-redhat/rosa-hcp//modules/vpc`.
