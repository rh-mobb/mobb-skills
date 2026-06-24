# ROSA Cost Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the `rosa` plugin for mobb-skills with five commands for ROSA cost estimation, comparison, optimization, and strategic advisory reporting.

**Architecture:** A single `rosa-cost` skill holds all pricing data, calculation methodology, and output templates as the authoritative reference. Five thin command files set context and delegate to the skill. No external API calls — pricing is embedded in the skill.

**Tech Stack:** Markdown (Claude Code plugin format), skillsaw linting (`make lint`), marketplace sync (`make update`), container runtime (podman or docker) required for linting.

## Global Constraints

- All files are Markdown with YAML frontmatter.
- Skillsaw rules enforced: `content-embedded-secrets` (error), `content-tautological` (error), `content-weak-language` (error), `agentskill-valid/name/description` (error), `instruction-file-valid` (error), `content-cognitive-chunks` (warning only).
- Command frontmatter requires `description:`. Add `argument-hint:` only for positional arguments — none of the five rosa commands use positional args, so omit it.
- Skills frontmatter requires `name:` and `description:`.
- `make lint` uses a container image (`ghcr.io/stbenjam/skillsaw:0.14.0`) — ensure container runtime is available.
- `make update` regenerates `docs/` — run after all plugin files exist.
- The spec noted no git commits until all plugin files exist and `make lint` passes. All commits happen in Task 6.
- Region default: us-east-1. Currency: USD. Hours/month: 730.
- The spec's "Files to Create" section omits `cost-report.md` but the user confirmed this fifth command; include it.

---

### Task 1: Plugin Scaffold

Create the directory structure and required boilerplate files that skillsaw validates before looking at skill/command content.

**Files:**
- Create: `plugins/rosa/.claude-plugin/plugin.json`
- Create: `plugins/rosa/OWNERS`
- Create: `plugins/rosa/README.md`

**Interfaces:**
- Produces: A valid plugin scaffold that `make lint` recognizes as a registered plugin (even with no commands yet — skillsaw will warn but not error on missing commands during scaffold phase).

- [ ] **Step 1: Create `plugins/rosa/.claude-plugin/plugin.json`**

```json
{
  "name": "rosa",
  "description": "ROSA cost estimation, comparison, and optimization for Classic and HCP clusters.",
  "version": "0.1.0",
  "author": {
    "name": "github.com/rh-mobb"
  }
}
```

- [ ] **Step 2: Create `plugins/rosa/OWNERS`**

```yaml
approvers:
  - pczarkow
reviewers:
  - pczarkow
```

- [ ] **Step 3: Create `plugins/rosa/README.md`**

```markdown
# rosa

ROSA cost estimation and optimization plugin for the MOBB team.

Supports ROSA Classic and ROSA HCP cost calculation for individual clusters and fleets.

## Commands

| Command | Purpose |
|---|---|
| `/rosa:cost` | Guided wizard — collects data conversationally, produces full analysis |
| `/rosa:cost-estimate` | Calculate monthly/annual costs for a fleet |
| `/rosa:cost-compare` | Classic vs HCP side-by-side with savings delta |
| `/rosa:cost-optimize` | Ranked savings opportunities with estimated impact |
| `/rosa:cost-report` | Full strategic advisory report for Classic→HCP migration |

## Input Modes

All commands accept three input modes:

- **Live**: OCM cluster IDs — requires active `ocm login`
- **Detailed**: Machine pool spec (cluster name, instance type, replica count per pool)
- **Estimate**: Cluster count + total vCPU budget

## Quick Start

```
/rosa:cost
```

For a fleet with known cluster IDs:
```
/rosa:cost-estimate cluster-id-1 cluster-id-2 cluster-id-3
```

For a quick estimate with 5 clusters at 240 total vCPUs:
```
/rosa:cost-estimate 5 clusters, 240 vCPUs total, 1yr contract
```

## Pricing Reference

Rates sourced from https://aws.amazon.com/rosa/pricing/ (us-east-1, current as of 2026-06).
Always verify current rates before quoting to customers.
```

