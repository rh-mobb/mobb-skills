# ROSA Cost Optimization — Red Truck Logistics

**Date:** 2026-06-26
**Command:** /rosa:cost-optimize
**Rates:** EC2 on-demand sourced from AWS Pricing API. ROSA fees current as of 2026-06 — verify at https://aws.amazon.com/rosa/pricing/ before quoting.
**Baseline:** $142,595/mo ($1,711,140/yr) — us-east-1, 1-year contracts. See [2026-06-26-cost-analysis.md](2026-06-26-cost-analysis.md) for full baseline detail.

---

## Graviton ARM Rates Used (us-east-1, on-demand)

| Instance | vCPU | On-demand/hr | $/vCPU/hr | vs. x86 equivalent |
|---|---|---|---|---|
| r7g.2xlarge (Memory Opt ARM) | 8 | $0.4536 | $0.0567 | vs. r6i $0.0630 → **−10%** |
| r7g.4xlarge (Memory Opt ARM) | 16 | $0.9072 | $0.0567 | vs. r6i $0.0630 → **−10%** |
| m7g.xlarge (General Purpose ARM) | 4 | $0.1632 | $0.0408 | vs. m6i $0.0480 → **−15%** |

_With Graviton E = 1.25 performance multiplier: 100 x86 vCPUs → 80 ARM vCPUs for equivalent throughput. Combined rate savings × node count reduction = 20–30% total Memory Optimized EC2 reduction._

---

## Cost Optimization Recommendations

