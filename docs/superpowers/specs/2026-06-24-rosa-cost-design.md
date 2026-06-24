# ROSA Cost Estimation Plugin — Design Spec

**Date:** 2026-06-24
**Status:** Approved

## Summary

A new `rosa` plugin for the `mobb-skills` marketplace that helps users calculate costs for ROSA Classic and ROSA HCP clusters, compare the two architectures, and surface cost-optimization recommendations including Classic→HCP migration savings. Supports individual clusters and fleets of up to many clusters.

---

## Plugin Structure

```
plugins/rosa/
├── .claude-plugin/
│   └── plugin.json          # name=rosa, version=0.1.0, author=github.com/rh-mobb
├── commands/
│   ├── cost.md              # /rosa:cost — guided wizard
│   ├── cost-estimate.md     # /rosa:cost-estimate — calculate fleet costs
│   ├── cost-compare.md      # /rosa:cost-compare — Classic vs HCP side-by-side
│   └── cost-optimize.md     # /rosa:cost-optimize — savings recommendations
├── skills/
│   └── rosa-cost/
│       └── SKILL.md         # all pricing data, calculation logic, output templates
├── OWNERS                   # at least one GitHub username
└── README.md
```

The skill is the single source of truth for pricing and methodology. Commands are thin entry points that set the mode and delegate to the skill.

---

## The `rosa-cost` Skill

### 1. Pricing Tables (static, embedded in skill)

The skill must cite https://aws.amazon.com/rosa/pricing/ when presenting results and note that users should verify current rates there.

**ROSA service fees (Red Hat charge, uniform across all supported AWS standard Regions):**

| Charge | Rate | Applies to |
|---|---|---|
| Worker node fee | **$0.171/4-vCPU/hr** = **$1,500/4-vCPU/year** on-demand | Classic and HCP — worker nodes only; does not fractionalize below 4 vCPU |
| HCP cluster fee | **$0.25/cluster/hr** = **$2,190/cluster/year** | HCP only (in addition to worker fee); never discounted |
| Classic cluster fee | $0 | Classic has no cluster-level fee |

ROSA worker node service fee by contract term (per 4-vCPU block):

| Term | Hourly | Yearly |
|---|---|---|
| On-demand (PAYGO) | $0.171 | $1,500 |
| 1-year contract | $0.1142 | $1,000 |
| 3-year contract | $0.0761 | $667 |

**EC2 on-demand instance profile rates** (AWS compute cost, separate from ROSA fee):

| Profile | Rate ($/vCPU/hr) | Example instances | Notes |
|---|---|---|---|
| General Purpose (Intel) | $0.048 | m5, m6i, m7i | Hyperthreaded (1 vCPU = 0.5 physical core) |
| General Purpose (ARM/Graviton) | $0.040 | m6g, m7g | Physical cores; ~15–19% cheaper than Intel equivalent (19% on 1yr reserved m7g vs m7i); 20–30% faster per-core |
| Compute Optimized (Intel) | $0.0425 | c5, c6i, c7i | Hyperthreaded |
| Compute Optimized (ARM/Graviton) | $0.036 | c6g, c7g | Physical cores; ~15% cheaper |
| Memory Optimized (Intel) | $0.063 | r5, r6i, x1 | Hyperthreaded |
| Memory Optimized (ARM/Graviton) | $0.054 | r6g, r7g | Physical cores; ~15% cheaper |
| Bare Metal | $0.048 | *.metal | No hypervisor overhead |
| GPU Optimized | $0.1015 | p3, g4, inf1 | |

**Spot pricing** (available via Karpenter on ROSA HCP 4.22+):
- Spot EC2 discount: typically **60–90% off on-demand** EC2 price (variable; the skill uses 70% as a conservative default estimate)
- ROSA worker node fee applies at the **same rate** regardless of Spot or on-demand
- Spot instances carry interruption risk; suitable for stateless/fault-tolerant workloads

EC2 discount multipliers (applied to EC2 portion independently from ROSA fee discounts):

| Term | Multiplier |
|---|---|
| PAYGO (on-demand) | 1.0× |
| 1-year reserved | ~0.6× |
| 3-year reserved | ~0.4× |

Users may override any multiplier with a specific discount percentage or reserved instance price (e.g., `ec2_discount=40%`, `rh_discount=20%`).

