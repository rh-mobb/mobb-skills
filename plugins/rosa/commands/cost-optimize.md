---
description: Rank cost savings opportunities for a ROSA fleet with estimated savings and implementation complexity.
---

## Name

rosa:cost-optimize

## Synopsis

```
/rosa:cost-optimize [inputs]
```

## Description

Analyzes a ROSA fleet and produces a ranked list of cost optimization opportunities, each with estimated monthly savings and implementation complexity (low / medium / high).

Accepts the same inputs as `/rosa:cost-estimate`, plus:
- `arm_pct=50` — target percentage of fleet to migrate to ARM Graviton (default: 50%)
- `prod_clusters=N` — number of production clusters (used for Karpenter scale-to-zero savings on non-prod)

## Implementation

1. Collect fleet data and contract terms the same way as `/rosa:cost-estimate`.

2. Calculate the current baseline cost using the formula in the rosa-cost skill.

3. Evaluate and quantify each opportunity in order:

**Opportunity 1: Migrate Classic clusters to HCP**

Use the Classic→HCP Savings Per Cluster table from the rosa-cost skill. For each Classic cluster:
- Single-AZ: approximately $1,148/month net savings (gross $1,331/mo less $182.50/mo HCP cluster fee)
- Multi-AZ: approximately $1,357/month net savings (gross $1,539/mo less $182.50/mo HCP cluster fee)

Multiply by the count of Classic clusters in the fleet to obtain total savings. If the fleet contains no Classic clusters, skip this opportunity.

Complexity: **Medium** (infrastructure change; no application changes in Phase 1).

**Opportunity 2: Contract pricing for steady-state capacity**

If autoscaling min/max data is available (Live mode from OCM or user-provided):
- Split steady-state (minimum replica count) from burst (max − min)
- Apply the break-even analysis from the rosa-cost skill: 1-year contracts break even at >67% utilization; 3-year contracts at >45%
- Calculate annual savings by moving steady-state capacity to contract terms and applying the break-even threshold to burst

If autoscaling data is not available, ask: "What percentage of time do your clusters scale beyond minimum replica count?" Then estimate based on that percentage.

Example savings calculation: If steady-state is 100 vCPUs on PAYGO and you move to a 1-year contract, you save (100 / 4) × ($1,500 − $1,000) = $12,500/year = ~$1,042/month.

Complexity: **Low** (administrative change; no infrastructure impact).

**Opportunity 3: Karpenter on ROSA HCP 4.22+**

Confirm or ask whether the target ROSA version is 4.22+. If the user has not yet migrated to HCP, state that Karpenter requires HCP as a prerequisite — surface this opportunity only after HCP migration is planned.

For HCP clusters, quantify each Karpenter sub-lever separately, then combine:

- **Bin-packing (~10% fewer nodes):** Apply 10% reduction to worker node EC2 cost and ROSA worker fee
- **Spot instances (~70% EC2 discount on burst):** Calculate burst capacity (max − min vCPUs) and apply 70% EC2 discount to the burst portion only; ROSA worker fee unchanged
- **ARM/Graviton (up to 40% better price-performance):** If target ARM percentage is provided, use Graviton performance multiplier E = 1.25. Required ARM nodes = x86_nodes / 1.25 (e.g., 100 x86 nodes → 80 ARM nodes). Apply EC2 rate difference: ARM General Purpose $0.040/vCPU-hr vs Intel $0.048/vCPU-hr. Combine the node-count reduction and the per-vCPU rate reduction for total savings on both EC2 and ROSA worker fee.
- **Scale-to-zero (dev/test clusters):** Ask how many clusters are non-production if `prod_clusters=N` is not provided. Estimate idle hours using the default: 12 hrs/day idle ≈ 50% reduction in EC2 + ROSA worker fee for non-production clusters. The HCP cluster fee ($0.25/hr) continues even at zero workers and is excluded from this saving.

Total Karpenter savings = sum of all four sub-levers.

Complexity: **Medium** (requires HCP migration first; Karpenter itself is low-config once on HCP).

**Opportunity 4: Right-size oversized machine pools**

Flag clusters with fewer than 16 worker vCPUs as consolidation candidates — these are likely cheaper to merge into a larger cluster than to run as standalone overhead. Do not fetch live utilization metrics. Surface as a prompt to review pool sizes; pools sized for historical peaks may be reduced if current workloads are smaller.

Complexity: **Low** (operational review; no infrastructure change required).

**Opportunity 5: Consolidate small clusters**

Identify clusters with low vCPU counts (e.g., <16 vCPUs) that may be cheaper to merge into larger clusters. Use the Classic→HCP savings per-cluster and per-node economics to estimate savings from reducing cluster count (fewer cluster fees or CP+infra overhead).

Complexity: **Medium** (requires cluster migration; potential application downtime during consolidation).

4. Rank all opportunities by estimated annual savings (highest first) and present as a table:

```
## Cost Optimization Recommendations

| # | Opportunity | Est. savings/mo | Est. savings/yr | Complexity |
|---|---|---|---|---|
| 1 | Migrate to HCP | $X | $X | Medium |
| 2 | 1yr contracts (steady state) | $X | $X | Low |
| 3 | Karpenter (bin-packing + ARM + Spot + scale-to-zero) | $X | $X | Medium |
| 4 | Right-size machine pools | Review recommended | — | Low |
| 5 | Consolidate small clusters | Review recommended | — | Medium |
```

For opportunities where a specific savings amount is not quantifiable (e.g., right-sizing or consolidation without detailed pool data), use "Review recommended" in the savings columns and omit the annual figure.

5. Follow with the Optimized TCO Table from the rosa-cost skill, showing current vs. optimized annual costs:

```
| | Current | HCP Optimized |
|---|---|---|
| Overhead (CP+Infra EC2+EBS or HCP cluster fee) | $X/yr | $X/yr |
| Steady workers (1yr contract, x86 or ARM) | $X/yr | $X/yr |
| Burst workers (PAYGO Spot, N days/month) | $X/yr | $X/yr |
| **Annual total** | **$X** | **$X** |
| **Annual savings** | | **$X (~Y%)** |
```

6. Follow with a 3–5 sentence narrative:
   - Total current fleet spend (monthly and annual)
   - Largest cost driver
   - Top recommendation with estimated annual savings
   - Implementation complexity and recommended phasing
   - Direct to `/rosa:cost-report` for a full strategic advisory report with a phased migration plan

Example narrative: "Your current fleet costs approximately $X/month ($Y/year). The largest cost driver is control-plane overhead on Classic clusters. Migrating all N Classic clusters to HCP saves approximately $Z/year with medium complexity. Pairing the HCP migration with Karpenter in 4.22+ and 1-year contracts for steady-state capacity can reduce your total fleet cost by $W/year. For a phased migration plan tailored to your infrastructure and business timeline, use `/rosa:cost-report`."

## Notes

- Cite https://aws.amazon.com/rosa/pricing/ when presenting results. Rates in this skill are current as of 2026-06 — direct users to verify current rates on the AWS pricing page before quoting to customers.
- If the user provides no fleet data, ask which input mode they prefer (Live, Detailed, or Estimate).
- If using Live mode, confirm `ocm whoami` succeeds before querying OCM.
- Ask for single-AZ or multi-AZ cluster topology if not inferable from OCM data.
- Ask for contract terms (PAYGO / 1yr / 3yr) for both ROSA fee and EC2 if not specified.
