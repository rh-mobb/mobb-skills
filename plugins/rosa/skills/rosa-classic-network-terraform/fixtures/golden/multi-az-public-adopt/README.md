# Network Terraform — `demo-multi-classic`

- Region: **us-east-1**
- Mode: **adopt**

Standalone network stack (no cluster root in parent). Wire outputs into HCP `terraform.tfvars` or run **`merge_hcp_stack.py`**.

## Prerequisites

- [ROSA CLI](https://docs.openshift.com/rosa/) — `rosa login` (and OCM token for cluster stacks)
- AWS credentials with access to **`us-east-1`** (read for plan; write for apply)
- [Terraform](https://developer.hashicorp.com/terraform) ≥ 1.5

## Manual Terraform (`network/`)

```bash
cd network
export AWS_DEFAULT_REGION=us-east-1
terraform init
terraform fmt
terraform validate
terraform plan
terraform apply
```

## Files

- `INVENTORY.md`, `network-outputs.json`, `imports.tf` (adopt)

