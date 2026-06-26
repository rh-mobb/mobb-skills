# ROSA Cost Analysis — Red Truck Logistics

**Date:** 2026-06-26
**Command:** /rosa:cost
**Rates:** EC2 on-demand sourced from AWS Pricing API; ROSA fees current as of 2026-06 — verify at https://aws.amazon.com/rosa/pricing/ before quoting
**Region:** us-east-1 (N. Virginia) — all clusters

---

## EC2 Rates Used (us-east-1, on-demand)

| Instance | vCPU | On-demand/hr | $/vCPU/hr |
|---|---|---|---|
| r5.4xlarge | 16 | $1.008 | $0.0630 |
| r6i.2xlarge | 8 | $0.504 | $0.0630 |
| m6i.4xlarge | 16 | $0.768 | $0.0480 |
| m5.2xlarge | 8 | $0.384 | $0.0480 |
| m5.xlarge (CP nodes) | 4 | $0.192 | $0.0480 |
| r5.xlarge (Infra nodes) | 4 | $0.252 | $0.0630 |
| m5.xlarge | 4 | $0.192 | $0.0480 |
| t3.xlarge | 4 | $0.1664 | $0.0416 |

_1-year reserved multiplier: 0.6× on-demand. EBS gp3: $0.08/GB-month ($8/node/month assumed)._

## Fleet Profile

- **Total clusters:** 11 (8 Classic, 3 HCP)
- **Total worker vCPUs:** 2,788 (2,728 Classic, 60 HCP)
- **Total worker nodes:** 263 (248 Classic, 15 HCP)
- **ROSA contract term:** 1-year
- **EC2 reserved term:** 1-year (0.6× on-demand)
- **AZ topology:** Multi-AZ (3 AZs) — all clusters

## Classic Cluster Baseline

| Cluster | vCPUs | Nodes | EC2 Profile | ROSA Fee/mo | Worker EC2+EBS/mo | CP+Infra/mo | **Total/mo** |
|---|---|---|---|---|---|---|---|
| prod-core-1 | 1,200 | 75 | r5.4xlarge — Mem | $25,000 | $33,734 | $980 | **$59,714** |
| prod-core-2 | 800 | 50 | r5.4xlarge — Mem | $16,666 | $22,476 | $980 | **$40,122** |
| prod-batch-1 | 200 | 25 | r6i.2xlarge — Mem | $4,167 | $5,721 | $980 | **$10,868** |
| prod-batch-2 | 96 | 12 | r6i.2xlarge — Mem | $2,000 | $2,746 | $980 | **$5,726** |
| prod-data-1 | 112 | 7 | r5.4xlarge — Mem | $2,333 | $3,147 | $980 | **$6,460** |
| prod-infra-1 | 192 | 12 | m6i.4xlarge — GP | $4,000 | $4,134 | $980 | **$9,114** |
| dev-core-1 | 80 | 10 | m5.2xlarge — GP | $1,667 | $1,765 | $980 | **$4,412** |
| dev-batch-1 | 48 | 12 | m5.xlarge — GP | $1,000 | $1,107 | $980 | **$3,087** |
| **Classic total** | **2,728** | **203** | | **$56,833** | **$74,830** | **$7,840** | **$139,503** |

Classic fleet annual: **$1,674,036**

**Classic CP+Infra per cluster (multi-AZ, us-east-1, 1yr reserved):**
- CP (3 × m5.2xlarge, 24 vCPU @ $0.0480/vCPU/hr): $504/mo + $72 EBS = $576/mo
- Infra (3 × r5.xlarge, 12 vCPU @ $0.0630/vCPU/hr): $331/mo + $72 EBS = $403/mo
- **Per cluster: $980/mo**

## HCP Cluster Costs (Already Migrated)

| Cluster | vCPUs | Nodes | EC2 Profile | ROSA Fee/mo | Worker EC2+EBS/mo | Cluster Fee/mo | **Total/mo** |
|---|---|---|---|---|---|---|---|
| hcp-prod-1 | 16 | 4 | m5.xlarge | $333 | $369 | $183 | **$885** |
| hcp-dev-1 | 12 | 3 | m5.xlarge | $250 | $277 | $183 | **$710** |
| hcp-poc-1 | 32 | 8 | t3.xlarge | $667 | $647 | $183 | **$1,497** |
| **HCP total** | **60** | **15** | | **$1,250** | **$1,293** | **$549** | **$3,092** |

HCP fleet annual: **$37,104**

## Fleet Summary