---

### Task 2: rosa-cost Skill

The skill is the authoritative source for all pricing data, formulas, and output templates. Commands reference it rather than embedding pricing themselves.

**Files:**
- Create: `plugins/rosa/skills/rosa-cost/SKILL.md`

**Interfaces:**
- Produces: A skill named `rosa-cost` that commands can reference for all pricing logic, formulas, and output format.

- [ ] **Step 1: Create `plugins/rosa/skills/rosa-cost/SKILL.md`**

```markdown
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
```

- [ ] **Step 2: Verify the skill file exists and has correct frontmatter**

```bash
head -20 plugins/rosa/skills/rosa-cost/SKILL.md
```

Expected: frontmatter shows `name: rosa-cost`, `description:` block, `user_invocable: false`.

---

### Task 3: cost-estimate Command

**Files:**
- Create: `plugins/rosa/commands/cost-estimate.md`

**Interfaces:**
- Consumes: pricing data from the `rosa-cost` skill
- Produces: A command that calculates fleet costs and outputs the Simple Cost Table

- [ ] **Step 1: Create `plugins/rosa/commands/cost-estimate.md`**

```markdown
---
description: Calculate monthly and annual costs for a ROSA fleet at its current configuration.
---

## Name
rosa:cost-estimate

## Synopsis
```
/rosa:cost-estimate [inputs]
```

## Description

Calculates monthly and annual costs for a fleet of ROSA Classic or HCP clusters.

Accepts three input modes:
- **Live**: OCM cluster IDs — requires active `ocm login`
- **Detailed**: pool spec block (cluster name, instance type, replica count per pool)
- **Estimate**: cluster count and total vCPU budget

Optional overrides (provide inline with your request):
- `discount=1yr` or `discount=3yr` — ROSA worker node fee contract term (default: PAYGO)
- `ec2=1yr` or `ec2=3yr` — EC2 reserved instance term (default: on-demand)
- `rh_discount=15%` — custom ROSA fee discount percentage
- `ec2_discount=40%` — custom EC2 discount percentage

## Implementation

1. Identify the input mode from what the user provides. If the user provides no fleet data, ask which mode they prefer.

2. Collect missing information conversationally:
   - If Live mode: confirm `ocm whoami` succeeds before running `ocm list machinepool`.
   - Ask whether clusters are single-AZ or multi-AZ if not inferable from OCM data.
   - Ask for contract terms (PAYGO / 1yr / 3yr) for both ROSA fee and EC2 if not specified.

3. Apply the calculation formula from the rosa-cost skill to compute per-cluster line items.

4. Output the Simple Cost Table (single-architecture column for whichever type they are estimating — Classic or HCP) with per-cluster rows and a fleet summary row.

5. Show both monthly and annual totals.

6. Follow with the narrative (total fleet spend, largest cost driver, top recommendation, implementation complexity).

Use the Simple Cost Table format and Narrative format defined in the rosa-cost skill.

For a Classic vs HCP side-by-side comparison, use `/rosa:cost-compare`.
For ranked optimization opportunities, use `/rosa:cost-optimize`.
```

---

### Task 4: cost-compare Command

**Files:**
- Create: `plugins/rosa/commands/cost-compare.md`

**Interfaces:**
- Consumes: pricing data from the `rosa-cost` skill
- Produces: A command that runs the formula twice (Classic and HCP) and shows both with a savings column

- [ ] **Step 1: Create `plugins/rosa/commands/cost-compare.md`**

