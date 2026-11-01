# Network inventory: `demo-classic`

- VPC `vpc-036a76adeadc2472f` — `10.0.0.0/16`
- Mode: **copy**

## Subnets

- `subnet-041b27bf8c76685eb` — ap-southeast-2a — `10.0.0.0/20` — private
- `subnet-04a0c4ee61ea198e2` — ap-southeast-2a — `10.0.48.0/20` — public
- `subnet-08388a612d5f23b98` — ap-southeast-2b — `10.0.16.0/20` — private
- `subnet-08a334b8972a53c88` — ap-southeast-2b — `10.0.64.0/20` — public
- `subnet-0b8753db7e124d2d8` — ap-southeast-2c — `10.0.32.0/20` — private
- `subnet-0ee675543e89d0972` — ap-southeast-2c — `10.0.80.0/20` — public

## ROSA HCP wiring

`aws_subnet_ids`: `subnet-041b27bf8c76685eb, subnet-08388a612d5f23b98, subnet-0b8753db7e124d2d8, subnet-04a0c4ee61ea198e2, subnet-08a334b8972a53c88, subnet-0ee675543e89d0972`

## Transit Gateway

See **`transit_gateway_optional.tf`** (commented). Coordinate with the team that owns the shared TGW before attachment or hub route changes.
