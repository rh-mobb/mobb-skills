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

**Customer setup**: Follow the customer setup process from the rosa-cost skill. Ask for the customer name, check for an existing `reports/<customer-name>/index.md`, and propose the default output path `reports/<customer-name>/YYYY-MM-DD-cost-report.md`.

Collect all required fleet data before generating the report. Ask conversationally for any missing inputs:
- Fleet details: cluster count, worker pools per cluster, instance types, replica counts per pool
- Contract terms: ROSA fee term (PAYGO / 1yr / 3yr) and EC2 reserved term (on-demand / 1yr / 3yr)
- AZ topology: single-AZ or multi-AZ per cluster (determines infra node count and CP+infra overhead)
- Prod vs non-prod cluster split: ask if not provided (drives Phase 1 timing)
- ARM migration target: `arm_pct` (default 50%); confirm if not provided

Compute all dollar figures from the fleet's actual inputs using the formulas in the rosa-cost skill before writing any section. Do not emit placeholder values — every figure in the report must be derived from the collected data.

Then generate the eight sections below in order.

---

### Section 1: Executive Summary

Open with a fleet profile header:
- Total cluster count, total worker node count, total worker vCPUs
- Any additional metrics available from OCM data (e.g., active pods, namespace count)

Follow with 3–4 bullet outcomes, each with a quantified figure derived from fleet data:
- **Control plane overhead eliminated**: Classic CP+infra overhead is $975.25/cluster/month (multi-AZ, 1yr reserved EC2+EBS). For this fleet: $975.25 × N clusters = $X/month currently funding no customer workloads.
- **Monthly run-rate reduction after full migration**: total Classic spend minus projected HCP spend at steady state = $X/month reduction ($Y/year).
- **Compute throughput improvement from ARM Graviton**: applying the Graviton performance multiplier E=1.25 to the `arm_pct` portion of the fleet — x86_nodes × arm_pct → x86_nodes × arm_pct / 1.25 ARM nodes = Z node reduction fleet-wide.
- **Karpenter bin-packing and Spot savings**: ~10% node reduction from bin-packing = $X/month; Spot discount (~70% off EC2) applied to burst-eligible workloads = additional $X/month.

---

### Section 2: Fleet Profile and Operational Challenges

**Workload topology**:
- Production clusters: N_prod, with M_prod worker nodes, V_prod total vCPUs
- Non-production clusters: N_nonprod, with M_nonprod worker nodes, V_nonprod total vCPUs

Identify three operational challenges with exact dollar amounts from the fleet:

**Challenge 1 — Dedicated control plane overhead**
N clusters × 3 control plane nodes (m5.2xlarge) + infra nodes (r5.xlarge) = $975.25/cluster/month not serving customer workloads. Fleet total: $X/month = $Y/year in overhead EC2 and EBS spend.

**Challenge 2 — Hardware thread contention on x86**
Classic worker vCPUs on Intel/AMD instances are hyperthreads — 1 vCPU = 0.5 physical core. Compute-intensive workloads share a physical core with a co-scheduled thread, reducing effective throughput. Graviton3 ARM vCPUs are physical cores: the same workload running on ARM achieves equivalent throughput with fewer vCPUs billed.

**Challenge 3 — Capacity fragmentation from MachineSet topology**
Classic requires one MachineSet per (instance family × architecture × AZ) permutation. For this fleet that means N_machineset MachineSets across the fleet. Each MachineSet scales independently, creating allocation slack. Karpenter on HCP 4.22+ collapses all permutations into a single NodePool that selects the optimal instance at scheduling time.

---

### Section 3: Cost Analysis and Unit Economics

**Unit Economics Reference** (1-year contract, 4 vCPUs — m7i.xlarge / m7g.xlarge):

| Component | x86/Intel | ARM/Graviton |
|---|---|---|
| EC2 (1yr reserved) | $90.83/mo | $73.58/mo |
| EBS (300 GB gp3) | $24.00/mo | $24.00/mo |
| ROSA worker node fee (1yr, 4-vCPU block) | $83.34/mo | $83.34/mo |
| **Total per node/month** | **$198.17** | **$180.92** |

**Classic cluster overhead** (multi-AZ, 1yr reserved EC2+EBS for CP+infra): **$975.25/cluster/month** = **$11,703/cluster/year**
**HCP cluster fee**: **$182.50/cluster/month** = **$2,190/cluster/year**

**Classic→HCP net savings per cluster**:

| Component | Single-AZ | Multi-AZ |
|---|---|---|
| CP EC2 (3 × m5.2xlarge, PAYGO) | $841.92/mo | $841.92/mo |
| Infra EC2 (2–3 × r5.xlarge, PAYGO) | $368.64/mo | $552.96/mo |
| EBS (300 GB × 5–6 nodes) | $120.00/mo | $144.00/mo |
| Gross savings | ~$1,331/mo | ~$1,539/mo |
| Less HCP cluster fee | ($182.50/mo) | ($182.50/mo) |
| **Net savings/cluster/month** | **~$1,148** | **~$1,357** |