```markdown
---
description: Show Classic vs HCP costs side-by-side for the same fleet, with migration savings.
---

## Name
rosa:cost-compare

## Synopsis
```
/rosa:cost-compare [inputs]
```

## Description

Runs the cost formula for the same fleet twice — once as Classic, once as HCP — and shows the results side-by-side with a Savings column.

Accepts the same inputs as `/rosa:cost-estimate`.

## Implementation

1. Collect fleet data the same way as `/rosa:cost-estimate`.

2. Run the formula twice using the same worker vCPU counts:
   - **Classic**: include cp_total and infra_total; cluster_fee = $0.
   - **HCP**: cp_total = $0; infra_total = $0; cluster_fee = $182.50/month.

3. Output the side-by-side cost table (cost-compare variant from the rosa-cost skill) with Savings/mo and Savings/yr columns. Show per-cluster rows and a fleet summary row.

4. Include the fleet-level narrative: "Migrating all N clusters to HCP saves approximately $X/month ($Y/year)."

5. Show the HCP Qualitative Benefits table from the rosa-cost skill after the cost table.

Use the Simple Cost Table (cost-compare variant) and HCP Qualitative Benefits table formats defined in the rosa-cost skill.

For ranked optimization recommendations beyond Classic→HCP, use `/rosa:cost-optimize`.
For a full strategic advisory report with a phased migration plan, use `/rosa:cost-report`.
```

---

### Task 5: cost-optimize Command

**Files:**
- Create: `plugins/rosa/commands/cost-optimize.md`

**Interfaces:**
- Consumes: pricing data from the `rosa-cost` skill
- Produces: A command that ranks savings opportunities with estimated impact and the Optimized TCO Table

- [ ] **Step 1: Create `plugins/rosa/commands/cost-optimize.md`**

```markdown
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

3. Evaluate and quantify each opportunity:

**Opportunity 1: Migrate Classic clusters to HCP**
Use the Classic→HCP Savings Per Cluster table from the rosa-cost skill. Multiply by fleet size.
Complexity: Medium (infrastructure change; no application changes in Phase 1).

**Opportunity 2: Contract pricing for steady-state capacity**
If autoscaling min/max data is available (Live mode from OCM or user-provided), split steady-state vs burst. Apply the break-even analysis from the rosa-cost skill.
If not available, ask: "What percentage of time do your clusters scale beyond minimum replica count?"
Complexity: Low.

**Opportunity 3: Karpenter on ROSA HCP 4.22+**
Confirm or ask whether the target ROSA version is 4.22+. Then quantify each Karpenter lever from the rosa-cost skill separately (bin-packing, Spot, ARM, scale-to-zero) and combine them.
Complexity: Medium (requires HCP migration first; Karpenter itself is low-config once on HCP).

**Opportunity 4: Right-size oversized machine pools**
Surface as a prompt to review pool sizes. Do not fetch live utilization metrics.
Complexity: Low.

**Opportunity 5: Consolidate small clusters**
Identify clusters with low vCPU counts that may be cheaper to merge.
Complexity: Medium.

4. Present as a ranked table, highest estimated savings first:

```
## Cost Optimization Recommendations

| # | Opportunity | Est. savings/mo | Est. savings/yr | Complexity |
|---|---|---|---|---|
| 1 | Migrate to HCP | $X | $X | Medium |
| 2 | 1yr contracts (steady state) | $X | $X | Low |
| 3 | Karpenter (bin-packing + ARM + Spot + zero-scale) | $X | $X | Medium |
| 4 | Right-size machine pools | Review recommended | — | Low |
| 5 | Consolidate small clusters | Review recommended | — | Medium |
```

5. Follow with the Optimized TCO Table from the rosa-cost skill showing current vs optimized annual costs.

6. Follow with the narrative (total current spend, largest driver, top recommendation, complexity).

For a full strategic advisory report with a phased migration plan, use `/rosa:cost-report`.
```

---

### Task 6: cost-report Command

**Files:**
- Create: `plugins/rosa/commands/cost-report.md`

**Interfaces:**
- Consumes: pricing data and report format from the `rosa-cost` skill
- Produces: A command that generates the full strategic advisory report for Classic→HCP migration engagements

