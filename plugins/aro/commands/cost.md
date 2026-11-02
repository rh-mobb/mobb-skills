---
description: Guided wizard for ARO cost estimation, comparison, and optimization. Collects data conversationally and routes to the right analysis.
argument-hint: "[optional: what you want to know]"
---

## Name

aro:cost

## Synopsis

```
/aro:cost [what you want to know]
```

## Description

Entry point for ARO cost work. Collects fleet data conversationally, then routes to the appropriate analysis.

Use this when you are not sure which of the other commands you need.

## Implementation

0. **Customer setup**: ask for the customer name (slug-friendly, e.g. `acme-corp`) and check for an existing `reports/<customer-name>/index.md`. If it exists, read it and offer the recorded fleet profile and pricing basis as proposed values rather than re-asking for data that has not changed. Follow the customer setup process in the aro-cost skill.

1. Ask what the user wants:
   - "What does my current fleet cost?" → `/aro:cost-estimate`
   - "Should I move to HCP?" → `/aro:cost-compare`
   - "Where can I save money?" → `/aro:cost-optimize`
   - "I need a full report for a customer" → `/aro:cost-report`

2. Collect the shared inputs once, so the user is not asked twice:
   - Customer name
   - Architecture of each cluster (Standard or HCP)
   - Region
   - Control plane VM size and worker pools, or a worker vCPU budget
   - **Azure compute term**: pay-as-you-go, 1-year RI, 3-year RI, or savings plan
   - **OpenShift license commitment term** (pay-as-you-go, 1-year, 3-year) and the effective rate if known. Subscriptions transfer to HCP, so this affects the totals but cancels out of the migration delta
   - **Azure reservation scope, utilization and expiry**, needed to say whether a modeled saving translates into a reduced bill

3. Confirm regional availability if the user is considering HCP. ARO HCP is not offered in every region.

4. Hand off to the chosen command with the collected data, following the aro-cost skill throughout. Pass the customer name and confirmed output path so the user is not asked a second time.

5. After the chosen command produces its output, create or update `reports/<customer-name>/index.md` using the index format in the aro-cost skill: refresh the Fleet Profile with anything newly collected and append a row to the Generated Reports table.
