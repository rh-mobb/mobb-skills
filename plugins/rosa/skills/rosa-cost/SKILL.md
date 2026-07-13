---
name: rosa-cost
description: |
  Two-phase advisory skill for ROSA cost analysis and per-cluster optimization.

  Phase 1 — Cost Analysis:
  - Estimate ROSA Classic or HCP cluster costs for individuals or fleets
  - Compare Classic vs HCP costs with a savings delta
  - Identify top optimization opportunities (contracts, Karpenter, ARM, Spot)
  - Generate strategic cost reports for Classic→HCP migration engagements

  Phase 2 — Per-Cluster Optimization Guide:
  - Machine pool breakdown tables per cluster (instance, vCPU, GiB, min→max nodes/vCPU)
  - Ordered recommendations per cluster (🟢 Quick / 🟡 Medium / 🔴 Long-term)
  - Confirmed instance pricing via AWS Pricing MCP
  - Fleet summary tables across all effort levels

  Handles three input modes: live OCM cluster IDs, detailed pool specs, or high-level vCPU estimates.

  Self-improving: add confirmed pricing and engagement lessons to the registry sections after each engagement so the skill improves over time.

  NOT for: General AWS pricing questions or non-ROSA OpenShift deployments.
license: Apache-2.0
user_invocable: false
model: inherit
color: "#cc0000"
allowed-tools: []
---

# ROSA Cost Reference

Cite https://aws.amazon.com/rosa/pricing/ when presenting results. Rates in this skill are current as of 2026-06 — direct users to verify current rates on the AWS pricing page before quoting to customers.

## ROSA Service Fees

Red Hat charges these fees uniformly across all supported AWS standard Regions.

### Worker Node Fee

Billing unit: 4-vCPU block. Does not fractionalize below 4 vCPU.

| Term | Hourly rate | Annual rate per 4-vCPU block |
|---|---|---|
| On-demand (PAYGO) | $0.171 | $1,500 |
| 1-year contract | $0.1142 | $1,000 |
| 3-year contract | $0.0761 | $667 |

1-year contracts save 33% off on-demand. 3-year contracts save 55%. Discounts apply to worker node fee only.

### HCP Cluster Fee

$0.25/cluster/hr = $182.50/cluster/month = $2,190/cluster/year.

This fee applies to HCP clusters only. Classic clusters have no cluster-level fee. The HCP cluster fee is never discounted — it applies regardless of ROSA contract term.

## EC2 Instance Profile Rates

AWS compute cost, billed separately from the ROSA service fee.

| Profile | $/vCPU/hr | Example instances | Notes |
|---|---|---|---|
| General Purpose (Intel/x86) | $0.048 | m5, m6i, m7i | Hyperthreaded — 1 vCPU = 0.5 physical core |
| General Purpose (ARM/Graviton) | $0.040 | m6g, m7g | Physical cores; 19% cheaper than Intel equivalent (1yr reserved m7g vs m7i); 20–30% faster per-core |
| Compute Optimized (Intel) | $0.0425 | c5, c6i, c7i | Hyperthreaded |
| Compute Optimized (ARM) | $0.036 | c6g, c7g | Physical cores; ~15% cheaper than Intel equivalent |
| Memory Optimized (Intel) | $0.063 | r5, r6i, x1 | Hyperthreaded |
| Memory Optimized (ARM) | $0.054 | r6g, r7g | Physical cores; ~15% cheaper than Intel equivalent |
| Bare Metal | $0.048 | *.metal | No hypervisor overhead |
| GPU Optimized | $0.1015 | p3, g4, inf1 | |

Rates above are on-demand. Apply the EC2 discount multiplier for reserved instances:

| EC2 term | Multiplier |
|---|---|
| On-demand | 1.00× |
| 1-year reserved | 0.60× |
| 3-year reserved | 0.40× |

Users with custom EDP or private pricing should override with an explicit percentage (e.g., `ec2_discount=45%`).

## Spot Instances

Available via Karpenter on ROSA HCP 4.22+.

- Spot EC2 discount: **70% off on-demand** EC2 (conservative default; actual savings vary 60–90%).
- ROSA worker node fee applies at the same rate for Spot and on-demand instances.
- Spot instances carry interruption risk. Recommend Spot only for stateless and fault-tolerant workloads.
- On ROSA HCP 4.22+, Karpenter provides automatic on-demand fallback and native graceful drain on the 2-minute EC2 interruption notice. No Node Termination Handler needed.

## EBS Storage

gp3 pricing varies by region. Common rates:

| Region | $/GB-month | $/node/month (300 GB) |
|---|---|---|
| us-east-1 (N. Virginia) | $0.08 | $24.00 |
| ap-northeast-1 (Tokyo) | $0.088 | $26.40 |
| ap-northeast-3 (Osaka) | $0.088 | $26.40 |
| ap-southeast-2 (Sydney) | $0.096 | $28.80 |
| eu-west-1 (Ireland) | $0.088 | $26.40 |

