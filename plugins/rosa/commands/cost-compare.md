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

Accepts the same inputs as `/rosa:cost-estimate`: live OCM cluster IDs, detailed pool specs, or high-level vCPU estimates. Supports the same optional overrides (discount terms for ROSA and EC2, custom discount percentages).

## Implementation

1. Collect fleet data using the same input resolution as `/rosa:cost-estimate`.
   - If the user provides no fleet data, ask which mode they prefer (Live, Detailed, or Estimate).
   - Confirm `ocm whoami` if using Live mode.
   - Ask for single-AZ or multi-AZ cluster topology if not inferable.
   - Ask for contract terms (PAYGO / 1yr / 3yr) for both ROSA fee and EC2 if not specified.

2. Run the calculation formula from the rosa-cost skill twice using identical worker vCPU counts:
   - **Classic run**: include cp_total and infra_total in the total; cluster_fee = $0.
   - **HCP run**: cp_total = $0; infra_total = $0; cluster_fee = $182.50/month.

3. Output the side-by-side cost table (cost-compare variant) with Savings/mo and Savings/yr columns. Show per-cluster rows and a fleet summary row.

4. Include the fleet-level narrative: "Migrating all N clusters to HCP saves approximately $X/month ($Y/year)."

5. Show the HCP Qualitative Benefits table from the rosa-cost skill after the cost table.

6. For ranked cost optimization opportunities beyond Classic→HCP migration, direct users to `/rosa:cost-optimize`.

7. For a full strategic advisory report with a phased migration plan, direct users to `/rosa:cost-report`.