**Default region:** us-east-1. All calculations use a single region for simplicity; users may note a different region but the rates table does not change per-region in this skill.

**Hours/month:** 730 (standard billing assumption).

### 2. Input Resolution — Three Modes

The skill detects which mode applies based on what the user provides:

| Mode | What the user provides | How the skill resolves it |
|---|---|---|
| **Live** | One or more cluster IDs | Runs `ocm list machinepool --cluster <ID>` per cluster, reads instance type and replica count, maps instance type to profile bucket, sums vCPUs |
| **Detailed** | Pool spec block (cluster name, instance type, replica count per pool) | Maps instance type to profile bucket and computes directly |
| **Estimate** | Cluster count + total vCPU budget | Uses General Purpose as the default profile; distributes vCPUs evenly across clusters |

When using Live mode, the skill requires the user to be logged into OCM (`ocm whoami` must succeed). If not, it instructs them to run `ocm login`.

For Live mode, instance type → profile mapping:
- `m*`, `t*`, `a*` families → General Purpose
- `c*` family → Compute Optimized
- `r*`, `x*`, `u*` families → Memory Optimized
- `metal` suffix → Bare Metal
- `p*`, `g*`, `inf*`, `trn*` families → GPU Optimized

### 3. Calculation Formula

Per cluster, per month (730 hrs). Output is broken into the same line items shown in the example pricing slide:

```
worker_vcpus       = sum of (replicas × vcpus_per_instance) across all worker pools
                     (control plane and infra nodes excluded — accounted for separately)

# Line item: Worker node fee (ROSA RH subscription — same for Classic and HCP)
# Billing unit: 4-vCPU blocks. PAYGO: $1,500/block/yr | 1yr: $1,000/block/yr | 3yr: $667/block/yr
# worker_vcpus must be a multiple of 4 (guaranteed for all standard ROSA instance types)
rosa_worker_fee_monthly = (worker_vcpus / 4) × (rosa_block_annual_rate / 12)

# Line item: Cluster fee
cluster_fee        = $0.25 × 730  (HCP only = $182.50/month); Classic = $0

# Line item: Worker node EC2 + EBS
worker_ec2         = worker_vcpus × ec2_profile_rate × ec2_discount_multiplier × 730
worker_ebs         = worker_node_count × worker_disk_gb × $0.08
worker_ec2_total   = worker_ec2 + worker_ebs

# Line item: Control plane EC2 + EBS (Classic only; HCP = $0)
cp_ec2             = 3 × 8 vCPUs × $0.048 × ec2_discount_multiplier × 730
cp_ebs             = 3 × 300 × $0.08
cp_total           = cp_ec2 + cp_ebs

# Line item: Infra node EC2 + EBS (Classic only; HCP = $0)
infra_count        = 2 (single-AZ) or 3 (multi-AZ)
infra_ec2          = infra_count × 4 vCPUs × $0.063 × ec2_discount_multiplier × 730
infra_ebs          = infra_count × 300 × $0.08
infra_total        = infra_ec2 + infra_ebs

Total monthly      = rosa_worker_fee + cluster_fee + worker_ec2_total
                   + cp_total + infra_total
```

Fleet total = sum of all per-cluster totals.

For HCP comparison using the same worker vCPU counts as Classic: HCP eliminates Classic control-plane and infra EC2 nodes from the customer bill (they run on shared Red Hat infrastructure). The skill quantifies this saving using the known ROSA Classic defaults:

| Node role | Count | Default instance | vCPUs | Profile |
|---|---|---|---|---|
| Control plane | 3 (always) | m5.2xlarge | 8 | General Purpose |
| Infra (single-AZ) | 2 | r5.xlarge | 4 | Memory Optimized |
| Infra (multi-AZ) | 3 | r5.xlarge | 4 | Memory Optimized |

The skill asks whether the cluster is single-AZ or multi-AZ (or infers it from OCM data in Live mode) to use the correct infra count. These instance sizes are ROSA defaults; users may override them if their cluster uses non-default sizes.

**Important:** Control plane and infra nodes carry no Red Hat subscription fee — only worker nodes do. The savings from eliminating these nodes is EC2 + EBS only.