For other regions, look up the current gp3 rate using the AWS Pricing MCP tool (`get_pricing` with service code `AmazonEC2`, filter `storageClass=General Purpose`, `volumeType=gp3`).

Default root volume: **300 GB gp3** per node (applies to control plane, infra, and worker nodes unless the user overrides).

## ROSA Classic Node Defaults

Control plane and infra nodes carry no ROSA worker node fee. The savings from eliminating them in HCP are EC2 cost and EBS cost only.

| Node role | Count | Default instance | vCPUs | Profile |
|---|---|---|---|---|
| Control plane | 3 (always) | m5.2xlarge | 8 | General Purpose |
| Infra (single-AZ) | 2 | r5.xlarge | 4 | Memory Optimized |
| Infra (multi-AZ) | 3 | r5.xlarge | 4 | Memory Optimized |

Ask the user whether their clusters are single-AZ or multi-AZ when not available from OCM data, to use the correct infra count. Users may override instance sizes if their cluster uses non-default sizes.

## Input Resolution

Detect the input mode from what the user provides.

### Live Mode — Cluster IDs

Use the **ocm-cli skill** for all OCM interactions: profile resolution, login confirmation, Classic vs HCP detection, and machine pool / node pool retrieval. Refer to that skill for the exact commands.

For each cluster ID, extract:
- Cluster type (Classic or HCP) — from `hypershift.enabled` in cluster describe JSON
- Instance type per pool — for EC2 profile mapping (see table below)
- Replica count or autoscaling min/max per pool
- **Actual running vCPU if available** — prefer this over autoscaler min as the steady-state input; clusters typically run well above their minimum. Ask the user to check Hybrid Cloud Console analytics (console.redhat.com → Clusters → cluster → Overview → vCPU usage) or Telesense (internal Red Hat analytics) for the current Worker vCPUs figure. If not available, use autoscaler min and note the assumption.
- AZ count — determines infra node count for Classic (2 = single-AZ, 3 = multi-AZ)
- AZ topology per cluster — add `az: "single"` or `az: "multi"` to each Classic cluster entry.
  Read from `index.md` Fleet Profile (`**AZ topology:**` line). HCP clusters omit this field.

All customer-provisioned node pools in HCP incur the ROSA worker node fee regardless of their Kubernetes label. In Classic, infra nodes are RH-managed and free; in HCP, that overhead moves to Red Hat's account — every pool the customer provisions is billed as a worker node.

Map instance type family to profile:
- `m*`, `t*`, `a*` → General Purpose
- `c*` → Compute Optimized
- `r*`, `x*`, `u*` → Memory Optimized
- `*.metal` suffix → Bare Metal
- `p*`, `g*`, `inf*`, `trn*` → GPU Optimized

`arm64` architecture → use the ARM rate for that profile. Default is Intel/x86.

Read AZ count from cluster description to determine infra node count (2 = single-AZ, 3 = multi-AZ).

### Detailed Mode — Pool Spec Block

The user provides cluster name, instance type, and replica count per pool. Map instance type to profile using the rules above. Compute vCPUs per pool and sum across pools.

### Estimate Mode — vCPU Budget

The user provides cluster count and total vCPU budget. Use General Purpose Intel as the default profile. Distribute vCPUs evenly across clusters.

## Calculation Formula

Per cluster, per month (730 hours). Compute these line items in order.

```
worker_vcpus      = sum of (replicas × vcpus_per_instance) across all worker pools
                    (CP and infra nodes excluded — handled separately below)

# Worker node fee — same for Classic and HCP
rosa_block_annual = $1,500 (PAYGO) | $1,000 (1yr) | $667 (3yr)
rosa_worker_fee   = (worker_vcpus / 4) × (rosa_block_annual / 12)

# Cluster fee
cluster_fee       = $182.50/month (HCP only); $0 for Classic

# Worker node EC2 + EBS
worker_ec2        = worker_vcpus × ec2_profile_rate × ec2_discount_multiplier × 730
worker_ebs        = worker_node_count × worker_disk_gb × $0.08
worker_ec2_total  = worker_ec2 + worker_ebs

# Control plane EC2 + EBS — Classic only; HCP = $0 (CP runs on shared RH infrastructure)
cp_ec2            = 3 × 8 × $0.048 × ec2_discount_multiplier × 730
cp_ebs            = 3 × 300 × $0.08
cp_total          = cp_ec2 + cp_ebs

# Infra node EC2 + EBS — Classic only; HCP = $0
infra_count       = 2 (single-AZ) or 3 (multi-AZ)
infra_ec2         = infra_count × 4 × $0.063 × ec2_discount_multiplier × 730
infra_ebs         = infra_count × 300 × $0.08
infra_total       = infra_ec2 + infra_ebs

# Per-cluster total
cluster_total     = rosa_worker_fee + cluster_fee + worker_ec2_total + cp_total + infra_total
```

