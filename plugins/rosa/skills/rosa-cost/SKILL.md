---
name: rosa-cost
description: |
  Pricing data, calculation methodology, and output templates for ROSA cost estimation.

  Use when:
  - Estimating ROSA Classic or HCP cluster costs for individuals or fleets
  - Comparing Classic vs HCP costs with a savings delta
  - Identifying cost optimization opportunities (contracts, Karpenter, ARM, Spot)
  - Generating strategic advisory reports for Classic→HCP migration engagements

  Handles three input modes: live OCM cluster IDs, detailed pool specs, or high-level vCPU estimates.

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

gp3 at **$0.08/GB-month** in us-east-1.

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

Requires an active OCM login. Run `ocm whoami` first to confirm. If it fails, instruct the user:

```bash
ocm login --token=<token>  # get token at https://console.redhat.com/openshift/token
```

For each cluster ID:

```bash
ocm list machinepool --cluster <CLUSTER_ID>
```

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

## Constraints and Assumptions

- Region: us-east-1. ROSA worker node fees are uniform across AWS standard Regions. EC2 rates may vary but this skill uses us-east-1 as the baseline.
- Hours/month: 730.
- vCPU counts in Live mode come from `ocm list machinepool` replica counts, not live utilization metrics.
- Discount multipliers are approximations for standard reserved instances. Users with EDP or private pricing should provide explicit percentages.
- No calls to the AWS Pricing API — rates are embedded in this skill.
- Verify current rates at https://aws.amazon.com/rosa/pricing/ before quoting customers.