All control plane and infra nodes use a 300 GB gp3 root volume ($0.08/GB-month in us-east-1).

Approximate savings per cluster per month when migrating Classic → HCP (PAYGO, us-east-1):

| Component | Single-AZ | Multi-AZ |
|---|---|---|
| EC2 (control plane, 3 × m5.2xlarge) | $841.92 | $841.92 |
| EC2 (infra, r5.xlarge × 2 or 3) | $368.64 | $552.96 |
| EBS (300 GB gp3 × 5 or 6 nodes) | $120.00 | $144.00 |
| **Total per cluster/month** | **~$1,331** | **~$1,539** |

These figures do not include any RH subscription savings (none apply to control plane/infra nodes) or the HCP fixed cluster fee ($0.25/hr = $182.50/month) which partially offsets the savings.

### 4. Output Templates

**Simple cost table** (used by `cost-estimate` and `cost-compare`) — per-cluster line items:

| | Classic | HCP |
|---|---|---|
| Cluster fee | $0 | $182.50/mo |
| Worker node fee (ROSA RH sub) | $X | $X |
| Control plane EC2 + EBS | $X | $0 |
| Infra node EC2 + EBS | $X | $0 |
| Worker node EC2 + EBS | $X | $X |
| **Total/month** | **$X** | **$X** |

For fleet output: one table per cluster, then a fleet summary row. Always show both monthly and annual totals.

**Optimized TCO table** (used by `cost-optimize`) — separates steady-state and burst capacity, shows annual cost:

| | Classic | HCP Optimized |
|---|---|---|
| Overhead (CP+Infra EC2+EBS / HCP cluster fee) | $X | $2,190 |
| Steady workers (1yr contract, x86 / ARM) | $X | $X |
| Burst workers (PAYGO Spot, N days/month) | $X | $X |
| **Total annual cost** | **$X** | **$X** |
| **Annual savings** | | **$X (~Y%)** |

Example (15 steady nodes + 10-node burst at 10 days/month, 1yr contract, multi-AZ):

| | Classic (x86) | HCP (ARM) |
|---|---|---|
| Overhead | $11,703 | $2,190 |
| 15 steady workers | $34,170 | $31,295 |
| 10-node Spot burst | $5,546 | $2,640 |
| **Annual total** | **$51,419** | **$36,125** |
| **Savings** | | **$15,294/yr (~30%)** |

**Narrative** (3–5 sentences):
- Total fleet spend at current configuration (annual)
- Largest cost driver
- Top recommendation with estimated annual savings
- Complexity note (low / medium / high to implement)

### 5. Migration Delta Logic (`cost-compare`)

Run the formula twice for the same worker vCPU counts — once as Classic, once as HCP. The side-by-side output uses the line-item format above, adding a **Savings/mo** and **Savings/yr** column.

HCP savings come from two sources:
1. Eliminating Classic control plane EC2 + EBS (~$842–$866/cluster/month for 3 × m5.2xlarge + 300 GB gp3)
2. Eliminating Classic infra node EC2 + EBS (~$344–$552/cluster/month for 2–3 × r5.xlarge + 300 GB gp3)

Partially offset by the new HCP cluster fee: $182.50/cluster/month.

Approximate net EC2+EBS savings (PAYGO, before HCP cluster fee offset):
- Single-AZ: ~$1,331/cluster/month → net ~$1,148/cluster/month after HCP fee
- Multi-AZ: ~$1,539/cluster/month → net ~$1,357/cluster/month after HCP fee

Narrative: "Migrating all N clusters to HCP saves approximately $X/month ($Y/year)."

The compare output also includes a qualitative HCP benefits summary (not costed, but noted for completeness):

| Feature | Classic | HCP | So what? |
|---|---|---|---|
| AWS Managed Policies | No | Yes | Zero trust / least privilege by default |
| BYO CNI (e.g. Cilium) | No | Yes | Bring preferred networking stack |
| Graviton/ARM CPU | No | Yes | Up to 40% better price-performance |
| Karpenter (as of 4.22) | No | Yes | Single NodePool; bin-packing, Spot+ARM with auto fallback, scale to zero |
| Zero Egress | No | Yes | No internet egress for base cluster operators — reduces AWS data transfer costs (not quantified) |
| Cluster provisioning speed | ~52 min | ~15 min | 3.5× faster — less idle time before cluster is usable |
| Node provisioning speed | ~9–23 min | ~5–18 min | ~4 min faster across all instance types — autoscaling responds faster, less time paying for nodes not yet serving traffic |