Fleet total = sum of all per-cluster totals.

## Output Templates

### Simple Cost Table

Use for `cost-estimate` output. Show per-cluster line items, then a fleet summary row.

```
| | Classic | HCP |
|---|---|---|
| Cluster fee | $0 | $182.50/mo |
| Worker node fee (ROSA) | $X | $X |
| Control plane EC2 + EBS | $X | $0 |
| Infra node EC2 + EBS | $X | $0 |
| Worker node EC2 + EBS | $X | $X |
| **Total/month** | **$X** | **$X** |
| **Total/year** | **$X** | **$X** |
```

Show the column for the architecture being estimated (Classic or HCP). For `cost-compare`, show both columns with an additional Savings column:

```
| | Classic | HCP | Savings/mo | Savings/yr |
|---|---|---|---|---|
| Cluster fee | $0 | $182.50 | ($182.50) | ($2,190) |
| Worker node fee | $X | $X | $0 | $0 |
| CP EC2 + EBS | $X | $0 | $X | $X |
| Infra EC2 + EBS | $X | $0 | $X | $X |
| Worker EC2 + EBS | $X | $X | $0 | $0 |
| **Total** | **$X** | **$X** | **$X** | **$X** |
```

### Optimized TCO Table

Use for `cost-optimize` output. Separates steady-state and burst capacity.

```
| | Classic | HCP Optimized |
|---|---|---|
| Overhead (CP+Infra EC2+EBS or HCP cluster fee) | $X/yr | $2,190/yr |
| Steady workers (1yr contract, x86 or ARM) | $X/yr | $X/yr |
| Burst workers (PAYGO Spot, N days/month) | $X/yr | $X/yr |
| **Annual total** | **$X** | **$X** |
| **Annual savings** | | **$X (~Y%)** |
```

### Narrative

Always include a 3–5 sentence narrative after any cost table:
- Total fleet spend at the current configuration (monthly and annual)
- Largest cost driver
- Top recommendation with estimated annual savings
- Implementation complexity (low / medium / high)

## Classic→HCP Savings Per Cluster

Approximate savings from eliminating Classic CP and infra nodes. EC2 and EBS only — no ROSA fee savings on these nodes.

| Component | Single-AZ | Multi-AZ |
|---|---|---|
| CP EC2 (3 × m5.2xlarge, PAYGO) | $841.92/mo | $841.92/mo |
| Infra EC2 (2–3 × r5.xlarge, PAYGO) | $368.64/mo | $552.96/mo |
| EBS (300 GB × 5–6 nodes) | $120.00/mo | $144.00/mo |
| Gross savings | ~$1,331/mo | ~$1,539/mo |
| Less HCP cluster fee | ($182.50/mo) | ($182.50/mo) |
| **Net savings/cluster/month** | **~$1,148** | **~$1,357** |

## HCP Qualitative Benefits

Include this table in `cost-compare` output after the cost table:

| Feature | Classic | HCP | Benefit |
|---|---|---|---|
| AWS Managed Policies | No | Yes | Zero trust / least privilege by default |
| BYO CNI (e.g. Cilium) | No | Yes | Bring preferred networking stack |
| Graviton/ARM CPU | No | Yes | Up to 40% better price-performance |
| Karpenter (ROSA 4.22+) | No | Yes | Single NodePool; bin-packing, Spot+ARM, auto fallback, scale to zero |
| Zero Egress | No | Yes | No internet egress for base cluster operators |
| Cluster provisioning | ~52 min | ~15 min | 3.5× faster |
| Node provisioning | ~9–23 min | ~5–18 min | ~4 min faster |

## Break-Even Analysis for Contract Pricing

For autoscaling clusters, split steady-state and burst tiers.

Steady-state capacity (min replicas) → recommend 1yr or 3yr contract.

Burst capacity (max − min replicas) → apply break-even analysis:

| Contract | Annual cost/4-vCPU | PAYGO annual | Break-even utilization |
|---|---|---|---|
| 1-year | $1,000 | $1,500 | >67% of year |
| 3-year | $667 | $1,500 | >45% of year |

When burst utilization exceeds the break-even threshold, recommend a contract for burst vCPUs. Example language: "You scale beyond steady state ~70% of the time — a 1-year contract for your burst vCPUs saves $X/year over PAYGO at that utilization."

When autoscaling min/max data is available from OCM (Live mode) or user-provided, surface this analysis automatically. Otherwise ask the user to estimate what percentage of time their clusters scale beyond minimum.

## Karpenter Optimization Details

Karpenter is available on ROSA HCP 4.22+. Confirm or ask whether the target version meets this requirement before surfacing Karpenter savings.

Karpenter collapses what Classic requires as one MachineSet per (instance family × arch × AZ) permutation into a single NodePool that selects the optimal instance at scheduling time.

