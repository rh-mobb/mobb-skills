# Network Terraform (`network/`) — `demo-hcp-public`

- Region: **ap-southeast-2**
- Mode: **adopt**

AWS VPC/subnets/IGW/NAT/routes for ROSA. This directory is a **separate Terraform root** from the cluster stack in the parent folder.

See **[../README.md](../README.md)** for split-stack apply/destroy order and Makefile targets.

## Prerequisites

- [ROSA CLI](https://docs.openshift.com/rosa/) — `rosa login` (and OCM token for cluster stacks)
- AWS credentials with access to **`ap-southeast-2`** (read for plan; write for apply)
- [Terraform](https://developer.hashicorp.com/terraform) ≥ 1.5

## Manual Terraform (`network/`)

```bash
cd network
export AWS_DEFAULT_REGION=ap-southeast-2
terraform init
terraform fmt
terraform validate
terraform plan
terraform apply
```

## Files

- `INVENTORY.md` — discovered resources and wiring
- `network-outputs.json` — subnet order for `merge_hcp_stack.py`
- `imports.tf` — adopt mode only