---

## Commands

### `/rosa:cost` — Guided Wizard

**Purpose:** Entry point for users who don't know which sub-command to use. Walks through data collection conversationally, then calls the same logic as the focused commands.

**Flow:**
1. Ask which input mode the user has (cluster IDs / pool spec / vCPU estimate)
2. Collect the required data for that mode
3. Ask about discount terms (PAYGO / 1yr / 3yr; any custom RH discount)
4. Produce: cost-estimate table → cost-compare table → optimization narrative

**Frontmatter:** `description:` only (no `argument-hint:` — conversational, not positional).

### `/rosa:cost-estimate` — Fleet Cost Calculation

**Purpose:** Calculate monthly costs for a fleet at its current configuration.

**Accepts:** Cluster IDs, pool-spec block, or vCPU estimate. Optional inline overrides: `discount=1yr`, `rh_discount=15%`.

**Output:** Cost table + short narrative.

### `/rosa:cost-compare` — Classic vs HCP Side-by-Side

**Purpose:** Show what the same fleet would cost as Classic vs HCP.

**Accepts:** Same inputs as `cost-estimate`.

**Output:** Side-by-side table with delta column (savings/mo, savings/yr). Narrative with fleet-level migration savings.

### `/rosa:cost-optimize` — Savings Recommendations + Strategic Advisory Report

**Purpose:** Rank savings opportunities and optionally generate a full strategic advisory report.

**Accepts:** Same inputs as `cost-estimate`, plus:
- `report=yes` — generate the full advisory report format (see below)
- `arm_pct=50` — target percentage of fleet to migrate to ARM (default 50%)
- `prod_clusters=N` — number of production clusters (affects migration phasing)

**Output (default):** Ranked list of recommendations, each with estimated monthly savings and implementation complexity (low / medium / high).

**Output (report mode):** Full **Strategic Advisory Report** matching the structure below. This is the primary deliverable for customer-facing engagements.

Standard opportunities surfaced:

1. **Migrate Classic clusters to HCP** — quantified EC2+EBS savings per cluster (see migration delta logic)

2. **Contract pricing for steady-state capacity** — for autoscaling clusters, split the analysis into two tiers:
   - *Steady-state* (min replica count / baseline vCPUs): recommend 1yr or 3yr contract
   - *Burst capacity* (max − min replicas): run break-even analysis

   **Break-even thresholds** (ROSA worker fee only — EC2 reserved instance analysis is separate):
   | Contract | Annual cost/4vCPU | PAYGO equivalent | Break-even utilization |
   |---|---|---|---|
   | 1-year | $1,000 | $1,500 × X | **>67% of year** |
   | 3-year | $667 | $1,500 × X | **>45% of year** |

   If the user reports that burst capacity runs above steady state more than the break-even threshold, the skill recommends committing to a contract for that tier too. Example: "You scale beyond steady state ~70% of the time — a 1-year contract for your burst vCPUs saves $X/year over PAYGO at that utilization."

   If autoscaling min/max data is available (Live mode via OCM, or user-provided), the skill surfaces this analysis automatically. Otherwise it asks the user to estimate what % of time their clusters scale beyond minimum.