**Classic MachineSet complexity (context for the migration argument):**
- Spot on Classic: separate MachineSet per instance type × AZ with manual fallback logic
- ARM on Classic: separate ARM MachineSet; workloads must target it explicitly
- Spot + ARM on Classic: one MachineSet per (type × arch × AZ) = combinatorial growth
- Spot interruption on Classic: Node Termination Handler (NTH) required as a separate component

**HCP + Karpenter optimizations (quantify each separately, then combine):**

**a. Bin-packing efficiency (~10% fewer nodes)**
Karpenter's bin-packing reduces required node count by approximately 10% vs the Classic autoscaler. Savings apply to both EC2 cost and ROSA worker fee (fewer vCPUs billed).

**b. Spot instances (~70% EC2 discount on burst)**
Single NodePool with `capacity-type: spot,on-demand`. Karpenter provides automatic on-demand fallback. Native graceful drain on the 2-minute EC2 interruption notice. Recommend Spot only for stateless or fault-tolerant workloads. ROSA worker fee unchanged on Spot.

**c. ARM/Graviton (up to 40% better price-performance)**
NodePool with `arch: arm64` or mixed. ARM vCPUs are physical cores, not hyperthreads — compute-intensive workloads achieve equivalent throughput with fewer vCPUs, reducing both EC2 and ROSA worker fee.

Graviton performance multiplier: E = 1.25
Required ARM nodes = x86_nodes / 1.25
Example: 375 x86 nodes → 300 ARM nodes = 75 node reduction = additional savings on top of the EC2 rate difference.

**d. Scale to zero (dev/test clusters)**
Karpenter scales worker nodes to zero during idle periods. The HCP cluster fee ($0.25/hr) continues at zero workers. Ask how many clusters are non-production and estimate idle hours. Example: 12 hrs/day idle = ~50% reduction in EC2 + ROSA worker fee for those clusters.

**Combined output format:**
"Migrating to HCP 4.22+ with Karpenter bin-packing (−10% nodes), ARM Graviton (up to −40% price-performance), Spot for burst (−70% EC2 on burst), and zero-scale for dev clusters reduces fleet cost by approximately $X/month."

## Unit Economics Reference

Per-node costs at 1-year contract terms, 4 vCPUs (m7i.xlarge / m7g.xlarge):

| Component | x86/Intel | ARM/Graviton |
|---|---|---|
| EC2 (1yr reserved, m7i.xlarge / m7g.xlarge) | $90.83/mo | $73.58/mo |
| EBS (300 GB gp3) | $24.00/mo | $24.00/mo |
| ROSA worker node fee (1yr, 4-vCPU block) | $83.34/mo | $83.34/mo |
| **Total per node/month** | **$198.17** | **$180.92** |

Classic cluster overhead (multi-AZ, 1yr reserved EC2+EBS for CP+infra): **$975.25/cluster/month** = **$11,703/cluster/year**
HCP cluster fee: **$182.50/cluster/month** = **$2,190/cluster/year**

## Phase 2: Per-Cluster Optimization Guide

Generate this after the cost analysis (`YYYY-MM-DD-cost-analysis.md`) is complete and indexed. Output file: `reports/<customer>/YYYY-MM-DD-per-cluster-optimization.md`. Update `index.md` Generated Reports table when done.

### When to generate

The user may request it explicitly ("show me per-cluster recommendations"), or you should offer it after finishing the cost analysis: "Want me to generate a per-cluster optimization guide with machine pool breakdowns and ordered recommendations?"

Use `reports/example/per-cluster-optimization.md` as the structural template. Copy its section order and table layouts; replace placeholder content with customer-specific data.

### Per-cluster table format

One `###` section per cluster, ordered cost-descending (most expensive first). Within a section:

```markdown
### <cluster-name> — $X,XXX/mo [⚠ optional flag]

| Pool | Instance | vCPU | GiB | Min→Max nodes | Min→Max vCPU | Notes |
|---|---|---|---|---|---|---|
| worker | r5.2xlarge | 8 | 64 | 3→15 | 24→120 | variable |
| worker-01 | r5.8xlarge | 32 | 256 | 3→3 | 96→96 | fixed |
| **Worker total** | | | | | **120→216** | Actual (telemetry): **165 vCPU** |
| CP nodes | m5.2xlarge | 8 | 32 | 3→3 | — | Classic overhead |
| Infra nodes | r5.4xlarge | 16 | 128 | 3→3 | — | Classic overhead |

**Cost:** ROSA $X,XXX | EC2+EBS $X,XXX | HCP fee $183 | **Total $X,XXX/mo**

**Optimizations:**
🟢 ...
🟡 ...
🔴 ...
```

