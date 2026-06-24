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
