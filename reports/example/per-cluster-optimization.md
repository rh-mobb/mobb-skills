# ROSA Per-Cluster Optimization Guide — Example Customer

**Date:** YYYY-MM-DD
**Command:** /rosa:cost (Phase 2)
**Rates:** EC2 on-demand confirmed via AWS Pricing API — see pricing table below
**Region:** us-east-1 (N. Virginia) — all clusters

---

## Effort Key

| Symbol | Effort | Description |
|---|---|---|
| 🟢 | Quick win | No migration required; standard machine pool replace procedure |
| 🟡 | Medium | Requires planning, scheduling, or coordination |
| 🔴 | Long-term | Requires HCP, specific OCP version, Karpenter, or validated workload profiling |

**ARM prerequisite:** All ARM Graviton migrations require **Karpenter to be enabled first** (ROSA HCP 4.22+). Karpenter's NodePool configuration handles mixed-architecture scheduling and workload constraints; without it, ARM migration requires manual pool management and is higher-risk. Enable Karpenter before pursuing any ARM instance switch.

**AMD vs Intel:** Where both AMD and Intel are available for the same vCPU/memory profile, use the **cheaper of the two in the target region** — do not assume AMD is always cheaper. AMD EPYC's main advantage is higher memory bandwidth; if CloudWatch shows memory bandwidth saturation, benchmark before switching to Intel.

---

## Confirmed Instance Upgrade Pricing (us-east-1, on-demand)

Replacements at the same or lower price — confirmed via AWS Pricing API.

| Current | vCPU | GiB | $/hr | Confirmed | Replacement | $/hr | Confirmed | Delta | Note |
|---|---|---|---|---|---|---|---|---|---|
| r5.2xlarge | 8 | 64 | $0.5040 | YYYY-MM-DD | **r6i.2xlarge** | $0.5040 | YYYY-MM-DD | $0 | Intel Ice Lake — free perf upgrade |
| r5.8xlarge | 32 | 256 | $2.0160 | YYYY-MM-DD | **r6i.8xlarge** | $2.0160 | YYYY-MM-DD | $0 | Free perf upgrade |
| m5.2xlarge | 8 | 32 | $0.3840 | YYYY-MM-DD | **m6i.2xlarge** | $0.3840 | YYYY-MM-DD | $0 | Free perf upgrade |
| t3.xlarge | 4 | 16 | $0.1664 | YYYY-MM-DD | **t3a.xlarge** | $0.1498 | YYYY-MM-DD | −10% | AMD EPYC, quick win |
| t3.xlarge | 4 | 16 | $0.1664 | YYYY-MM-DD | **t4g.xlarge** | $0.1344 | YYYY-MM-DD | −19% | ARM Graviton2 — Karpenter first |

---

## Classic Clusters — $X,XXX,XXX/mo (XX% of fleet)

<!-- Classic clusters ordered cost-descending. CP and Infra rows are below the Worker total
     divider — their vCPU column is left blank (no ROSA billing); use Notes for role context. -->

### example-classic-001 — $XX,XXX/mo

| Pool | Instance | vCPU | GiB | Min→Max nodes | Min→Max vCPU | Notes |
|---|---|---|---|---|---|---|
| worker | r5.2xlarge | 8 | 64 | 3→15 | 24→120 | variable |
| worker-mem | r5.8xlarge | 32 | 256 | 3→3 | 96→96 | fixed |
| worker-gpu | g4dn.4xlarge | 16 | 64 | 0→4 | 0→64 | GPU, variable |
| **Worker total** | | | | | **120→280** | Actual (telemetry): **165 vCPU** |
| CP nodes | m5.2xlarge | 8 | 32 | 3→3 | — | Classic overhead |
| Infra nodes | r5.4xlarge | 16 | 128 | 3→3 | — | Classic overhead |

**Cost:** ROSA $X,XXX | Worker EC2+EBS $X,XXX | CP+Infra $X,XXX | **Total $XX,XXX/mo**