3. **Karpenter on ROSA HCP 4.22+** — four compounding optimizations, each quantified separately and combined. Karpenter collapses what Classic requires as one MachineSet per (instance family × arch × AZ) permutation into a single NodePool that selects the optimal combination at scheduling time.

   **Classic operational complexity (context for migration argument):**
   - Spot on Classic: separate MachineSet per instance type × AZ; manual fallback logic
   - ARM on Classic: separate ARM MachineSet; workloads must target the correct pool
   - Spot + ARM on Classic: one MachineSet per (type × arch × AZ) = combinatorial growth
   - Spot interruption on Classic: Node Termination Handler (NTH) required separately

   **HCP + Karpenter eliminates all of the above operationally, and adds:**

   a. **Bin-packing efficiency**: Karpenter's superior bin-packing reduces required node count by ~10% vs the Classic autoscaler. Savings apply to both EC2 cost and ROSA worker fee (fewer vCPUs billed).

   b. **Spot instances**: Single NodePool with `capacity-type: spot,on-demand` — Karpenter provides automatic on-demand fallback. Native graceful drain on 2-min EC2 interruption notice (no NTH needed). EC2 Spot discount default: 70% off on-demand (user may override). ROSA worker fee applies at the same rate regardless of Spot or on-demand. The skill flags interruption risk and recommends Spot only for stateless/fault-tolerant workloads. Savings shown as EC2 delta only.

   c. **ARM/Graviton**: NodePool `arch: arm64` or `mixed` — Karpenter selects per workload. Graviton instances offer up to **40% better price-performance ratio** vs comparable x86 instances, and consume less energy. ARM vCPUs are physical cores (not hyperthreads), so compute-intensive workloads may achieve the same throughput with fewer vCPUs — reducing both EC2 cost and ROSA worker fee. The skill asks if the workload is CPU-bound and adjusts the vCPU estimate if confirmed.

   d. **Scale to zero**: Karpenter can scale worker nodes to **true zero** during idle periods (e.g., dev/test clusters overnight or on weekends). ROSA HCP cluster fee ($0.25/hr) continues even at zero workers. The skill asks if any clusters are non-production and estimates savings from an idle schedule (e.g., 12 hrs/day at zero workers = ~50% EC2 + ROSA worker fee reduction for those clusters).

   These levers are additive. Example combined output: "Migrating to HCP 4.22+ with Karpenter bin-packing (−10% nodes), ARM Graviton (up to −40% price-performance), Spot for burst capacity (−70% EC2 on burst), and zero-scale for dev clusters reduces your fleet cost by approximately $X/month."

   **Prerequisite**: Karpenter optimizations are only surfaced when the target is ROSA HCP 4.22+. The skill checks (or asks) whether the cluster version meets this requirement.

4. **Right-size oversized machine pools** — prompts user to review pool sizes; does not fetch live utilization metrics

5. **Consolidate very small clusters** — identifies clusters with low vCPU counts that may be cheaper to merge

---

## Strategic Advisory Report Format

When `report=yes` is passed to `/rosa:cost-optimize` (or the guided wizard elects report mode), the skill generates a structured advisory report with the following sections. All dollar figures are calculated from the fleet's actual inputs.

### Report Sections

**1. Executive Summary**
- Fleet profile header: cluster count, node count, vCPU count, active pods (if known)
- 3–4 bullet outcomes with quantified savings: overhead reduction, monthly run-rate reduction, compute throughput improvement, Karpenter optimization

**2. Fleet Profile and Operational Challenges**
- Workload topology diagram (prod vs non-prod cluster split, node/vCPU counts)
- Challenge 1: Dedicated control plane cost overhead (N clusters × management nodes = $X/month wasted)
- Challenge 2: Hardware thread contention on x86 (vCPUs = physical cores ÷ 2 due to hyperthreading)
- Challenge 3: Capacity fragmentation in MachineSets (rigid scaling, allocation slack)

**3. Cost Analysis and Unit Economics**
Per-node unit costs used throughout the report:

| Cost Component | x86 (C_x86) | ARM (C_ARM) |
|---|---|---|
| EC2 (1yr reserved, m7i.xlarge / m7g.xlarge) | $90.83/month | $73.58/month |
| EBS (300 GB gp3) | $24.00/month | $24.00/month |
| ROSA worker node fee (1yr, 4 vCPU block) | $83.34/month | $83.34/month |
| **Total per node/month** | **$198.17** | **$180.92** |

Classic cluster overhead (C_Classic): **$975.25/month** (multi-AZ, 1yr reserved EC2+EBS for CP+infra)
HCP cluster fee (C_HCP): **$182.50/month** ($0.25/hr)

**Graviton Performance Multiplier:**
- E = 1.25 (Graviton3 provides up to 25% compute throughput improvement for CPU-bound workloads)
- Required ARM nodes = x86 nodes / E (e.g. 375 x86 nodes → 300 ARM nodes)
- Node reduction savings = (x86_nodes − arm_nodes) × C_ARM/month
- This is surfaced as "additional unbudgeted savings" on top of the raw EC2 discount