- [ ] **Step 1: Create `plugins/rosa/commands/cost-report.md`**

```markdown
---
description: Generate a full strategic advisory report for Classic-to-HCP migration with phased plan and month-by-month cost timeline.
---

## Name
rosa:cost-report

## Synopsis
```
/rosa:cost-report [inputs]
```

## Description

Generates a full strategic advisory report for customers migrating from ROSA Classic to HCP. Appropriate for customer-facing engagements where a structured, quantified migration recommendation is required.

This command is for existing Classic clusters only. For greenfield HCP customers, use `/rosa:cost-estimate` or `/rosa:cost-compare`.

Accepts the same inputs as `/rosa:cost-estimate`, plus:
- `arm_pct=50` — target percentage of fleet to migrate to ARM Graviton after HCP migration (default: 50%)
- `prod_clusters=N` — number of production clusters (drives phase timing)

## Implementation

Collect all required fleet data before generating the report:
- Fleet details (cluster count, worker pools, instance types, replica counts)
- Contract terms (ROSA fee term, EC2 reserved term)
- AZ topology (single-AZ or multi-AZ per cluster)
- Prod vs non-prod cluster split (ask if not provided)
- ARM migration target percentage (default 50%)

Then generate the strategic advisory report with these eight sections. Compute all dollar figures from the fleet's actual inputs using the formulas in the rosa-cost skill.

**Section 1: Executive Summary**

Fleet profile header:
- Cluster count, worker node count, total worker vCPUs
- Any additional metrics known (active pods, etc.)

3–4 bullet outcomes with quantified savings:
- Control plane overhead eliminated ($X/cluster/month × N clusters = $X/month)
- Monthly run-rate reduction after full migration ($X/month)
- Compute throughput improvement from ARM Graviton (X nodes → Y ARM nodes = Z node reduction)
- Karpenter bin-packing and Spot savings ($X/month for burst workloads)

**Section 2: Fleet Profile and Operational Challenges**

- Workload topology: prod vs non-prod cluster count, node counts, vCPU counts
- Challenge 1: Dedicated control plane overhead — N clusters × management nodes = $X/month not serving customer workloads
- Challenge 2: Hardware thread contention on x86 — vCPUs are hyperthreads, not physical cores
- Challenge 3: Capacity fragmentation — one MachineSet per (instance family × arch × AZ) = rigid scaling and allocation slack

**Section 3: Cost Analysis and Unit Economics**

Show the Unit Economics Reference table from the rosa-cost skill. Include:
- Classic cluster overhead: $975.25/cluster/month (multi-AZ, 1yr reserved EC2+EBS) = $11,703/cluster/year
- HCP cluster fee: $182.50/cluster/month = $2,190/cluster/year
- Net savings per cluster per month: ~$1,148 (single-AZ) or ~$1,357 (multi-AZ)
- Graviton performance multiplier: E = 1.25; show node reduction for this fleet: x86_nodes → x86_nodes/1.25 ARM nodes = reduction of X nodes

**Section 4: Phased Migration Strategy**

Two-phase plan. Adjust timing based on fleet size and prod/non-prod split.

Phase 1 (Months 1–6): HCP Structural Migration — x86 workers, no application changes required
- Phase 1A (Months 1–2): Pilot wave — 3 non-prod clusters (or fewer if fleet is small)
- Phase 1B (Months 3–4): Non-prod wave — remaining non-prod clusters
- Phase 1C (Months 5–6): Production cutover — production clusters with safety buffer nodes

Phase 2 (Months 7–18): Compute Modernization — ARM Graviton + Karpenter
- Phase 2A (Months 7–9): CI/CD pipeline readiness, multi-arch container images, Karpenter NodePool configuration
- Phase 2B (Months 10–12): Non-prod stateless workloads migrated to ARM
- Phase 2C (Months 13–18): Production cluster waves migrated to ARM

**Section 5: Projected Migration Timeline and Cost Analysis**

Month-by-month table from Month 0 (baseline) through Month 18 (or completion):

```
| Month | Phase | Classic Spend | HCP Spend | Total Bill |
|---|---|---|---|---|
| 0 | Baseline | $X | $0 | $X |
| 1 | Phase 1A: Deploy pilot targets | $X | $X | $X |
| 2 | Phase 1A complete: N clusters deleted | $X | $X | $X |
| ... | ... | ... | ... | ... |
| 6 | Fleet 100% on HCP x86 | $0 | $X | $X |
| 18 | arm_pct% fleet on ARM | $0 | $X | $X |
```

Include overlapping dual-run costs during cutover months (migration buffer nodes). Calculate HCP spend month-by-month as clusters move over.

**Section 6: Financial and Operational Value Realization**

- Phase 1 savings: $X/month reduction (overhead elimination, no application changes required)
- Phase 2 savings: additional $X/month (ARM rate difference + node reduction from Graviton performance multiplier)
- Combined savings: $X/month vs baseline ($Y/year total)
- Karpenter bin-packing bonus: 10% fewer nodes × cost per ARM node = additional $X/year

**Section 7: Performance and Reliability Enhancements**

- ARM vCPUs are physical cores — no hardware thread contention
- DDR5 memory bandwidth on Graviton3 (m7g): 50% higher than DDR4 on comparable Intel instances
- Karpenter scale-up: <45 seconds vs 3–4 minutes for Classic autoscaler
- Karpenter consolidation: automatic bin-packing with zero manual intervention
- Blast radius reduction: control plane runs in Red Hat's AWS account, not the customer's
- Cluster provisioning: ~15 min (HCP) vs ~52 min (Classic)

**Section 8: Next Steps**

3–4 concrete actions to initiate Phase 1A:
- IAM role and VPC configuration for HCP pilot environment
- Pilot cluster provisioning in target non-prod environment
- Migration Toolkit for Containers (MTC) connectivity validation
- Migration playbook review and approval with the customer's platform team
```

