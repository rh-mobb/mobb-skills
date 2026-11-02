---
description: Rank ARO cost savings opportunities with estimated savings and implementation complexity.
argument-hint: "[cluster names, pool specs, or total worker vCPUs]"
---

## Name

aro:cost-optimize

## Synopsis

```
/aro:cost-optimize [inputs]
```

## Description

Produces a ranked list of ARO cost savings opportunities for a fleet, grouped by implementation effort, with estimated annual savings for each.

## Implementation

0. **Customer setup**: ask for the customer name and propose the default output path `reports/<customer-name>/YYYY-MM-DD-cost-optimize.md`.

1. Collect fleet data using the input resolution rules in the aro-cost skill, including per-cluster VM sizes and node counts.

2. Evaluate each lever from the Optimization Levers section of the aro-cost skill against the actual fleet, and discard any that do not apply. In particular:
   - **Do not comment on control plane sizing.** Red Hat SRE sizes and operates ARO control planes, and vCPU counts alone say nothing about utilization. Report control plane cost as an input to the HCP saving, never as a finding. See the aro-cost skill.
   - Check for small clusters that would be cheaper as namespaces in a shared cluster.
   - Check whether non-production clusters dominate fleet worker vCPU, since every worker vCPU carries a license charge and right-sizing them needs no rebuild.
   - **Do not** recommend aligning worker vCPU totals to 4-vCPU block boundaries. Every supported ARO worker size except `Standard_NC6s_v3` is already a multiple of 4, so the advice is vacuous.

3. **Do not recommend ARM/Graviton migration, Spot instances, or scale-to-zero as current actions.** None are available on ARO today, and recommending them is a common error carried over from ROSA guidance. ARM has no supported sizes and is not on the roadmap. Spot and scale-to-zero arrive with Karpenter/AutoNode, which is in development for ARO HCP only: mention them as forthcoming if the customer is weighing migration timing, but never quote a saving from them. Re-check Karpenter status before each engagement, since the skill's status note dates quickly.

4. Group recommendations as 🟢 Quick, 🟡 Medium, 🔴 Long-term, with estimated annual saving and complexity for each.

5. Produce the per-cluster optimization tables and fleet summary using the **Phase 2: per-cluster optimization tables** template in the aro-cost skill.

6. Write the output to the confirmed report path and update `reports/<customer-name>/index.md`.