**Rules:**
- Classic clusters: one "Worker total" row summing worker pools; then separate CP and Infra rows below the divider (CP/Infra vCPUs go in Notes, not in the vCPU column — they don't count toward ROSA billing)
- HCP clusters: one "Total" row at end of the table
- Fixed pools: note `fixed — AT MAX` if actual = max
- `Min→Max vCPU` = min_nodes × vCPU_per_node → max_nodes × vCPU_per_node
- Telemetry actual: use HCC/Telesense snapshot; note `⚠` if actual exceeds configured max
- Identical cluster profiles: document the first fully; for duplicates write one line: "Identical profile to X — instance, vCPU/GiB per node, vCPU range. Actual (telemetry): N vCPU. Same optimizations."

### Effort taxonomy

```
🟢 Quick win — no migration required; can be done with standard machine pool replace procedure
🟡 Medium — requires planning, scheduling, or coordination (e.g., contract changes, capacity review)
🔴 Long-term — requires HCP, specific OCP version, Karpenter enabled, or validated workload profiling
```

Use consistent ordering within each cluster: 🟢 first, then 🟡, then 🔴.

### AMD vs Intel guidance

When a cluster uses r7a (AMD EPYC) or any AMD instance family, check whether an Intel equivalent is cheaper in the target region **before** recommending it as the preferred x86 option. Do not assume AMD is cheaper than Intel.

In **ap-northeast-1**: r7i (Intel Sapphire Rapids) is cheaper than r7a (AMD EPYC Genoa) at the same vCPU/memory tier. Use r7i as the default x86 recommendation.

AMD EPYC Genoa's advantage over Intel is **memory bandwidth** (12 DDR5 channels vs Intel's 8). If workloads are memory-bandwidth-saturated, AMD may outperform Intel despite the higher cost — always note this in the recommendation with a benchmark caveat:

> "Benchmark first if the workload is memory-bandwidth-saturated — AMD EPYC Genoa has higher memory bandwidth (12 DDR5 channels vs Intel Sapphire Rapids' 8); if bandwidth is the bottleneck, r7i may underperform despite the lower price."

Always confirm instance pricing via the AWS Pricing MCP tool before recommending an instance swap. See "Confirmed Instance Pricing" section below.

### ARM prerequisite

All ARM Graviton migrations require **Karpenter to be enabled first** (ROSA HCP 4.22+). Karpenter's NodePool configuration handles mixed-architecture scheduling and workload constraints. Without Karpenter, ARM migration requires manual pool management and is higher-risk.

Mark all ARM recommendations as 🔴 and include: "Requires Karpenter enabled first."

IBM Cloud Pak workloads are **x86_64 only** — never recommend ARM for IBM CP clusters regardless of HCP status.

### Confirmed Instance Pricing section

Always include a "Confirmed Instance Upgrade Pricing" table at the top of the optimization document, before any cluster sections. Use the AWS Pricing MCP tool to confirm each instance price; record source and date. Format:

```markdown
## Confirmed Instance Upgrade Pricing (<region>, on-demand)

| Current | vCPU | GiB | $/hr | Confirmed | Replacement | $/hr | Confirmed | Delta | Note |
|---|---|---|---|---|---|---|---|---|---|
| r5.2xlarge | 8 | 64 | $0.6080 | YYYY-MM-DD | **r6i.2xlarge** | $0.6080 | YYYY-MM-DD | $0 | Free perf upgrade |
| r7a.2xlarge | 8 | 64 | $0.7342 | YYYY-MM-DD | **r7i.2xlarge** | $0.6384 | YYYY-MM-DD | −13% | x86 default; benchmark if mem-BW bound |
| r7a.2xlarge | 8 | 64 | $0.7342 | YYYY-MM-DD | **r7g.2xlarge** | $0.5168 | YYYY-MM-DD | −30% | ARM — Karpenter first |
```

Each row carries the date the price was confirmed via AWS Pricing MCP. Before including a row, check the registry (see "Confirmed Instance Pricing Registry" section): if the rate was confirmed within 30 days, use it directly and carry the same date. If older than 30 days, re-query the API, update the registry row with the new rate and today's date, then write the refreshed rate into this table. Never include an instance without a confirmed date; mark estimated rates with `≈` prefix (e.g. `≈$0.50`).

### Fleet summary tables

End the document with three fleet-level summary tables:

```markdown
## Fleet Optimization Summary

### 🟢 Quick wins — do now, no migration required
| Action | Clusters | Estimated saving |
|---|---|---|

### 🟡 Medium — plan and schedule
| Action | Clusters | Estimated saving |
|---|---|---|

### 🔴 Long-term — post-Karpenter or validated profiling
| Action | Clusters | Estimated saving |
|---|---|---|
```

---

## Execution Approach

For standard ROSA cost reports, follow this discipline:

**No brainstorming or design docs.** Jump directly to data collection and file writing — these are routine deliverables with all needed structure in this skill. Do not invoke the brainstorming skill.

**Write incrementally.** Create `reports/<customer>/index.md` immediately after confirming the cluster list and scope (skeleton with placeholders is fine). Fill in each cluster's row and node pool data as you gather it from OCM. Do not wait until all data is collected before writing any files — that risks running out of context and losing collected information.

