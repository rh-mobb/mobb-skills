# MUFG ROSA Cost Analysis Report — Design Spec

**Date:** 2026-07-07
**Author:** Paul Czarkowski

---

## Context

MUFG (三菱UFJ銀行, org `2AVARHfxY3ZEYfY5D0feockGDlz`) operates 31 active ROSA clusters across two AWS regions in Japan, all on PAYGO ROSA and on-demand EC2. This spec describes the report set to produce: a fleet index, a cost analysis document, and an interactive cost explorer.

---

## Fleet Overview (as of 2026-07-03 telemetry)

**27 ROSA HCP clusters** — all `ap-northeast-1` (Tokyo)
**4 ROSA Classic clusters** — 3 in `ap-northeast-1`, 1 in `ap-northeast-3` (Osaka); labeled "IBM CP/ROSA" in HCC; IBM CP licensing is out of scope for this report.

**Out of scope:** 2 OCP/VMware clusters (EBS account 12577663) — different cost model.

---

## Output Files

```
reports/mufg/
├── index.md                        # Fleet profile
├── 2026-07-07-cost-analysis.md     # Per-cluster cost breakdown + optimization opportunities
└── cost-explorer.html              # Interactive cost explorer (same template as other customers)
```

---

## Data Sources

| Source | What it provides |
|--------|-----------------|
| HCC telemetry screenshots (2026-07-03) | Actual running worker vCPUs per cluster — used as steady-state billing basis |
| OCM CLI (RH profile, `ocm-rh.json`) | Node pools for all 27 HCP clusters; machine pools for all 4 Classic clusters (min/max replicas, instance types) |
| AWS Pricing API (`ap-northeast-1`, `ap-northeast-3`) | On-demand $/hr for every instance type in use |

### Instance types in use

**HCP clusters:** m5.xlarge, m5.2xlarge, m6a.2xlarge, r7i.xlarge, r7i.2xlarge, r7i.4xlarge, r7a.2xlarge, r7a.xlarge, c6a.4xlarge, c7i.4xlarge, t3.xlarge, g4dn.4xlarge

**Classic clusters:** r5.2xlarge (workers), r5.8xlarge, r5a.8xlarge, m5.8xlarge, r7a.xlarge (named pools); r5.4xlarge, r5.xlarge, r5.2xlarge (infra); plus `dis-mcp-001` in ap-northeast-3 uses r5.8xlarge workers + r5.xlarge infra.

---

## Cost Model

### HCP Clusters

| Line item | Formula |
|-----------|---------|
| ROSA HCP fee | $182.50/cluster/mo |
| Worker EC2 | actual_vCPU × $/vCPU/hr × 730 hr (blended rate across node pools) |
| EBS | ~$26/node/mo (300 GB gp3 at $0.088/GB-month, ap-northeast-1) |
| CP/Infra overhead | $0 — no customer-managed control plane or infra nodes |

**Steady-state vCPUs:** telemetry actual from HCC screenshots.
**Burst headroom:** autoscaler max vCPU (sum across all node pools) − actual vCPU.
**Burst billing:** 20% of remaining headroom (conservative default, adjustable in cost explorer).

### Classic Clusters (IBM CP/ROSA)

| Line item | Formula |
|-----------|---------|
| ROSA worker fee | PAYGO: $125 per 4-vCPU-block/mo, applied to actual + 20% burst |
| Worker EC2 | actual_vCPU × blended $/vCPU/hr × 730 hr (blended across all named machine pools) |
| CP overhead | 3 × master instance × $/hr × 730 hr + EBS |
| Infra overhead | 3 × infra instance × $/hr × 730 hr + EBS |
| EBS (workers) | ~$26/node/mo |

IBM CP licensing: noted in the report as out of scope; ROSA infrastructure costs only.

---

## index.md Content

- Fleet profile summary (cluster counts, regions, total actual vCPU, max vCPU, burst headroom)
- Cluster table: cluster ID (truncated), name, type (HCP/Classic), region, actual vCPU, max vCPU, primary instance types, node count
- All node pool / machine pool detail table per cluster
- Telemetry notes (data source, date, any anomalies)
- Pricing overrides section (confirmed instance prices from AWS Pricing API)
- Links to generated reports

---

## cost-analysis.md Content

1. **Methodology note** — telemetry-actual basis, burst billing assumption
2. **EC2 rates used** — per instance type, per region, on-demand
3. **Fleet profile summary**
4. **Classic CP+Infra overhead** — per Classic cluster
5. **Per-cluster baseline table** — ROSA fee, EC2+EBS, CP+Infra, total/mo
6. **EC2+EBS breakdown by cluster** — steady + burst + EBS per cluster
7. **Fleet summary** — ROSA fees, EC2+EBS, CP+Infra, total/mo and /yr
8. **GPU cluster callout** — reg-bdp-001 (g4dn.4xlarge pools): separate cost note; g4dn premium over standard compute
9. **IBM CP Classic overhead callout** — Classic CP+Infra savings available via HCP migration
10. **Top optimization opportunities table** — estimated savings/mo and /yr:
    - PAYGO → 1-year contracts
    - PAYGO → 3-year contracts
    - Graviton/ARM migration for eligible pools (r7g/c7g alternatives for r7i/c7i pools)
    - Classic → HCP migration (eliminates CP overhead for 4 clusters)
11. **Opportunity details** — one section per opportunity
12. **Optimized TCO summary** — phased savings roadmap
13. **Narrative** — plain-language summary of findings and top action

---

## cost-explorer.html

Same interactive template used for Suncorp, Cathay Pacific, and Red Truck Logistics. Adjustable levers:
- Contract term (PAYGO / 1yr / 3yr)
- Burst utilization %
- HCP migration toggle (for Classic clusters)
- Graviton/ARM migration toggle (for eligible HCP node pools)

---

## Assumptions

- Telemetry snapshot date: 2026-07-03 (HCC last active date shown in app)
- EBS: 300 GB gp3 per node — $0.088/GB-month in ap-northeast-1; ap-northeast-3 rate to be confirmed via AWS Pricing API during implementation
- Burst billing: 20% of remaining headroom (max − actual vCPU)
- EC2: on-demand, no discount
- ROSA: PAYGO for all clusters
- IBM CP licensing: not included
- OCP/VMware clusters: not included

---

## Exclusions

- IBM CP licensing costs
- OCP/VMware cluster costs (EBS account 12577663)
- Data transfer / networking costs
- Storage costs beyond EBS worker root volumes
- Spot instance savings (noted as future opportunity but not modeled in baseline)