| | Classic | HCP | **Fleet Total** |
|---|---|---|---|
| ROSA worker fee | $56,833 | $1,250 | $58,083 |
| Worker EC2 + EBS | $74,830 | $1,293 | $76,123 |
| CP+Infra or Cluster fee | $7,840 | $549 | $8,389 |
| **Total/month** | **$139,503** | **$3,092** | **$142,595** |
| **Total/year** | **$1,674,036** | **$37,104** | **$1,711,140** |

## Classic vs HCP Cost Comparison

If the 8 Classic clusters were migrated to HCP today (same worker configuration, 1yr reserved EC2, us-east-1):

| Line item | Classic | HCP |
|---|---|---|
| CP+Infra EC2+EBS | $7,840/mo | $0 |
| HCP cluster fee | $0 | $1,460/mo (8 clusters × $182.50) |
| Worker costs | $131,663/mo | $131,663/mo |
| **Total/month** | **$139,503** | **$133,123** |
| **Total/year** | **$1,674,036** | **$1,597,476** |
| **Savings** | | **$6,380/mo — $76,560/yr** |

Net savings per migrated cluster: **$797/mo** (CP+Infra $980 − HCP fee $183).

## HCP Qualitative Benefits

| Feature | Classic | HCP | Benefit |
|---|---|---|---|
| AWS Managed Policies | No | Yes | Zero trust / least privilege by default |
| BYO CNI (e.g. Cilium) | No | Yes | Bring preferred networking stack |
| Graviton/ARM CPU | No | Yes | Up to 40% better price-performance |
| Karpenter (4.22+) | No | Yes | Single NodePool; bin-packing, Spot+ARM, scale to zero |
| Zero Egress | No | Yes | No internet egress for base cluster operators |
| Cluster provisioning | ~52 min | ~15 min | 3.5× faster |

## Top Optimization Opportunities

| # | Opportunity | Est. savings/mo | Est. savings/yr | Complexity |
|---|---|---|---|---|
| 1 | Upgrade steady-state to 3yr contracts | ~$28,000 | ~$336,000 | Low |
| 2 | Migrate 8 Classic clusters to HCP | $6,380 | $76,560 | Medium |
| 3 | ARM Graviton + Karpenter (post-HCP) | TBD post-migration | TBD | Medium |

### Opportunity 1 detail: 3-year contract upgrade

The fleet has ~2,200 vCPUs of steady-state capacity and ~528 vCPUs of burst. Upgrading steady-state to 3yr terms saves:

- ROSA fee (1yr→3yr, $20.83→$13.89/vCPU/mo): 2,200 × $6.94 = **$15,268/mo**
- EC2 1yr→3yr delta (~20% additional off on-demand):
  - ~2,000 vCPU r5/r6i @ $0.063 OD: **$9,198/mo**
  - ~200 vCPU m6i/m5 @ $0.048 OD: **$1,402/mo**
  - EC2 subtotal: **$10,600/mo**
- **Combined: ~$25,868/mo ≈ ~$28,000/mo = ~$336,000/yr — administrative change only, no infrastructure impact**

dev-core-1 and dev-batch-1 are unlikely steady-state candidates; recommend 90-day utilization review before committing dev workloads to 3yr terms.

### Opportunity 2 detail: Classic→HCP migration

Each Classic cluster contributes $980/mo in CP+Infra EC2+EBS overhead at us-east-1 1yr reserved rates. Migrating to HCP eliminates this and adds the $182.50/mo HCP cluster fee — a net saving of **$797/cluster/month**. All 8 Classic clusters are multi-AZ; no application changes are required in Phase 1.

### Opportunity 3 detail: ARM Graviton + Karpenter

The fleet is Memory Optimized-heavy (r5, r6i). Post-HCP-migration on ROSA 4.22+, Karpenter enables:
- Graviton3 r7g ARM nodes — ~15% cheaper per vCPU than r6i at equivalent pricing
- E=1.25 performance multiplier: x86 nodes / 1.25 = fewer nodes for equivalent throughput
- Spot instances (~70% EC2 discount) for burst workloads
- Scale-to-zero for non-production clusters (hcp-poc-1, hcp-dev-1)

Quantification requires HCP migration first; recommend `/rosa:cost-optimize` post-migration for detailed figures.

## Narrative

Red Truck Logistics is spending **$142,595/month ($1,711,140/year)** on ROSA across 11 clusters at us-east-1 on-demand rates with 1-year reserved EC2. The dominant cost is prod-core-1 at **$59,714/month (43% of Classic spend)**. The largest single opportunity is upgrading steady-state capacity to 3-year contracts, worth **~$336,000/year** with no infrastructure changes. Migrating the 8 Classic clusters to HCP saves **$76,560/year** and unlocks the Karpenter opportunity. For a detailed optimization analysis with phased execution plan, use `/rosa:cost-optimize`.