**Use only the example report as a template reference.** `reports/example/` is the only tracked template. Never read gitignored customer report files (`reports/suncorp/`, `reports/cathay-pacific/`, etc.) — they are not available to other users and should not be treated as authoritative sources. This skill and `reports/example/` contain all needed templates and conventions.

## File Output Conventions

All commands write their output to the `reports/` directory. Collect the customer name at the start of every command and use it to determine the output path.

### Directory structure

```
reports/
└── <customer-name>/
    ├── index.md                          # Customer profile and report history
    ├── cost-explorer.html                # Interactive cost explorer
    ├── YYYY-MM-DD-cost-estimate.md
    ├── YYYY-MM-DD-cost-compare.md
    ├── YYYY-MM-DD-cost-optimize.md
    └── YYYY-MM-DD-cost-report.md
```

### Customer setup — start of every command

1. Ask: "What's the customer name?" (use a slug-friendly form, e.g., `acme-corp`)
2. Check whether `reports/<customer-name>/index.md` exists.
   - If it exists: read it and surface the recorded values for the parameters below — the user confirms or overrides, they do not need to re-enter unchanged data.
   - If it does not exist: collect all required data normally; create the index when done.
3. Propose the default output path and confirm: `reports/<customer-name>/YYYY-MM-DD-<report-name>.md`. Accept an alternative path if the user provides one.
4. **Confirm pricing assumptions — always ask, never assume, never carry over from a previous customer in the same session.** Suggest the defaults below and wait for the user to confirm or correct each one before doing any calculation:

   | Parameter | Default | What to ask |
   |---|---|---|
   | AWS region | us-east-1 | "Which AWS region are their clusters in?" |
   | ROSA contract term | 1-year | "What ROSA contract term are they on? (PAYGO / 1-year / 3-year)" |
   | EC2 discount | 40% (standard 1-year reserved) | "Are they on standard reserved pricing, an EDP, or something else? I'll default to standard 1-year reserved (40% off on-demand)." |
   | Burst utilization | 20% | "What share of the month do burst nodes typically run beyond their current steady state? I'll default to 20%. Check CloudWatch node count metrics, Hybrid Cloud Console analytics, or Telesense for actual data." |

   If the index.md already records these values, show them as the proposed values rather than re-asking from scratch — but still show them and let the user correct before proceeding.

   **Do not start any cost calculation until all four parameters are confirmed.** A single batch message with all four questions and their defaults is fine — the user can reply with "all defaults" or correct specific ones.

### Report file header

Begin every report file with:

```markdown
# ROSA <Report Type> — <Customer Name>

**Date:** YYYY-MM-DD
**Command:** /rosa:<command-name>
**Rates:** current as of 2026-06 — verify at https://aws.amazon.com/rosa/pricing/ before quoting

---
```

Follow with the full command output.

### index.md format

```markdown
# <Customer Name> — ROSA Cost Analysis

**Last updated:** YYYY-MM-DD

## Fleet Profile

- **Cluster count:** N
- **Architecture:** Classic / HCP / Mixed
- **AZ topology:** Single-AZ / Multi-AZ
- **Total worker vCPUs:** X
- **ROSA contract term:** PAYGO / 1yr / 3yr
- **EC2 reserved term:** On-demand / 1yr / 3yr
- **Region:** us-east-1

## Cluster Details

| Cluster ID or Name | Type | Worker pools | Total vCPUs | Instance profile |
|---|---|---|---|---|

## Pricing Overrides

- `rh_discount:` X% _(omit if not set)_
- `ec2_discount:` X% _(omit if not set)_

## Generated Reports

| Date | Report | File |
|---|---|---|
| YYYY-MM-DD | Cost Estimate | YYYY-MM-DD-cost-estimate.md |
```

After every command run: refresh Fleet Profile with any new data collected and append a row to the Generated Reports table.

### Recalculation workflow — when cluster sizes change

Whenever you recalculate cluster vCPU counts for a customer (new telemetry snapshot, updated pool configs, or corrected data), apply this sequence **before** updating any report files:

1. **Update `index.md` first** — revise the Fleet Profile (actual/min/max vCPUs, remaining burst headroom, actual node count, baseline cost) and the Cluster Details table (actual vCPU and remaining burst columns). This is the single source of truth for the customer fleet.
2. **Update all reports in the customer directory** — every `.md` cost analysis and every `cost-explorer.html` in `reports/<customer-name>/` must reflect the new vCPU basis. Update per-cluster tables, fleet summaries, optimization scenarios, and narrative sections.
  If a cost explorer HTML file exists, update its `CLUSTERS` JS array to match — including
  the `az` field on any Classic clusters.
3. **Note the change** — add a "Revised: YYYY-MM-DD" line to the report header and a brief methodology note explaining what changed (e.g., switched from autoscaler minimum to telemetry-actual vCPUs).

Do not update any report until index.md reflects the new data. This prevents reports from diverging from the customer profile.

### cost-explorer.html — customization guide