**Optimizations:**
🟢 **r5.2xlarge → r6i.2xlarge** — same $0.5040/hr, same 8 vCPU / 64 GiB. Free generation upgrade (Intel Ice Lake). Create new r6i pool, drain r5 pool, delete. No cost change; improved per-core throughput may reduce node count if CPU-bound.
🟡 **Capacity headroom review** — worker pool has variable range 24→120 vCPU; confirm 90-day CloudWatch node count to validate whether burst headroom is used or can be trimmed to reduce burst billing.
🔴 **ARM (r6g.2xlarge or r7g.2xlarge)** — requires Karpenter enabled first. Estimate ≈15% EC2 saving on memory-optimized pools with ARM-compatible workloads. Validate container images and no x86 affinity before migrating.

---

## HCP Clusters — $XXX,XXX/mo (XX% of fleet)

<!-- HCP clusters ordered cost-descending. No CP/Infra rows — all overhead is on Red Hat's account.
     Every pool the customer provisions is billed as a worker node. -->

### example-hcp-001 — $X,XXX/mo

| Pool | Instance | vCPU | GiB | Min→Max nodes | Min→Max vCPU | Notes |
|---|---|---|---|---|---|---|
| workers | r7i.2xlarge | 8 | 64 | 2→4 | 16→32 | variable |
| workers-compute | c7i.4xlarge | 16 | 32 | 3→6 | 48→96 | variable |
| **Total** | | | | | **64→128** | Actual (telemetry): **64 vCPU** |

**Cost:** ROSA $X,XXX | EC2+EBS $X,XXX | HCP fee $183 | **Total $X,XXX/mo**

**Optimizations:**
🟢 **No quick instance wins** — r7i and c7i are current-gen Intel; no cheaper same-tier x86 alternative confirmed in this region.
🟡 **ROSA 1-yr contract** — fleet-wide opportunity; see fleet summary.
🔴 **ARM (r7g.2xlarge / c7g.4xlarge)** — ≈15–20% cheaper for the same vCPU/mem. Requires Karpenter enabled first. Validate ARM workload compatibility before migrating.

---

### example-hcp-002 — $X,XXX/mo

<!-- Identical profile to example-hcp-001 — r7i.2xlarge workers + c7i.4xlarge compute,
     16→32 vCPU workers / 48→96 vCPU compute. Actual (telemetry): 64 vCPU. Same optimizations. -->

Identical profile to example-hcp-001. Actual (telemetry): **64 vCPU**. Same optimizations apply.

---

## Fleet Optimization Summary

Ordered by effort and impact across the fleet.

### 🟢 Quick wins — do now, no migration required

| Action | Clusters | Estimated saving |
|---|---|---|
| r5.2xlarge → r6i.2xlarge (same price, 8 vCPU / 64 GiB) | example-classic-001 | $0 cost, free perf — node reduction if CPU-bound |
| m5.2xlarge → m6i.2xlarge (same price, 8 vCPU / 32 GiB) | example-classic-001 (CP nodes) | $0 cost, free perf |
| t3.xlarge → t3a.xlarge (−10%, 4 vCPU / 16 GiB) | example-hcp-dws | **≈$XXX/mo** |

### 🟡 Medium — plan and schedule

| Action | Clusters | Estimated saving |
|---|---|---|
| ROSA 1-yr + EC2 1-yr reserved | All N clusters | **≈$X,XXX/mo** |
| Classic → HCP migration | example-classic-001, example-classic-002 | **≈$X,XXX/mo** (eliminates CP+Infra) |

### 🔴 Long-term — post-Karpenter or validated profiling

| Action | Clusters | Estimated saving |
|---|---|---|
| ARM (r7g, c7g) for eligible HCP pools *(Karpenter first)* | example-hcp-001, example-hcp-002 | **≈$X,XXX/mo** |
| Karpenter bin-packing + Spot burst *(HCP 4.22+)* | All HCP clusters | **≈$X,XXX/mo** |
| Karpenter scale-to-zero *(dev/test clusters)* | example-hcp-dev | Overnight idle elimination |
