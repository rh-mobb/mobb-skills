---
description: Show ARO Standard vs HCP costs side-by-side for the same fleet, with migration savings.
argument-hint: "[cluster names, pool specs, or total worker vCPUs]"
---

## Name

aro:cost-compare

## Synopsis

```
/aro:cost-compare [inputs]
```

## Description

Runs the ARO cost formula over the same fleet twice, once as Standard and once as HCP, and shows the results side-by-side with a delta column.

On ARO the entire delta is three customer-billed control plane VMs and their disks versus the $182.50/month cluster management fee. The OpenShift license and worker costs are identical on both architectures for the same workload.

## Implementation

0. **Customer setup**: ask for the customer name, check for an existing `reports/<customer-name>/index.md`, and propose the default output path `reports/<customer-name>/YYYY-MM-DD-cost-compare.md`.

1. Collect fleet data using the same input resolution as `/aro:cost-estimate`.
   - Ask for the control plane VM size if not available from live data, since it drives the entire delta. Do not assume the default without saying so.
   - **Ask the Azure compute term**: pay-as-you-go, 1-year RI, 3-year RI, or savings plan. It applies to both architectures and materially changes the saving, because reserving compute makes the control plane you are deleting cheaper to keep.
   - **Ask whether an ARO license commitment is held**, 1-year or 3-year. Rates match ROSA: $83.33 and $55.58 per 4-vCPU block per month. The commitment carries over to HCP, so it affects the totals on both sides equally and cancels out of the delta. Ask so the totals are right, not because it changes the recommendation.
   - If the customer is on reserved compute, run the pay-as-you-go case as well and show both, so they can see how much of the case depends on their commitment term.

2. Run the calculation formula twice using identical worker vCPU counts:
   - **Standard run**: include `cp_vm` and `cp_disk`; `cluster_fee` = $0.
   - **HCP run**: `cp_vm` = $0, `cp_disk` = $0; `cluster_fee` = $182.50/month.

3. Show the license at the customer's committed rate on **both** sides of the table, so it is visible that it cancels. If the customer expects the commitment to be a barrier to migration, state explicitly that it travels with the workload and is not a reason to wait for renewal.

4. Output the comparison table with Delta/mo and Delta/yr columns, per-cluster rows and a fleet summary row.

5. Include the fleet narrative: "Migrating all N clusters to HCP saves approximately $X/month ($Y/year)." If the result is unfavorable, state that plainly rather than burying it.

6. Show the HCP Qualitative Benefits table from the aro-cost skill after the cost table. Several of those benefits, particularly freed subscription vCPU quota and faster provisioning, often matter more than the dollar delta.

   Include the Karpenter/AutoNode row. It is HCP-only and in development, so it is not a saving you can quote, but it is a real sequencing argument: migrating positions the customer for bin-packing, Spot and scale-to-zero, while staying on Standard forecloses them. On ARO those levers reduce the OpenShift license fee as well as the VM bill, because the license is billed on worker vCPU. Label it clearly as forthcoming.

7. State that HCP requires a cluster rebuild rather than an in-place conversion, and that the identity model changes to managed identity only.

8. Write the output to the confirmed report path and update `reports/<customer-name>/index.md`.
