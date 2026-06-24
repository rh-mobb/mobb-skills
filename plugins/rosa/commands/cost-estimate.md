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

0. **Customer setup**: Follow the customer setup process from the rosa-cost skill. Ask for the customer name, check for an existing `reports/<customer-name>/index.md`, and propose the default output path `reports/<customer-name>/YYYY-MM-DD-cost-estimate.md`.

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

7. Write the full output to the confirmed report path using the report file header format from the rosa-cost skill, followed by the cost table and narrative.

8. Create or update `reports/<customer-name>/index.md` with any fleet profile data collected and append a row to the Generated Reports table (date, "Cost Estimate", filename).

For a Classic vs HCP side-by-side comparison, use `/rosa:cost-compare`.
For ranked optimization opportunities, use `/rosa:cost-optimize`.
