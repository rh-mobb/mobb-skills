---
description: Generate a full strategic advisory report for ARO Standard-to-HCP migration with a phased plan and cost timeline.
argument-hint: "[customer name and fleet data]"
---

## Name

aro:cost-report

## Synopsis

```
/aro:cost-report [customer name and fleet data]
```

## Description

Produces a customer-ready strategic advisory report covering current fleet spend, Standard vs HCP economics, ranked optimization opportunities, and a phased migration plan with a month-by-month cost timeline.

## Implementation

0. **Customer setup**: ask for the customer name and propose the default output path `reports/<customer-name>/YYYY-MM-DD-cost-report.md`.

1. Collect complete fleet data. For a customer-facing report, do not estimate where live data is obtainable.

2. Run `/aro:cost-estimate`, `/aro:cost-compare` and `/aro:cost-optimize` logic in sequence and assemble the outputs.

3. Add a phased migration plan. ARO HCP requires a **cluster rebuild**: there is no in-place conversion path. Sequence clusters by:
   - Smallest and least critical first, to build confidence
   - Clusters with the largest proportional saving next
   - Production and large clusters last

4. Add a month-by-month cost timeline showing spend during the migration window, when both the old and new clusters run concurrently. Do not present the end-state saving as if it begins on day one.

5. Call out the operational changes explicitly: managed identity only, no in-place upgrade path from Standard, regional availability limits, and ARO HCP's public preview status.

5a. Follow the report structure and honesty requirements in the "Presenting an estimate" section of the aro-cost skill: title it a preliminary estimate, open with the basis-and-limitations block, label the figures a modeled cost subtotal with exclusions named, distinguish modeled savings from reduced payments, keep Karpenter out of the headline, and close with the data request.

6. Write the report to the confirmed path and update `reports/<customer-name>/index.md`.