---

### Task 7: cost Guided Wizard Command

**Files:**
- Create: `plugins/rosa/commands/cost.md`

The wizard is the entry point that collects data conversationally and delegates to the same logic as the focused commands.

**Interfaces:**
- Consumes: all output formats from the `rosa-cost` skill
- Produces: A guided multi-step conversation that routes to the appropriate output format

- [ ] **Step 1: Create `plugins/rosa/commands/cost.md`**

```markdown
---
description: Guided wizard for ROSA cost estimation, comparison, and optimization. Collects data conversationally and routes to the right analysis.
---

## Name
rosa:cost

## Synopsis
```
/rosa:cost
```

## Description

Entry point for ROSA cost analysis. Collects required information conversationally and produces the appropriate output for the situation.

Use this command when you are not sure which focused command applies. Power users can go straight to `/rosa:cost-estimate`, `/rosa:cost-compare`, `/rosa:cost-optimize`, or `/rosa:cost-report`.

## Implementation

**Step 1: Determine customer context**

Ask:
> "Are you pricing a new ROSA deployment, or do you have existing Classic clusters you want to analyze?"

- **New deployment**: estimate HCP costs only, then surface optimization opportunities (contracts, ARM, Karpenter). Skip all Classic-specific sections.
- **Existing Classic**: collect Classic baseline, produce HCP comparison with savings, then offer optimization analysis.

**Step 2: Collect fleet data**

Ask which input mode they have:
> "Do you have cluster IDs I can look up in OCM, a pool spec with instance types and counts, or just an estimate of cluster count and vCPU budget?"

Collect the data for whichever mode they choose. See the rosa-cost skill for input resolution details.

If Live mode: run `ocm whoami` to confirm login before running `ocm list machinepool`.

**Step 3: Contract terms**

Ask:
> "What contract terms are you on or modeling? On-demand/PAYGO, 1-year, or 3-year — for both the ROSA worker node fee and AWS EC2."

Accept inline overrides such as `rh_discount=15%` or `ec2_discount=40%` for custom pricing.

**Step 4: AZ topology**

If not inferable from OCM data, ask:
> "Are these clusters single-AZ or multi-AZ?"

**Step 5: Produce output**

For **existing Classic customers**:
1. Show Classic baseline cost table (Simple Cost Table, Classic column only).
2. Show Classic vs HCP side-by-side with savings delta (cost-compare format including HCP Qualitative Benefits table).
3. Show top 3 ranked optimization opportunities (cost-optimize format).
4. Ask: "Would you like a full strategic advisory report with a phased migration plan and month-by-month cost timeline?"
   - If yes: follow the full report format from `/rosa:cost-report`.

For **new HCP customers**:
1. Show HCP cost estimate (Simple Cost Table, HCP column only).
2. Show ranked optimization opportunities: contract terms, ARM Graviton, Karpenter, Spot.

All output follows the templates defined in the rosa-cost skill.
```