**Fleet-level overhead savings**: $NET_PER_CLUSTER/month × N clusters = $FLEET_NET/month = $FLEET_NET_YEAR/year.

**Graviton performance multiplier**: E = 1.25
- Formula: ARM_nodes = x86_nodes / 1.25
- For this fleet (`arm_pct`% of worker nodes): X x86 nodes → X/1.25 ARM nodes = Z node reduction
- Node reduction value: Z nodes × $198.17/node/month (x86) − (X/1.25 nodes × $180.92/node/month ARM) = $DELTA/month

---

### Section 4: Phased Migration Strategy

Two phases. Adjust sub-phase timing based on fleet size and prod/non-prod split provided.

**Phase 1 (Months 1–6): HCP Structural Migration — x86 workers, no application changes required**

No application changes are required in Phase 1. Worker nodes remain x86; only the cluster architecture changes from Classic to HCP.

- **Phase 1A (Months 1–2): Pilot wave**
  Deploy 3 non-prod clusters (or all non-prod clusters if the fleet has fewer than 3) on HCP with x86 workers. Validate cluster configuration, workload connectivity, CI/CD integration, and observability. Run old and new clusters in parallel until cutover is confirmed. Decommission pilot Classic clusters at end of Month 2.

- **Phase 1B (Months 3–4): Non-prod wave**
  Migrate remaining non-prod clusters to HCP. Parallel run for cutover month (one billing cycle overlap per cluster). Decommission Classic non-prod clusters upon validation.

- **Phase 1C (Months 5–6): Production cutover**
  Migrate production clusters to HCP with safety buffer nodes (10% over steady-state replica count) provisioned on HCP before Classic cluster deletion. Stagger production cluster migrations with one per week to contain blast radius. Decommission Classic production clusters after two-week parallel-run validation window.

**Phase 2 (Months 7–18): Compute Modernization — ARM Graviton + Karpenter**

Phase 2 is independent of application architecture — stateless workloads requiring no native compilation changes migrate first. Workloads with C/Fortran/native dependencies require multi-arch container images.

- **Phase 2A (Months 7–9): CI/CD pipeline readiness**
  Enable multi-arch container builds (docker buildx / Buildah manifest). Instrument pipelines to produce arm64 image layers. Configure Karpenter NodePools with `arch: arm64,amd64` and `capacity-type: spot,on-demand` for non-prod clusters. Validate scheduling behavior on ARM before production rollout.

- **Phase 2B (Months 10–12): Non-prod stateless migration to ARM**
  Shift stateless non-prod workloads to ARM NodePools. Measure per-workload throughput vs x86 baseline. Document any workloads requiring x86 pinning (typically JVM-heavy or native-compiled). Realize ARM EC2 rate savings ($73.58/node/month vs $90.83/node/month) plus Graviton performance uplift on non-prod fleet.

- **Phase 2C (Months 13–18): Production cluster ARM waves**
  Migrate production clusters to ARM in rolling waves — one production cluster per two-week window. Pin remaining x86-dependent workloads explicitly; everything else defaults to ARM. Realize full Graviton savings on the `arm_pct`% ARM target.

---

### Section 5: Projected Migration Timeline and Cost Analysis

Month-by-month table from Month 0 (baseline) through Month 18. Dual-run costs appear in cutover months where Classic and HCP clusters run concurrently.

Classic spend decreases as clusters are decommissioned. HCP spend accumulates as clusters come online. During cutover months, both appear in Total Bill.

Calculate per-cluster costs using the formulas in the rosa-cost skill. Use the actual fleet inputs to populate each month below. The example structure uses N_total clusters with N_nonprod non-prod and N_prod production clusters.

```
| Month | Phase                                    | Classic Spend | HCP Spend | Total Bill |
|-------|------------------------------------------|---------------|-----------|------------|
| 0     | Baseline (all Classic)                   | $X            | $0        | $X         |
| 1     | 1A: Deploy pilot HCP clusters            | $X            | $X        | $X         |
| 2     | 1A complete: pilot Classic deleted       | $X            | $X        | $X         |
| 3     | 1B: Deploy remaining non-prod HCP        | $X            | $X        | $X         |
| 4     | 1B complete: non-prod Classic deleted    | $X            | $X        | $X         |
| 5     | 1C: Deploy production HCP (staggered)    | $X            | $X        | $X         |
| 6     | 1C complete: fleet 100% HCP x86          | $0            | $X        | $X         |
| 7     | 2A: CI/CD pipeline readiness             | $0            | $X        | $X         |
| 9     | 2A complete: NodePools configured        | $0            | $X        | $X         |
| 10    | 2B: Non-prod migrates to ARM             | $0            | $X        | $X         |
| 12    | 2B complete: non-prod on ARM             | $0            | $X        | $X         |
| 13    | 2C: Production ARM wave begins           | $0            | $X        | $X         |
| 15    | 2C: Production ARM wave mid-point        | $0            | $X        | $X         |
| 18    | 2C complete: arm_pct% fleet on ARM       | $0            | $X        | $X         |
```