| # | Opportunity | Est. savings/mo | Est. savings/yr | Complexity | Prerequisite |
|---|---|---|---|---|---|
| 1 | Upgrade steady-state to 3yr contracts | ~$28,000 | ~$336,000 | **Low** | None — today |
| 2 | Classic→HCP migration (8 clusters) | $6,380 | $76,560 | **Medium** | None |
| 3 | Karpenter (bin-packing + ARM + Spot + scale-to-zero) | ~$27,500 | ~$330,000 | **Medium** | HCP migration (#2) |
| 4 | Right-size small clusters | Review recommended | — | **Low** | None |

_Items 2 and 3 are sequential: HCP migration (#2) unlocks Karpenter (#3). Combined Phase 1+2 savings: ~$742,000/yr (−43%). Recommended execution order: 1 → 2 → 3._

---

## Opportunity Detail

### 1. 3-year contract upgrade — ~$336,000/yr | Low complexity | Today

**Mechanism:** ~2,200 vCPUs of steady-state capacity are on 1-year ROSA and EC2 contracts. Upgrading to 3-year terms reduces both fees with zero infrastructure change.

| Component | Calculation | Savings/mo |
|---|---|---|
| ROSA fee (1yr→3yr, $6.94/vCPU/mo delta) | 2,200 × $6.94 | $15,268 |
| r5/r6i EC2 (1yr→3yr, ~2,000 vCPU @ $0.063 OD) | 2,000 × $0.063 × 0.20 × 730 | $9,198 |
| m6i/m5 EC2 (1yr→3yr, ~200 vCPU @ $0.048 OD) | 200 × $0.048 × 0.20 × 730 | $1,402 |
| **Total** | | **~$25,868/mo ≈ ~$28,000/mo = ~$336,000/yr** |

**Burst assessment:** prod-core-1 and prod-core-2 together run ~200 vCPUs above autoscaling minimums. At >45% annualized utilization, 3-year contracts are cost-effective on burst capacity too. Recommend pulling 90-day CloudWatch utilization before committing burst vCPUs.

**Exclusions:** dev-core-1 and dev-batch-1 (128 combined vCPU) are unlikely to be steady-state; keep on 1yr terms or PAYGO until utilization patterns are confirmed.

---

### 2. Classic→HCP migration (8 clusters) — $76,560/yr | Medium | Enables Karpenter (#3)

All 8 Classic clusters are multi-AZ. Each carries $980/mo in CP+Infra EC2+EBS overhead. HCP eliminates this and replaces it with the $182.50/mo HCP cluster fee.

| Metric | Per cluster | 8 clusters |
|---|---|---|
| CP+Infra eliminated | $980/mo | $7,840/mo |
| HCP cluster fee | ($182.50)/mo | ($1,460)/mo |
| **Net savings** | **$797.50/mo** | **$6,380/mo = $76,560/yr** |

In addition, HCP migration:
- Enables Karpenter (#3) — the ~$330,000/yr opportunity
- Reduces provisioning time from ~52 min to ~15 min per cluster
- Enables AWS Managed Policies, BYO CNI, and zero egress for cluster operators

**Recommended migration order** (smallest first to minimize blast radius): dev-batch-1 (48 vCPU) → dev-core-1 (80 vCPU) → prod-batch-2 (96 vCPU) → prod-batch-1 (200 vCPU) → prod-infra-1 (192 vCPU) → prod-data-1 (112 vCPU) → prod-core-2 (800 vCPU) → prod-core-1 (1,200 vCPU).

---

### 3. Karpenter on ROSA HCP 4.22+ — ~$330,000/yr | Medium | Requires HCP migration (#2)

_Prerequisite: all Classic clusters must be migrated to HCP before Karpenter is available on those workloads._

#### 3a. Bin-packing (~10% fewer nodes)

| Component | Calculation | Savings/mo |
|---|---|---|
| Worker EC2+EBS (10% of $74,830/mo) | $74,830 × 10% | $7,483 |
| ROSA worker fee (10% of $56,833/mo) | $56,833 × 10% | $5,683 |
| **Subtotal** | | **$13,166/mo = $157,992/yr** |

#### 3b. ARM/Graviton (50% of fleet migrated to r7g)

Post bin-packing: ~2,455 effective vCPUs. 50% ARM = ~1,228 x86 vCPUs migrated.
With E = 1.25 multiplier: 1,228 x86 → 982 ARM vCPUs (246 vCPU reduction).

| Component | Calculation | Savings/mo |
|---|---|---|
| EC2 rate savings (x86 r6i → ARM r7g) | 1,228 × ($0.063 − $0.0567) × 0.6 × 730 | $3,383 |
| Fewer vCPUs (246 × $0.0567 × 0.6 × 730) | Included in above | — |
| ROSA fee savings (246 fewer vCPUs, 3yr) | 246 × $13.89/mo | $3,417 |
| **Subtotal** | | **$6,800/mo = $81,600/yr** |

#### 3c. Spot instances for burst (~528 vCPU burst capacity)

Karpenter's single NodePool enables `capacity-type: spot,on-demand` with automatic on-demand fallback.

| Component | Calculation | Savings/mo |
|---|---|---|
| Burst EC2 1yr reserved → Spot (~70% of OD) | 528 vCPU × $0.063 OD × (0.6−0.3) × 730 | $7,298 |
| Bin-packing on burst | 10% fewer burst nodes | $1,640 |
| **Subtotal** | | **$8,938/mo = $107,256/yr** |

_Spot carries interruption risk. Recommended only for stateless and fault-tolerant workloads._

#### 3d. Scale-to-zero for non-production clusters

| Cluster | vCPU | Worker EC2+ROSA/mo | 50% idle savings/mo | 50% idle savings/yr |
|---|---|---|---|---|
| hcp-poc-1 | 32, t3.xlarge | $1,314 | **$657** | **$7,884** |
| hcp-dev-1 | 12, m5.xlarge | $527 | **$264** | **$3,168** |
| **Combined** | | | **$921** | **$11,052** |

_HCP cluster fee ($183/mo each) continues at zero workers — excluded from savings._

#### Karpenter combined savings

| Sub-lever | Savings/mo | Savings/yr |
|---|---|---|
| a. Bin-packing | $13,166 | $157,992 |
| b. ARM Graviton 50% | $6,800 | $81,600 |
| c. Spot for burst | $8,938 | $107,256 |
| d. Scale-to-zero (poc + dev) | $921 | $11,052 |
| **Total Karpenter** | **~$29,825** | **~$357,900** |

_Sub-levers interact marginally; conservative combined estimate: ~$27,500/mo = ~$330,000/yr._

---

### 4. Right-size small clusters — Review recommended | Low

| Cluster | vCPU | CP+Infra/mo | Overhead ratio |
|---|---|---|---|
| dev-batch-1 | 48 | $980 | 32% of total cost |
| prod-batch-2 | 96 | $980 | 17% of total cost |

dev-batch-1 has the highest overhead ratio in the fleet. Post-HCP-migration, the cluster fee drops to $183/mo (6% of cost). If dev-batch-1 and dev-core-1 could share a node pool, one cluster registration could be eliminated entirely, saving a further $183/mo.

---

## Optimized TCO Table

Scenario: Full Phase 1 + Phase 2 applied (3yr contracts, HCP migration, Karpenter bin-packing + ARM 50% + Spot burst + scale-to-zero).

| | Current (1yr, Classic+HCP) | Optimized (3yr + HCP + Karpenter) |
|---|---|---|
| Overhead (CP+Infra or HCP cluster fee) | $100,668/yr | $19,716/yr |
| Steady workers (ROSA + EC2, 3yr, post-optimization) | $1,199,052/yr | ~$640,000/yr |
| Burst workers (Spot + ROSA, scale-to-zero) | $411,420/yr | ~$234,000/yr |
| **Annual total** | **$1,711,140/yr** | **~$894,000/yr** |
| **Annual savings** | | **~$817,000/yr (~48%)** |

---

## Recommended Execution Phases

| Phase | Actions | Annual savings | Complexity |
|---|---|---|---|
| **Phase 0 — Today** | Upgrade ~2,200 vCPU steady-state to 3yr contracts | ~$336,000 | Low |
| **Phase 1 — Q3 2026** | Migrate 8 Classic clusters to HCP (smallest first) | $76,560 | Medium |
| **Phase 2 — Q4 2026** | Enable Karpenter 4.22+: bin-packing, ARM, Spot, scale-to-zero | ~$330,000 | Medium |
| **Combined** | All phases complete | **~$742,560/yr** | |

---

## Narrative

Red Truck Logistics is spending **$142,595/month ($1,711,140/year)** on ROSA across 11 clusters at us-east-1 on-demand rates with 1-year reserved contracts. The dominant cost is prod-core-1 at $59,714/month (43% of Classic spend). The highest-ROI action available today — with zero infrastructure risk — is upgrading the ~2,200 vCPUs of steady-state capacity to 3-year contracts, saving **~$336,000/year** through administrative changes alone. Migrating the 8 Classic clusters to HCP (recommended order: smallest first, ~Q3 2026) saves an additional $76,560/year and unlocks the Karpenter opportunity. Post-migration on ROSA 4.22+, enabling Karpenter with bin-packing, ARM Graviton on 50% of the Memory Optimized fleet, and Spot for burst workloads saves approximately **$330,000/year**. Executing all three phases reduces the annual fleet cost from **$1,711,140 to approximately $894,000 — a 48% reduction totaling ~$817,000/year in savings**.
