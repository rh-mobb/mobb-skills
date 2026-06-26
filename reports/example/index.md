# Red Truck Logistics — ROSA Cost Analysis

**Last updated:** 2026-06-26

## Fleet Profile

- **Cluster count:** 11 (8 Classic, 3 HCP)
- **Architecture:** Mixed (Classic + HCP)
- **AZ topology:** Multi-AZ (3 AZs) — all clusters
- **Total worker vCPUs:** 2,788 (2,728 Classic, 60 HCP)
- **Total worker nodes:** 263
- **ROSA contract term:** 1-year
- **EC2 reserved term:** 1-year
- **Region:** us-east-1

## Cluster Details

| Cluster ID | Name | Type | Worker vCPUs | Nodes | Instance profile |
|---|---|---|---|---|---|
| a3f4c2e1-... | prod-core-1 | Classic | 1,200 | 75 | r5.4xlarge — Memory Optimized |
| b8d7e9f0-... | prod-core-2 | Classic | 800 | 50 | r5.4xlarge — Memory Optimized |
| c1d4e5f6-... | prod-batch-1 | Classic | 200 | 25 | r6i.2xlarge — Memory Optimized |
| d9e0f1a2-... | prod-batch-2 | Classic | 96 | 12 | r6i.2xlarge — Memory Optimized |
| e5f6a7b8-... | prod-data-1 | Classic | 112 | 7 | r5.4xlarge — Memory Optimized |
| f2a3b4c5-... | prod-infra-1 | Classic | 192 | 12 | m6i.4xlarge — General Purpose |
| a7b8c9d0-... | dev-core-1 | Classic | 80 | 10 | m5.2xlarge — General Purpose |
| b4c5d6e7-... | dev-batch-1 | Classic | 48 | 12 | m5.xlarge — General Purpose |
| c9d0e1f2-... | hcp-prod-1 | HCP | 16 | 4 | m5.xlarge |
| d6e7f8a9-... | hcp-dev-1 | HCP | 12 | 3 | m5.xlarge (autoscale 1–2/pool, 3 pools) |
| e3f4a5b6-... | hcp-poc-1 | HCP | 32 | 8 | t3.xlarge |

## Pricing Overrides

_(none)_

## Generated Reports

| Date | Report | File |
|---|---|---|
| 2026-06-26 | Cost Analysis | [2026-06-26-cost-analysis.md](2026-06-26-cost-analysis.md) |
| 2026-06-26 | Cost Optimization | [2026-06-26-cost-optimize.md](2026-06-26-cost-optimize.md) |