Start from `reports/example/cost-explorer.html`. The following must be updated for each customer:

| Field | What to set |
|---|---|
| `<title>` and `<h1><span>` | Customer name |
| `.header-meta` text | Cluster count, region(s), EC2 pricing date |
| `CLUSTERS` array | One entry per cluster (schema below) |
| `EC2` object | On-demand $/vCPU/hr per instance key (from AWS Pricing MCP or this skill's embedded rates) |
| `EBS_NODE` | `300 × gp3_rate_in_region` (e.g., $26.40 in ap-northeast-1) |
| `CLASSIC_OH` | Default per-cluster CP+Infra overhead in $/month |
| `s.contractTerm` initial value | Match customer's current term (`'paygo'`, `'1yr'`, `'3yr'`) |
| `s.ec2Discount` initial value | 0 for PAYGO/on-demand, 40 for 1yr, 60 for 3yr |

**CLUSTERS entry schema:**

```js
{
  id:         "abcd1234",   // first 8 chars of external cluster ID
  name:       "my-cluster",
  type:       "hcp",        // or "classic"
  az:         "multi",      // Classic only: "single" or "multi"
  nodes:      8,            // worker nodes at steady state
  min:        16,           // autoscaler min vCPU across all pools
  steady:     32,           // actual vCPU from telemetry (billing basis)
  burst:      32,           // autoscaler max vCPU − actual vCPU (headroom)
  inst:       "r7i_2xl",    // key into the EC2 object
  cat:        "memory",     // "memory" | "general" | "compute" — controls ARM toggle
  cpInfraOH:  1911,         // Classic only: per-cluster CP+Infra $/month; omit to use CLASSIC_OH
}
```

**Mixed-instance clusters:** Use a blended $/vCPU/hr = total_node_hourly_cost / total_vCPU.
Set `cat` to the dominant instance family.

**Per-cluster Classic overhead:** When Classic clusters use different infra types, add `cpInfraOH` to each Classic entry and patch `calcCluster`:

```js
// in calcCluster, replace:
const overhead = isHcp ? HCP_FEE : CLASSIC_OH;
// with:
const overhead = isHcp ? HCP_FEE : (c.cpInfraOH ?? CLASSIC_OH);
// and propagate into the return:
cpInfra: isHcp ? null : (c.cpInfraOH ?? CLASSIC_OH),
```

**`min` and `steadyVCPU` columns:** The per-cluster table shows min / actual / max. Add these to `calcCluster`'s return:

```js
minVCPU:    Math.round((c.min ?? c.steady) * binpack),
steadyVCPU: effSteady,
```

**Baseline snapshot:** Set `s.contractTerm` and `s.ec2Discount` defaults to the customer's current configuration so the initial baseline reflects actual spend. The user can then move sliders to explore savings.

## Constraints and Assumptions

- Region: confirmed per customer (see Customer setup step 4). ROSA worker node fees are uniform across AWS standard Regions; EC2 rates vary by region — use the AWS Pricing API or the embedded us-east-1 rates as a baseline and note if using a proxy rate for another region.
- Hours/month: 730.
- vCPU counts in Live mode come from `ocm list machinepool` replica counts, not live utilization metrics.
- Discount multipliers are approximations for standard reserved instances. Users with EDP or private pricing should provide explicit percentages.
- EC2 rates: use embedded rates in this skill as defaults. For non-us-east-1 regions or when the AWS Pricing MCP tool is available, look up rates directly and note the source and date. The embedded rates are for us-east-1 and may not reflect current pricing in other regions.
- Verify current ROSA rates at https://aws.amazon.com/rosa/pricing/ before quoting customers.

---

## Confirmed Instance Pricing Registry

On-demand rates confirmed via AWS Pricing MCP. Each row carries the date it was last confirmed.

**Freshness rule:** Before using a rate from this registry, check its `Confirmed` date. If it is **more than 30 days old**, re-query the AWS Pricing MCP for that instance, update the row with the new rate and today's date, then use the refreshed rate in the report. If the rate changed, note it in the report header. If unchanged, the refresh still resets the clock.

When a rate is not in the registry at all, query the API, add a new row with today's date, and use the confirmed rate.

### ap-northeast-1 (Tokyo)

Rates below confirmed identical for ap-northeast-3 (Osaka) for all instances listed.

| Instance | vCPU | GiB | $/hr | $/vCPU/hr | Confirmed |
|---|---|---|---|---|---|
| m5.xlarge | 4 | 16 | $0.2480 | $0.0620 | 2026-07-01 |
| m5.2xlarge | 8 | 32 | $0.4960 | $0.0620 | 2026-07-01 |
| m5.8xlarge | 32 | 128 | $1.9840 | $0.0620 | 2026-07-01 |
| m6a.2xlarge | 8 | 32 | $0.4464 | $0.0558 | 2026-07-01 |
| m7i.8xlarge | 32 | 128 | $2.0832 | $0.0651 | 2026-07-01 |
| r5.xlarge | 4 | 32 | $0.3040 | $0.0760 | 2026-07-01 |
| r5.2xlarge | 8 | 64 | $0.6080 | $0.0760 | 2026-07-01 |
| r5.4xlarge | 16 | 128 | $1.2160 | $0.0760 | 2026-07-01 |
| r5.8xlarge | 32 | 256 | $2.4320 | $0.0760 | 2026-07-01 |
| r5a.8xlarge | 32 | 256 | $2.1920 | $0.0685 | 2026-07-01 |
| r6i.8xlarge | 32 | 256 | $2.4320 | $0.0760 | 2026-07-01 |
| r6a.8xlarge | 32 | 256 | $2.1888 | $0.0684 | 2026-07-01 |
| r7i.2xlarge | 8 | 64 | $0.6384 | $0.0798 | 2026-07-01 |
| r7i.4xlarge | 16 | 128 | $1.2768 | $0.0798 | 2026-07-01 |
| r7a.xlarge | 4 | 32 | $0.3671 | $0.0918 | 2026-07-01 |
| r7a.2xlarge | 8 | 64 | $0.7342 | $0.0918 | 2026-07-01 |
| r7g.2xlarge | 8 | 64 | $0.5168 | $0.0646 | 2026-07-01 |
| r8g.2xlarge | 8 | 64 | $0.5685 | $0.0711 | 2026-07-01 |
| c6a.4xlarge | 16 | 32 | $0.7704 | $0.0482 | 2026-07-01 |
| c7i.4xlarge | 16 | 32 | $0.8988 | $0.0562 | 2026-07-01 |
| t3.xlarge | 4 | 16 | $0.2176 | $0.0544 | 2026-07-01 |
| t3a.xlarge | 4 | 16 | $0.1958 | $0.0490 | 2026-07-01 |
| g4dn.4xlarge | 16 | 64 | $1.6250 | $0.1016 | 2026-07-01 |

---

## Engagement Lessons

Reusable findings from completed customer engagements. **After each engagement, add any new pricing discoveries or analysis patterns that would have saved time.** Keep entries concise — one paragraph max per lesson. Remove lessons that become stale or are superseded by a newer pattern.

### AMD vs Intel in ap-northeast-1 (from MUFG, 2026-07)

In ap-northeast-1, **Intel (r7i) is cheaper than AMD (r7a)** for the same vCPU/memory tier: r7i.2xlarge $0.6384 vs r7a.2xlarge $0.7342 (−13%). Do not assume AMD is the cheaper x86 option — pricing varies by region. AMD EPYC Genoa's legitimate advantage is higher memory bandwidth (12 DDR5 channels vs Intel Sapphire Rapids' 8); recommend AMD only if there's evidence the workload is memory-bandwidth-saturated. Otherwise, recommend Intel and note the benchmark caveat.