**4. Phased Migration Strategy**
Two-phase plan customized to the fleet:

- **Phase 1 (Months 1–6): HCP Structural Migration** — migrate all clusters to HCP keeping x86, capture immediate overhead savings, no app changes required
  - Phase 1A (Months 1–2): Pilot wave — 3 non-prod clusters with buffer
  - Phase 1B (Months 3–4): Non-prod wave — remaining non-prod clusters
  - Phase 1C (Months 5–6): Production cutover — production clusters with safety buffer nodes
- **Phase 2 (Months 7–18): Compute Modernization** — migrate target % of fleet to ARM + implement Karpenter
  - Phase 2A (Months 7–9): CI/CD pipeline readiness, multi-arch images, Karpenter init
  - Phase 2B (Months 10–12): Non-prod stateless workloads to ARM
  - Phase 2C (Months 13–18): Production cluster waves to ARM

Phase timing adjusts based on fleet size and prod/non-prod split.

**5. Projected Migration Timeline and Cost Analysis**
Month-by-month table showing Classic spend declining and HCP spend rising as clusters migrate:

| Month | Phase | Classic Spend | HCP Spend | Total Bill |
|---|---|---|---|---|
| 0 | Baseline | $X | $0 | $X |
| 1 | Phase 1A: Deploy pilot targets | $X | $X | $X |
| 2 | Phase 1A complete: N clusters deleted | $X | $X | $X |
| ... | ... | ... | ... | ... |
| 6 | Fleet 100% on HCP x86 | $0 | $X | $X |
| 18 | 50% fleet on ARM | $0 | $X | $X |

The table tracks overlapping dual-run costs (migration buffer nodes) during cutover months.

**6. Financial and Operational Value Realization**
- Phase 1 savings: $X/month reduction (overhead elimination, no app changes)
- Phase 2 savings: additional $X/month (ARM discount + node reduction)
- Combined: $X/month total savings vs baseline
- Karpenter consolidation bonus: 10% node reduction × C_ARM = additional $X/year unbudgeted

**7. Performance and Reliability Enhancements**
- Dedicated cores vs hyperthreading (1 ARM vCPU = 1 physical core)
- DDR5 memory bandwidth on Graviton3 (m7g) — 50% higher than DDR4
- Karpenter scale-up: <45 seconds vs 3–4 minutes for Classic ASG
- Karpenter consolidation: automatic bin-packing, zero manual intervention
- Blast radius reduction: control plane out of customer AWS account

**8. Next Steps and Recommendations**
3–4 actionable items to initiate Phase 1A (IAM roles, pilot cluster provisioning, MTC connectivity, migration playbook approval).

---

## Constraints and Assumptions

- Currency: USD only
- Region: us-east-1 assumed; rates do not vary per-region within this skill
- Control plane and infra nodes: excluded from Classic worker cost calculations (they are ROSA-managed overhead), but their EC2 and EBS costs ARE included in the Classic→HCP savings calculation using known ROSA defaults (m5.2xlarge × 3 control plane, r5.xlarge × 2–3 infra, 300 GB gp3 root volume per node). No RH subscription fee applies to these nodes — savings are EC2 + EBS only. Users may override instance sizes if their cluster uses non-defaults.
- vCPU counts for Live mode come from `ocm list machinepool` replica counts — not live node metrics
- Discount multipliers are approximations; users with custom EDP or private pricing should override with explicit percentages
- The skill does not make API calls to AWS Pricing API — it uses the embedded rate table

---

## Files to Create

| File | Notes |
|---|---|
| `plugins/rosa/.claude-plugin/plugin.json` | name, description, version, author |
| `plugins/rosa/skills/rosa-cost/SKILL.md` | full skill content |
| `plugins/rosa/commands/cost.md` | guided wizard |
| `plugins/rosa/commands/cost-estimate.md` | fleet cost calculation |
| `plugins/rosa/commands/cost-compare.md` | Classic vs HCP compare |
| `plugins/rosa/commands/cost-optimize.md` | savings recommendations |
| `plugins/rosa/commands/cost-report.md` | full strategic advisory report (Classic→HCP migration only; not for greenfield customers) |
| `plugins/rosa/OWNERS` | GitHub username(s) |
| `plugins/rosa/README.md` | plugin docs |