Annotate any month where dual-run costs exceed baseline (overlap window). Overlap cost = (Classic cluster cost for clusters not yet decommissioned) + (HCP cluster cost for clusters already provisioned). Typical overlap per cluster = one billing month of Classic + one billing month of HCP = net cost above steady-state for that transition month.

---

### Section 6: Financial and Operational Value Realization

**Phase 1 savings (Months 1–6): HCP structural migration**
- Classic CP+infra overhead eliminated: $975.25/cluster/month × N_total clusters = $X/month saved
- Less HCP cluster fee offset: $182.50/cluster/month × N_total clusters = $Y/month added
- **Net Phase 1 monthly savings at steady state**: $X/month (no application changes required)
- Annualized: $X × 12 = $Y/year

**Phase 2 savings (Months 7–18): Compute modernization**
- ARM EC2 rate reduction: (x86 rate − ARM rate) × ARM node count × 730 hrs = $X/month
- ARM node reduction from Graviton performance multiplier (E=1.25): Z nodes × $180.92/node/month = $X/month
- Karpenter bin-packing (−10% nodes): node_count × 0.10 × $198.17/node/month = $X/month
- **Net Phase 2 additional monthly savings**: $X/month
- Annualized: $X × 12 = $Y/year

**Combined savings vs baseline**:
- Phase 1 + Phase 2 monthly savings: $X/month
- Annual savings: $Y/year
- 3-year total: $Z

**Karpenter bin-packing bonus**:
Bin-packing achieves approximately 10% fewer worker nodes fleet-wide. For this fleet: (total_arm_nodes × 0.10) nodes × $180.92/node/month = $X/month = $Y/year in additional savings not captured in the ARM rate delta above.

---

### Section 7: Performance and Reliability Enhancements

**Physical cores eliminate thread contention**
ARM Graviton vCPUs are physical cores. Intel/AMD x86 vCPUs on Classic are hyperthreads — two vCPUs share one physical core. Compute-intensive workloads achieve equivalent throughput on ARM with 20–30% fewer vCPUs, reducing both EC2 cost and the ROSA worker node fee (billed per 4-vCPU block).

**DDR5 memory bandwidth on Graviton3**
Graviton3 instances (m7g, c7g, r7g) use DDR5 memory, delivering 50% higher memory bandwidth than DDR4 on comparable Intel instances (m7i, c7i, r7i). Memory-bandwidth-bound workloads (caching, analytics, data transformation) benefit directly without code changes.

**Karpenter scale-up latency**
Karpenter on ROSA HCP 4.22+ provisions replacement or burst nodes in under 45 seconds from scheduling trigger. The Classic Cluster Autoscaler requires 3–4 minutes for the same operation. This 4–5× improvement in scale-up latency directly reduces burst tail latency for stateless services.

**Karpenter consolidation**
Karpenter continuously compacts the node pool, automatically bin-packing workloads onto fewer, fuller nodes and terminating underutilized instances. The Classic autoscaler scales up reactively but does not consolidate — manual right-sizing is required to reclaim idle capacity.

**Blast radius reduction**
HCP control planes run in Red Hat's AWS account, isolated from the customer's account. A customer-account IAM incident, VPC misconfiguration, or runaway automation cannot corrupt the control plane. Classic clusters run control plane nodes in the customer's account, meaning customer-side operational errors can destabilize the cluster.

**Cluster provisioning time**
- ROSA HCP: approximately 15 minutes from `rosa create cluster` to first workload-ready node
- ROSA Classic: approximately 52 minutes for the equivalent operation
- 3.5× faster provisioning reduces time-to-capacity for new environments and disaster recovery scenarios.

---

### Section 8: Next Steps

Four concrete actions to initiate Phase 1A:

1. **IAM role and VPC configuration for HCP pilot environment**
   Create the HCP-required IAM roles (`ManagedOpenShift-HCP-ROSA-*`) and verify VPC subnets have sufficient free IP space for HCP worker nodes. HCP requires a minimum of 5 free IPs per subnet per AZ. Use `rosa verify quota` and `rosa verify permissions` to validate the target AWS account before cluster creation.

2. **Pilot cluster provisioning in target non-prod environment**
   Provision 3 HCP clusters (or the full non-prod set if smaller) in the designated non-prod AWS account. Use the same instance types and replica counts as the existing Classic clusters to produce a direct cost and performance comparison for the Phase 1A report.

3. **Migration Toolkit for Containers (MTC) connectivity validation**
   Deploy MTC in both the source Classic and target HCP clusters. Validate network connectivity between source and destination, confirm PV replication works for any stateful workloads, and run a dry-run migration of one non-critical application before the Phase 1A cutover date.

4. **Migration playbook review and approval with the customer's platform team**
   Schedule a working session with the customer's platform engineering and SRE teams to walk through the Phase 1A runbook: rollback criteria, cutover window, parallel-run duration, and decommission checklist. Confirm on-call coverage for the first production cutover (Phase 1C) before Phase 1A begins.

---

**After generating the report:**

Write all eight sections to the confirmed report path using the report file header format from the rosa-cost skill.

Create or update `reports/<customer-name>/index.md` with the complete fleet profile data collected and append a row to the Generated Reports table (date, "Strategic Advisory Report", filename).