### ARM prerequisite: Karpenter first (from MUFG, 2026-07)

ARM Graviton pool migrations require Karpenter to be enabled first (ROSA HCP 4.22+). Karpenter's NodePool architecture handles mixed-architecture scheduling cleanly; without it, ARM migration requires manual pool management across drain cycles and is higher-risk operationally. Always mark ARM as 🔴 Long-term and include "Requires Karpenter enabled first" in the recommendation text.

### Autoscaler max is per-pool, not cluster-wide (from MUFG, 2026-07)

The "max vCPU" for a cluster is the arithmetic sum of `max_nodes × vCPU_per_node` across all machine pools — not a single cluster-wide cap. OCM configures `MachineAutoscaler` resources per pool. Actual running vCPU can exceed the arithmetic sum if live node counts exceed pool configs (known OCM soft-limit anomaly). When actual > configured max, note this as `⚠` and recommend inspecting `ocm list machinepool --cluster <id>` or `oc get machineautoscaler -n openshift-machine-api`.

### r6i/r6a are free upgrades from r5/r5a at same price (from MUFG, 2026-07)

In ap-northeast-1: r6i.8xlarge = r5.8xlarge ($2.4320/hr), r6a.8xlarge ≈ r5a.8xlarge ($2.1888 vs $2.1920). These are zero-cost instance family upgrades (Intel Ice Lake / AMD Milan generation jump). Recommend these as 🟢 quick wins for any Classic cluster still on r5/r5a pools. Node count reduction is possible if Classic workers are CPU-bound (improved per-core throughput) — flag this contingency and recommend pulling CloudWatch CPUUtilization before committing to node reduction savings.

### Burst billing: use 20% of remaining headroom as the conservative default (from MUFG, 2026-07)

Burst billing = the cost of vCPU headroom that isn't currently used but may be. A conservative default of 20% × (max vCPU − actual vCPU) reflects occasional scale-out without overstating steady-state cost. Clusters at ceiling (actual = max) have zero burst billing. Surface burst billing as a separate line item so customers can see how much they're paying for headroom vs running workloads.
