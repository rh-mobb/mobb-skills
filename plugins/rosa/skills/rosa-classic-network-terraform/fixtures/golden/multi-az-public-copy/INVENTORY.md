# Network inventory: `demo-multi-classic`

- VPC `vpc-fixture001` — `10.0.0.0/16`
- Mode: **copy**

## Subnets

- `subnet-private-a` — us-east-1a — `10.0.0.0/20` — private
- `subnet-public-a` — us-east-1a — `10.0.48.0/20` — public
- `subnet-private-b` — us-east-1b — `10.0.16.0/20` — private
- `subnet-public-b` — us-east-1b — `10.0.64.0/20` — public
- `subnet-private-c` — us-east-1c — `10.0.32.0/20` — private
- `subnet-public-c` — us-east-1c — `10.0.80.0/20` — public

## ROSA HCP wiring

`aws_subnet_ids`: `subnet-private-a, subnet-private-b, subnet-private-c, subnet-public-a, subnet-public-b, subnet-public-c`
