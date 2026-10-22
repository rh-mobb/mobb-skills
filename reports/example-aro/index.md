# Example Corp — ARO Cost Analysis

**Last updated:** 2026-10-20

## Fleet Profile

- **Cluster count:** 15 (all Standard; 9 further subscriptions Archived or Stale, excluded)
- **Architecture:** Standard
- **Azure region(s):** eastus — modeled at public East US list rates; actual region not supplied
- **Total worker vCPUs:** 1,608
- **Total control plane vCPUs:** 732 (31% of 2,340 provisioned)
- **Total compute nodes:** 236
- **Azure compute term:** 3-year RI (modeled at 0.38×)
- **ARO license term:** 3-year committed
- **Reservation scope:** not supplied
- **Reservation utilization:** not supplied
- **Reservation expiry:** not supplied

Reservation scope, utilization and expiry are outstanding. Until they are known, the
figures in the linked report are a **modeled saving only** and cannot be stated as a
reduction in what Example Corp pays.

## Cluster Details

Control plane VM size is derived from reported vCPU totals, not from supplied SKUs.
Worker pool composition was not supplied; compute node counts are shown instead.

| Cluster | Architecture | Version | CP VM (derived) | Compute nodes | Worker vCPU | CP vCPU |
|---|---|---|---|---|---|---|
| ocp-dev-01 | Standard | 4.21.28 | 3 × 20 vCPU | 8 | 40 | 60 |
| ocp-prd-01 | Standard | 4.18.48 | 3 × 16 vCPU | 37 | 272 | 48 |
| ocp-prd-02 | Standard | 4.19.30 | 3 × 16 vCPU | 14 | 88 | 48 |
| ocp-prd-03 | Standard | 4.21.25 | 3 × 8 vCPU | 4 | 64 | 24 |
| ocp-prd-04 | Standard | 4.20.15 | 3 × 16 vCPU | 11 | 64 | 48 |
| ocp-prd-05 | Standard | 4.21.27 | 3 × 16 vCPU | 11 | 64 | 48 |
| ocp-tst-01 | Standard | 4.18.48 | 3 × 24 vCPU | 45 | 336 | 72 |
| ocp-tst-02 | Standard | 4.20.32 | 3 × 16 vCPU | 18 | 120 | 48 |
| ocp-tst-03 | Standard | 4.20.32 | 3 × 8 vCPU | 8 | 64 | 24 |
| ocp-tst-04 | Standard | 4.18.48 | 3 × 16 vCPU | 27 | 192 | 48 |
| ocp-tst-05 | Standard | 4.21.21 | 3 × 16 vCPU | 12 | 72 | 48 |
| ocp-tst-06 | Standard | 4.21.24 | 3 × 16 vCPU | 11 | 64 | 48 |
| ocp-tst-07 | Standard | 4.19.30 | 3 × 24 vCPU | 12 | 72 | 72 |
| ocp-tst-08 | Standard | 4.19.30 | 3 × 16 vCPU | 7 | 32 | 48 |
| ocp-tst-09 | Standard | 4.21.21 | 3 × 16 vCPU | 11 | 64 | 48 |
| **Total** | | | **45 nodes** | **236** | **1,608** | **732** |

### Environment split

| Prefix | Environment | Clusters | Worker vCPU | Share |
|---|---|---|---|---|
| ocp-dev | Development | 1 | 40 | 2.5% |
| ocp-prd | Production | 5 | 552 | 34.3% |
| ocp-tst | Test | 9 | 1,016 | 63.2% |

## Pricing Overrides

- `azure_discount:` 62% (3-year RI, 0.38× multiplier)
- `license_rate:` customer's 3-year committed rate

## Generated Reports

| Date | Report | File |
|---|---|---|
| 2026-10-20 | Cost Report | [2026-10-20-cost-report.md](2026-10-20-cost-report.md) |