---

### Task 8: Lint, Update, and Commit

All files exist at this point. Run linting and sync docs, then commit everything together.

**Files:**
- Modify: `docs/superpowers/specs/2026-06-24-rosa-cost-design.md` — add `cost-report.md` to the Files to Create section
- Generate: `docs/` (via `make update`)

- [ ] **Step 1: Verify directory structure**

```bash
find plugins/rosa -type f | sort
```

Expected output (7 plugin files):
```
plugins/rosa/.claude-plugin/plugin.json
plugins/rosa/OWNERS
plugins/rosa/README.md
plugins/rosa/commands/cost-compare.md
plugins/rosa/commands/cost-estimate.md
plugins/rosa/commands/cost-optimize.md
plugins/rosa/commands/cost-report.md
plugins/rosa/commands/cost.md
plugins/rosa/skills/rosa-cost/SKILL.md
```

- [ ] **Step 2: Run `make lint`**

```bash
make lint
```

Expected: exit code 0 with no errors. Warnings on `content-cognitive-chunks` are acceptable. Errors must be fixed before committing.

If linting fails:
- `content-weak-language`: remove phrases like "might", "maybe", "could possibly", "you may want to"
- `content-tautological`: remove statements that say nothing beyond what the heading already says
- `content-embedded-secrets`: check for any tokens or credentials accidentally included
- `agentskill-description`: verify skill frontmatter has a multi-line `description:` block
- `instruction-file-valid`: verify command files have `description:` in frontmatter

Fix any errors and re-run `make lint` until it passes.

- [ ] **Step 3: Update spec to include cost-report.md**

Open `docs/superpowers/specs/2026-06-24-rosa-cost-design.md`. Find the Files to Create table and add the missing row:

```
| `plugins/rosa/commands/cost-report.md` | strategic advisory report (Classic→HCP migration only) |
```

Also update the Commands section to list `/rosa:cost-report` as a fifth command if not already present.

- [ ] **Step 4: Run `make update`**

```bash
make update
```

Expected: regenerates `docs/` without errors. This updates the skillsaw documentation site.

- [ ] **Step 5: Commit everything**

```bash
git add plugins/rosa/ docs/
git commit -m "$(cat <<'EOF'
feat(rosa): add rosa cost estimation and optimization plugin

Adds the rosa plugin with five commands for ROSA Classic and HCP cost
analysis, migration savings comparison, ranked optimization recommendations,
and a full strategic advisory report for Classic→HCP migration engagements.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected: commit succeeds and `git status` shows a clean working tree.

- [ ] **Step 6: Verify the commit**

```bash
git log --oneline -3
git show --stat HEAD
```

Expected: the new commit at the top lists all `plugins/rosa/` files and the updated `docs/`.
