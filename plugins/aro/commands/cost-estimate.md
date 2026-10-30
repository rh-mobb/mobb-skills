---
description: Calculate monthly and annual costs for an ARO fleet at its current configuration.
argument-hint: "[cluster names, pool specs, or total worker vCPUs]"
---

## Name

aro:cost-estimate

## Synopsis

```
/aro:cost-estimate [inputs]
```

## Description

Runs the ARO cost formula over one or more clusters and reports monthly and annual spend, broken down by OpenShift license, control plane VMs and disks, worker VMs, and the HCP cluster management fee where applicable. Worker disks are excluded because they are unchanged by the architecture.

Accepts live Azure CLI cluster data, detailed pool specs, or a high-level worker vCPU budget.

## Implementation

0. **Customer setup**: ask for the customer name, check for an existing `reports/<customer-name>/index.md`, and propose the default output path `reports/<customer-name>/YYYY-MM-DD-cost-estimate.md`.

1. Resolve inputs using the input resolution rules in the aro-cost skill.
   - If no fleet data is supplied, ask which mode the user prefers (Live, Detailed, or Estimate).
   - For Live mode, confirm `az account show` first.
   - Ask whether each cluster is Standard or HCP architecture.
   - **Ask the pricing term before calculating.** Two separate questions: (a) the Azure compute term, pay-as-you-go / 1-year RI / 3-year RI / savings plan; and (b) the OpenShift license commitment term, pay-as-you-go / 1-year / 3-year. Both apply to Standard and HCP alike. Do not assume pay-as-you-go silently.
   - State the chosen basis at the top of the output.

2. Confirm VM rates for the target region with the Azure Retail Prices API rather than relying on the skill's example table. Filter out Spot, Low Priority and Windows SKUs.

3. Run the calculation formula from the aro-cost skill per cluster.

4. Output the simple cost table per cluster plus a fleet summary row, followed by the narrative.

5. For a Standard vs HCP side-by-side, direct the user to `/aro:cost-compare`. For ranked savings opportunities, direct them to `/aro:cost-optimize`.

6. Write the output to the confirmed report path and update `reports/<customer-name>/index.md`.
