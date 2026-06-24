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

**ROSA subscription fees (Red Hat charge, on top of EC2):**

These are reference values embedded in the skill for calculations. The skill must cite https://aws.amazon.com/rosa/pricing/ when presenting results and note that users should verify current rates there.

| Cluster Type | Fee |
|---|---|
| ROSA Classic | $0.03/vCPU/hr per worker vCPU |
| ROSA HCP | $0.10/cluster/hr (fixed) + $0.03/vCPU/hr per worker vCPU |

**EC2 instance profile rates:**

| Profile | Rate ($/vCPU/hr) |
|---|---|
| General Purpose (Standard) | $0.048 |
| Compute Optimized | $0.0425 |
| Memory Optimized | $0.063 |
| Bare Metal (Standard) | $0.048 |
| GPU Optimized (Mid-tier baseline) | $0.1015 |

**Discount multipliers** (applied independently to RH portion and EC2 portion):

| Term | Multiplier |
|---|---|
| PAYGO (on-demand) | 1.0× |
| 1-year reserved | ~0.6× |
| 3-year reserved | ~0.4× |

Users may override any multiplier with a specific discount percentage (e.g., `rh_discount=20%`).

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

Per cluster, per month (730 hrs):

```
worker_vcpus  = sum of (replicas × vcpus_per_instance) across all worker pools
               (control plane nodes excluded — ROSA manages them separately)

EC2 cost      = worker_vcpus × ec2_profile_rate × 730 × ec2_discount_multiplier
ROSA cost     = worker_vcpus × 0.03 × 730 × rh_discount_multiplier
              + cluster_hourly_fee × 730   ← HCP only ($0.10/hr); Classic = $0
Total monthly = EC2 cost + ROSA cost
```

Fleet total = sum of all per-cluster totals.

For HCP comparison using the same worker vCPU counts as Classic: HCP eliminates Classic control-plane and infra EC2 nodes from the customer bill (they run on shared Red Hat infrastructure). The skill quantifies this saving using the known ROSA Classic defaults:

| Node role | Count | Default instance | vCPUs | Profile |
|---|---|---|---|---|
| Control plane | 3 (always) | m5.2xlarge | 8 | General Purpose |
| Infra (single-AZ) | 2 | r5.xlarge | 4 | Memory Optimized |
| Infra (multi-AZ) | 3 | r5.xlarge | 4 | Memory Optimized |

The skill asks whether the cluster is single-AZ or multi-AZ (or infers it from OCM data in Live mode) to use the correct infra count. These instance sizes are ROSA defaults; users may override them if their cluster uses non-default sizes.

Approximate EC2 savings per cluster per month (PAYGO, us-east-1):
- Single-AZ: ~$1,211/cluster/month
- Multi-AZ: ~$1,395/cluster/month

### 4. Output Templates

**Cost table** (Markdown, one row per cluster):

| Cluster | Type | vCPUs | EC2/mo | ROSA/mo | Total/mo |
|---|---|---|---|---|---|
| prod-cluster-1 | Classic | 96 | $3,363 | $2,102 | $5,465 |
| ... | | | | | |
| **Fleet total** | | | | | **$XX,XXX** |

**Narrative** (3–5 sentences):
- Total fleet spend at current configuration
- Largest cost driver (biggest cluster or highest-rate profile)
- Top recommendation (e.g., migrate to HCP, apply 1yr reserved)
- Estimated savings from top recommendation

### 5. Migration Delta Logic (`cost-compare`)

Run the formula twice for the same worker vCPU counts:
- Once as Classic (no cluster hourly fee)
- Once as HCP ($0.10/cluster/hr fixed fee added)

Output: side-by-side table with a **Savings/mo** and **Savings/yr** delta column per cluster, plus fleet totals. Narrative frames the fleet-level number: "Migrating all N clusters to HCP saves approximately $X/month ($Y/year)."

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

### `/rosa:cost-optimize` — Savings Recommendations

**Purpose:** Rank savings opportunities across the fleet.

**Accepts:** Same inputs as `cost-estimate`.

**Output:** Ranked list of recommendations, each with:
- Description of the opportunity
- Estimated monthly savings
- Implementation complexity: low / medium / high

Standard opportunities surfaced:
1. Migrate Classic clusters to HCP
2. Apply 1yr or 3yr reserved pricing (RH and/or EC2)
3. Right-size oversized machine pools (the skill prompts the user to review pool sizes; it does not fetch live utilization metrics — this is a prompted recommendation, not automated detection)
4. Consolidate very small clusters into larger ones

---

## Constraints and Assumptions

- Currency: USD only
- Region: us-east-1 assumed; rates do not vary per-region within this skill
- Control plane and infra nodes: excluded from Classic worker cost calculations (they are ROSA-managed overhead), but their EC2 cost IS included in the Classic→HCP savings calculation using known ROSA defaults (m5.2xlarge × 3 control plane, r5.xlarge × 2–3 infra). Users may override instance sizes if their cluster uses non-defaults.
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
| `plugins/rosa/OWNERS` | GitHub username(s) |
| `plugins/rosa/README.md` | plugin docs |
