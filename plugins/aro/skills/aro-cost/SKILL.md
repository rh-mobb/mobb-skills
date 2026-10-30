---
name: aro-cost
description: |
  Azure Red Hat OpenShift cost analysis and Standard→HCP migration economics, for single clusters or fleets.

  Phase 1 — Cost analysis: estimate Standard or HCP costs, compare the two with a savings delta, rank
  optimization opportunities, and produce strategic migration reports.

  Phase 2 — Per-cluster optimization: machine pool breakdowns, ordered recommendations
  (🟢 Quick / 🟡 Medium / 🔴 Long-term), confirmed VM pricing via the Azure Retail Prices API, and fleet
  summary tables.

  Accepts live Azure CLI data, detailed pool specs, or high-level vCPU estimates.

  ARO specifics: Standard bills three customer-owned control plane VMs that HCP removes, there are no ARM VM
  sizes, scale-to-zero is unsupported, and subscriptions transfer to HCP so the license cancels out of the
  delta. Also encodes modeled-versus-actual language and a mandatory basis-and-limitations block.

  NOT for: general Azure pricing, ROSA (use rosa-cost), or self-managed OpenShift on Azure.
license: Apache-2.0
metadata:
  user_invocable: "false"
  model: inherit
  color: "#0078d4"
---

# ARO Cost Reference

Cite https://azure.microsoft.com/en-us/pricing/details/openshift/ when presenting results. Rates here are current as of 2026-10. Azure VM rates vary by region and change frequently: confirm with the Azure Retail Prices API before quoting to customers.

Several statements here come from internal sources or observation rather than public documentation. Re-verify them before each engagement: subscription transfer to HCP (ARO product management, 2026-10), Karpenter/AutoNode status on ROSA and ARO, ARO HCP preview status and regional availability, and provisioning times.

## Presenting an estimate: modeled, not actual

Everything this skill produces from public rates and a cluster inventory is a **preliminary estimate**. It has not been reconciled to the customer's billing records. Get this framing right or the customer will treat a model as a quote.

**Title deliverables as estimates**, not analyses of what the customer pays. "Preliminary ARO Standard-to-HCP Cost Estimate", not "ARO Cost Analysis".

**Open every report with a basis-and-limitations block**, directly above the executive summary. Adapt this:

> This analysis uses the supplied cluster inventory, publicly available pricing and product information, and modeling assumptions. The figures have not been reconciled to {customer}'s Azure billing records, negotiated discounts, reservation coverage, or OpenShift subscription terms. {customer} should confirm the actual resource configurations, effective costs, remaining commitments, and applicable HCP pricing with its Microsoft and Red Hat account teams before using these estimates for budgeting or migration decisions. Savings represent potential ongoing cost reductions; their amount and timing depend on contract terms and implementation. Migration costs and temporary parallel operation are excluded.

**Use modeled language consistently.** The difference is not cosmetic: one is a claim about the customer's finances, the other about your model.

| Write | Not |
|---|---|
| "the modeled 3-year reserved compute scenario" | "the customer's current pricing" |
| "the model estimates $22,343/month" | "the customer pays $22,343/month" |
| "~$13,100/month, ~$157,000/year" | "$13,091/month, $157,092/year" |
| "control plane capacity is removed on HCP" | "oversized control planes" |

**Round to the precision the inputs justify.** Dollar-level precision on a figure built from a 0.38× planning multiplier implies an accuracy the model does not have. Round headline figures to the nearest hundred per month and nearest thousand per year. Keep full precision inside tables where lines must reconcile, and round the narrative.

### A modeled saving is not a reduction in payments

This is the most common way a cost report misleads. Removing resources reduces modeled consumption; it does not automatically reduce the bill.

- **Azure reservations are a commitment, not a per-resource discount.** Deleting the VMs a reservation was sized for does not cancel the commitment. Azure may apply the benefit to other matching resources in the reservation's scope; where none exists, the reserved hours go unused. Always ask for reservation scope, utilization and expiry dates.
- **The same applies to a prepaid or committed license.** Reducing licensed worker vCPU lowers future requirements without necessarily reducing a commitment already paid for.

State plainly that **the timing of any realized saving depends on reservation scope, utilization and expiry**, not only on when clusters migrate.

### Label totals honestly and list what is excluded

A table of modeled line items is a **"Modeled cost subtotal"**, never "total platform spend". Name the exclusions explicitly: worker node disks, application and persistent storage, networking and egress, load balancers, backup, logging and monitoring data costs, and Azure services consumed by the applications.

Those are legitimately omitted because they are broadly unchanged by the architecture decision — say that too, so the omission reads as deliberate rather than careless.

**Always exclude, and say you have excluded:** migration project effort, any period of parallel operation running both environments, and any remaining commitment that outlives the migration. Do not quote first-year savings or payback until those are costed.

### Close with a data request

End any fleet report with what you would need to firm it up: Azure actual and amortized cost exports, VM and disk inventory by cluster and region, reservation utilization and expiry with scope, confirmation of effective license rates, resource request-versus-usage data from two or three representative clusters, and migration constraints such as change windows or compliance requirements.

## Pricing term: ask before you calculate

**Never run an ARO cost analysis without first establishing the pricing term.** Ask explicitly, and state the chosen basis in every output.

Ask two separate questions. They are different commitments and are frequently confused:

**1. Azure compute term** — applies to VM cost on **both** architectures.

| Term | Multiplier | Ask as |
|---|---|---|
| Pay-as-you-go | 1.00× | "No commitment" |
| 1-year reserved instance | ~0.58× | "1-year RI" |
| 3-year reserved instance | ~0.38× | "3-year RI" |
| Azure savings plan (1yr, flexible) | ~0.65× | "Savings plan rather than RI" |

**2. ARO license commitment** — 1-year or 3-year, at the same rates as ROSA.

| Term | Per 4-vCPU block | Discount |
|---|---|---|
| Pay-as-you-go | $124.83/month ($0.171/hr, listed also as $1,500/year) | — |
| 1-year commitment | $83.33/month ($1,000/year) | 33% |
| 3-year commitment | $55.58/month ($667/year) | 55% |

**ARO subscriptions transfer from ARO Standard to ARO HCP.** Confirmed with ARO product management, 2026-10. The same rate applies on both architectures, so the license line is identical on each side of the comparison and cancels out of the delta. Ask for the term so the totals are right, but never model it as a migration cost or a forfeited benefit.

If a customer raises the parenthetical on the Azure pricing page restricting reservations to "standard architecture": the same page states HCP pricing "is not yet reflected here", and transfer is confirmed. Point them at their Microsoft account team to confirm their own effective rate.

### HCP is always cheaper, by a predictable amount

Because the license cancels, the Standard to HCP delta reduces to:

```
monthly_saving = cp_vm + cp_disk - cluster_fee
```

This is always positive for a real cluster: three control plane VMs plus their disks cost far more than $182.50/month. There is no break-even to compute and no scenario in which Standard is cheaper. The only question is how large the saving is, which depends on the **Azure compute term**, not the license term.

Worked example, a 15-cluster fleet with 732 control plane vCPU:

| Azure compute basis | Modeled monthly saving | Annual |
|---|---|---|
| Pay-as-you-go | ~$29,000 | ~$348,000 |
| 3-year reserved | ~$13,100 | ~$157,000 |

Reserving compute reduces the saving, because it makes the control plane being deleted cheaper to run. It never eliminates it.

### Reserved compute shifts what matters

Control plane disks are a material part of the saving at every term. Under 3-year RI, VM cost drops ~62% while **managed disks are not covered by compute reservations and do not drop at all**, so their share grows. The share also depends on control plane size, because disk cost is fixed per cluster:

| Disk share of the gross control plane saving | Pay-as-you-go | 3-year RI |
|---|---|---|
| Default cluster (3 × `Standard_D8s_v5`) | ~33% | ~56% |
| Fleet above (15 clusters, 732 control plane vCPU) | ~19% | ~38% |

When the customer is on reserved compute, verify disk sizing rather than estimating it.

## Never characterize control plane sizing

**Report control plane vCPU as a cost input. Do not call it oversized, over-provisioned,
inconsistent, or a candidate for review, and do not recommend resizing it.**

Red Hat SRE sizes and operates ARO control planes. A fleet inventory shows vCPU counts
and nothing else: no etcd metrics, no API server request rates, no object counts, no
control plane utilization. A three node cluster with large masters may be sized for its object count, its API load, or a past incident. Inferring waste from the
ratio of control plane vCPU to worker vCPU is not supported by the data a cost analysis
has access to, and it reads as criticism of a managed service the customer does not
operate.

What you can legitimately say:

| Say | Do not say |
|---|---|
| "This cluster carries 96 control plane vCPU, worth $X/month on Standard" | "This control plane is oversized for 6 compute nodes" |
| "Control plane cost is eliminated on HCP regardless of current sizing" | "Right-size the control plane to reduce cost" |
| "Clusters with more control plane vCPU yield a larger per-cluster saving" | "Several control planes are larger than their node count warrants" |

The useful framing is that HCP removes this cost **whatever the sizing is**, so the
question of how a given control plane is sized never has to be answered.
That is a stronger argument than second-guessing it, and it does not require data you
do not have.

If a customer asks about control plane sizing, route it to their Red Hat
account team or SRE rather than answering from an inventory.

## How ARO differs from ROSA

Do not port ROSA cost logic directly. The relevant differences:

| | ROSA Classic | ARO Standard |
|---|---|---|
| Control plane | **Customer-billed EC2** on Classic, removed on HCP | **Customer-billed VMs** on Standard, removed on HCP |
| Infrastructure nodes | Mandatory customer-billed EC2, 2–3 per cluster on Classic | **Not deployed by default** |
| ARM / Graviton | Supported, a major savings lever | **No ARM sizes in the supported list** |
| Karpenter | ROSA HCP 4.22+ (AutoNode), per the rosa-cost skill; re-check | **In development for ARO HCP**, not yet available. See the Karpenter section |
| Scale to zero | Supported with Karpenter | **Unsupported today**, deallocating cluster VMs voids support |
| Subscription transfer to HCP | Supported | **Supported** (confirmed with ARO PM, 2026-10) |

The headline consequence: on ROSA the Classic→HCP saving removes both control plane and infra nodes; on ARO it is driven almost entirely by eliminating three control plane VMs and their disks, offset by the cluster management fee. There is no infra-node saving to count, and no ARM or Spot lever to layer on afterwards.

**Do not mention ROSA in customer-facing ARO deliverables.** An ARO customer does not care how ROSA behaves, and the comparison reads as a non-sequitur. Use it to inform your own modeling only.

## ARO Service Fees

### OpenShift License Fee

Charged on **worker** vCPUs only. Flat per-core rate, identical regardless of VM series, size or generation.

| Term | Rate per 4 worker vCPUs | Monthly per 4-vCPU block |
|---|---|---|
| Pay-as-you-go | $0.171/hr | $124.83 |
| 1-year commitment | ~$0.114/hr ($1,000/year) | $83.33 |
| 3-year commitment | ~$0.076/hr ($667/year) | $55.58 |

Billing unit is the 4-vCPU block and does not fractionalize below it. Control plane nodes are never charged a license fee on either architecture.

Microsoft does not publish reserved license rates on the pricing page. Ask the customer for their negotiated rate, or refer them to their Microsoft account team. The rates above match ROSA's and are a reasonable planning basis, but confirm rather than assume.

### HCP Cluster Management Fee

$0.25/cluster/hr = **$182.50/cluster/month** = $2,190/cluster/year.

ARO HCP only. Standard clusters have no cluster-level fee. Not discounted by any reservation. This matches the ROSA HCP cluster fee.

**ARO HCP is described as public preview.** Note its status and regional availability in any migration recommendation, and re-check before each engagement.

## Azure VM Rates

Billed separately from the license fee at standard Linux VM pricing. Representative on-demand rates (eastus2, 2026-10):

| VM size | vCPU | GiB | $/hr | $/vCPU/hr | Profile |
|---|---|---|---|---|---|
| Standard_D4s_v5 | 4 | 16 | $0.1920 | $0.048 | General purpose |
| Standard_D8s_v5 | 8 | 32 | $0.3840 | $0.048 | General purpose |
| Standard_D16s_v5 | 16 | 64 | $0.7680 | $0.048 | General purpose |
| Standard_D8s_v3 | 8 | 32 | $0.3840 | $0.048 | General purpose |
| Standard_E8s_v5 | 8 | 64 | $0.5040 | $0.063 | Memory optimized |

Rule of thumb: **general purpose D-series ≈ $0.048/vCPU/hr, memory-optimized E-series ≈ $0.063/vCPU/hr.** Use for rough sizing only. If the worker SKU mix is unknown, say that pricing memory-optimized workers as general purpose understates cost by roughly 31% on those nodes.

Confirm real rates with the Azure Retail Prices API (no auth required):

```bash
curl -s "https://prices.azure.com/api/retail/prices?\$filter=armRegionName%20eq%20'eastus2'%20and%20armSkuName%20eq%20'Standard_D8s_v5'%20and%20priceType%20eq%20'Consumption'%20and%20serviceName%20eq%20'Virtual%20Machines'" \
  | python3 -c "import sys,json;[print(i['armSkuName'],i['retailPrice'],i['skuName']) for i in json.load(sys.stdin)['Items']]"
```

Filter out `Spot` and `Low Priority` SKUs and any `Windows` product names.

### Azure discount multipliers

| Term | Multiplier |
|---|---|
| Pay-as-you-go | 1.00× |
| 1-year reserved instance | ~0.58× |
| 3-year reserved instance | ~0.38× |
| Azure savings plan for compute (1yr) | ~0.65× |

Reserved instances lock a VM series and region; savings plans are flexible across series. Azure compute discounts apply to both Standard and HCP. Ask customers for their actual negotiated rates (MACC, EA) rather than assuming list price, and label the multiplier as a planning figure where they cannot supply one.

## Control plane disks

Model at **1,024 GiB Premium SSD LRS per control plane node**, roughly $135/month each, three per Standard cluster.

The basis is Microsoft's ARO service definition, which documents 1,024 GiB Premium SSD LRS disks for Standard architecture control plane nodes. Cite it rather than inferring the size from etcd IOPS requirements — the throttling rationale is plausible but not something to assert categorically to a customer.

Two things to say when this line is material:

- **Reserved instances do not cover managed disks.** When compute is reserved, VM cost falls while disk cost does not, so disks become a much larger share of the saving. At 3-year RI this line is ~56% of the gross control plane saving for a default cluster, less where control plane VMs are larger (see the table above).
- **Inspecting one cluster does not validate a fleet.** Checking one managed resource group with `az disk list` confirms that cluster only. Clusters built at different times or OpenShift versions may differ. Ask for a disk inventory across all clusters.

## ARO Node Defaults and Constraints

| Node role | Standard | HCP | License fee? |
|---|---|---|---|
| Control plane | 3 mandatory, default `Standard_D8s_v5` | none, hosted | No |
| Worker | 3 minimum, default `Standard_D4s_v5` | node pools | **Yes** |

Hard constraints that rule out several common savings plays:

- Minimum **three** workers and **three** control plane nodes on Standard.
- Maximum **250** worker nodes per cluster.
- **Do not scale workers to zero.** Deallocating or powering down cluster VMs is unsupported.
- **No ARM/Graviton.** The supported VM list contains no Ampere (Dpsv5/Epsv5) sizes. AMD (`Das_v5`, `Eas_v5`) is supported and is often marginally cheaper than the Intel equivalent at the same vCPU/GiB: compare both.
- **No Karpenter today.** ARO uses MachineSets and the standard cluster autoscaler. Karpenter is in active development for ARO HCP: see the next section before advising on a migration timeline.
- Worker VM sizes are drawn from a published supported list spanning D/E/F/L/M/NC/ND series. Validate any proposed size against the ARO support policy before recommending it.

**Do not recommend aligning worker totals to 4-vCPU block boundaries.** Every supported ARO worker size is already a multiple of 4 vCPU (the sole exception is `Standard_NC6s_v3` at 6), so any realistic node count already lands on a block boundary. The advice sounds precise and is vacuous. The real node-sizing lever is overhead, below.

## Karpenter / AutoNode on ARO (forthcoming, not yet available)

**Status as of 2026-10: in development. Not GA, and not yet in public preview.** Do not tell a customer they can use it today, and do not put savings from it in a current-state cost model. Treat it as roadmap input to a migration *decision*, not as a line item.

Timing is sometimes given as early 2027, and the capability is understood to be HCP-only. **Both are subject to confirmation** and could not be verified in public sources. Verify against an approved Red Hat roadmap source before putting either in front of a customer, and label them as subject to confirmation if you cannot.

What is publicly verifiable:

| Evidence | What it shows |
|---|---|
| `Azure/ARO-HCP` PR #7542 (WIP) | Karpenter-backed **AutoNode** wiring across the ARO-HCP API, backend controllers, managed identities and monitoring. Introduces a `2027-03-30-preview` API version |
| `openshift/hypershift` PR #9545 (AUTOSCALE-974/980) | HyperShift CLI and Operator able to deploy Karpenter Provider Azure end to end, with Azure workload identity, `VNET_SUBNET_ID` and `AZURE_NODE_RESOURCE_GROUP` wiring |
| `openshift/Azure-karpenter-provider-azure` | OpenShift fork of the AKS Karpenter provider |

Two consequences matter for cost advice:

**1. It appears to be an HCP-only capability.** The work lands in ARO-HCP and HyperShift. For a customer weighing Standard→HCP this is a second argument for migrating beyond the control plane saving: it is the only path onto Karpenter later. Say so, flagged as forthcoming and subject to confirmation.

**2. On ARO the effect would be doubled relative to a pure-IaaS platform.** Reducing provisioned worker vCPU cuts **both** the Azure VM bill **and** the OpenShift license, because the license is charged per worker vCPU. A 25% reduction in provisioned worker vCPU therefore reduces both lines.

Expected levers once it lands, each currently unavailable:

- **Bin-packing and consolidation** — reduces licensed worker vCPU, the dominant cost at scale
- **Spot instances** — Karpenter Provider Azure supports Spot with NodePool weighting and On-Demand fallback. AKS Node Auto Provisioning, built on the same provider, is GA, so the capability is proven on Azure. Spot specifics for ARO HCP are not yet documented
- **Scale to zero** — currently unsupported on ARO and a stated reason not to recommend it
- **Instance-type diversity** — Karpenter selects sizes per workload rather than per MachineSet

Controllers run in the hosted control plane on the ROSA implementation, so they add no worker compute overhead. Expect the same on ARO HCP, but confirm when it ships.

### How to handle it in cost output

- **Keep it out of the headline and out of current-state numbers.** Present it as a separate, conditional opportunity that depends on availability, applicability to the customer's workloads, and successful implementation.
- Title any sensitivity table **"Illustrative worker-capacity reduction scenarios"**, not "Expected results". Define the percentages as **reductions in provisioned worker vCPU**, not "bin-packing gains" — the latter implies a mechanism and a confidence you do not have.
- **Never add Karpenter savings to right-sizing savings.** Capacity recovered by right-sizing today is capacity Karpenter cannot recover again later. They are alternative routes to the same reduction, with Karpenter automating what would otherwise be manual and ongoing. Say this explicitly wherever both appear.
- If you show a combined migration-plus-capacity figure, keep it out of the headline and state that it depends on two independent conditions, neither established.
- **Sizing assessments must cover memory as well as CPU**, together with scheduling constraints, anti-affinity and availability requirements, workload peaks, and node-level requirements such as taints or specialized hardware. Reductions achievable on paper from CPU requests alone frequently do not survive those constraints.
- Offer to **"produce a better-supported estimate"** by measuring two or three representative clusters. Do not promise to "turn this into a firm number".
- Re-check status before every engagement. This section will date quickly.

## Input Resolution

Detect the mode from what the user provides.

### Live Mode — Azure CLI

```bash
# Standard clusters
az aro list -o table
az aro show -g <rg> -n <name> \
  --query "{ver:clusterProfile.version,cp:masterProfile.vmSize,workers:(workerProfilesStatus || workerProfiles)[].{pool:name,size:vmSize,count:count,diskGb:diskSizeGb}}"

# HCP clusters — needs the preview aro extension: az extension add --name aro
az aro hcp cluster list -o table
az aro hcp cluster nodepool list -g <rg> -c <name> -o table
```

**Use `workerProfilesStatus`, not `workerProfiles`.** `workerProfiles` is the worker profile sent in the create request, so it reflects install time only and undercounts any cluster scaled or given extra MachineSets since. `workerProfilesStatus` is the resource provider's read-only observed status, enriched from the cluster's MachineSets, but its update latency is not documented. Read every entry, not just `[0]`. Where you have cluster access, cross-check with `oc get machinesets -n openshift-machine-api`, especially after a recent scale event.

### Detailed Mode — Pool Spec Block

Accept a per-cluster block: cluster name, region, control plane VM size, worker pools (VM size × count), license term, Azure discount term.

### Estimate Mode — vCPU Budget

Accept a total worker vCPU figure. Assume `Standard_D8s_v5` workers and three `Standard_D8s_v5` control plane nodes unless told otherwise. State the assumption in the output.

## Calculation Formula

Per cluster, per month (730 hours).

```
worker_vcpus     = sum of (replicas × vcpus_per_vm) across worker pools
                   (control plane excluded)

# OpenShift license — worker vCPUs only, same rate on both architectures
license_block    = $124.83 PAYGO | $83.33 1yr | $55.58 3yr, per 4 vCPU/month
                   ASK the customer. Subscriptions transfer to HCP.
azure_discount   = 1.00 PAYGO | 0.58 1yr RI | 0.38 3yr RI | 0.65 savings plan
                   ASK the customer. Never assume. Applies to both architectures.
license_fee      = ceil(worker_vcpus / 4) × license_block

# Cluster management fee
cluster_fee      = $182.50/month (HCP only); $0 for Standard

# Worker VMs (worker disks excluded: unchanged by architecture, listed as an exclusion)
worker_vm        = worker_vcpus × vcpu_rate × azure_discount × 730

# Control plane VMs — Standard only; $0 on HCP
cp_vm            = 3 × cp_vcpus × vcpu_rate × azure_discount × 730   # default D8s_v5
cp_disk          = 3 × 1024 GiB Premium SSD LRS ≈ 3 × $135           # see disk section

# Per-cluster modeled subtotal
cluster_total    = license_fee + cluster_fee
                 + worker_vm
                 + cp_vm + cp_disk
```

Fleet subtotal = sum of all per-cluster subtotals. Label it a **subtotal** and list the exclusions.

The license fee and worker costs are identical on both architectures for the same workload. **The entire delta is control plane VMs and disks versus the cluster management fee.**

## Standard→HCP Savings Per Cluster

PAYGO, eastus2, default control plane sizing.

| Component | Standard | HCP | Delta/month |
|---|---|---|---|
| Control plane VMs (3 × D8s_v5 @ $0.3840/hr) | $840.96 | $0 | **+$840.96** |
| Control plane disks (3 × 1,024 GiB Premium SSD) | ~$405 | $0 | **+$405** |
| Cluster management fee | $0 | $182.50 | −$182.50 |
| OpenShift license (worker vCPU) | unchanged | unchanged | $0 |
| Worker VMs | unchanged | unchanged | $0 |
| **Net modeled saving per cluster** | | | **~$1,060/month** |

Roughly **$12,800 per cluster per year** at pay-as-you-go, independent of cluster size.

**Always include control plane disks in per-cluster figures.** For a default cluster, omitting them understates the net saving by ~38% at PAYGO ($405 of ~$1,063) and ~75% at 3-year RI ($405 of ~$543), less where control plane VMs are larger. It is an easy mistake when working from vCPU counts alone.

Adjust the control plane line for non-default sizes and for the customer's Azure compute term. At a 0.38× 3-year RI multiplier the same cluster models at roughly $543/month, because the VM component shrinks while the disk component does not.

## Where the saving is largest

The saving is a fixed amount per cluster, while license and worker costs scale with workload. Consequences:

- **Small clusters win proportionally.** A 3-worker cluster carries the same three control plane VMs as a 50-worker cluster, so the saving is a much larger share of its total.
- **Fleet count multiplies it.** The saving is per cluster. Twenty clusters at ~$1,060/month is roughly **$254,000/year** at PAYGO.
- **Large clusters still save**, just a smaller percentage of a bigger bill.
- **Clusters with more control plane vCPU save most**, simply because there is more to remove. Report the figure; do not characterize the sizing. See the rule below.

HCP is most compelling for **fleet density**: many small or medium clusters where three control plane VMs per cluster dominate the bill. Every cluster saves something, so there is no qualifying threshold to apply.

## HCP Qualitative Benefits

Include after the cost table. Several of these matter more than the dollar delta.

| Feature | Standard | HCP | Benefit |
|---|---|---|---|
| Control plane management | Customer subscription | Hosted | No control plane VMs to size, patch or pay for |
| Control plane fault domain | Shares customer subscription limits | Isolated | Reduced blast radius |
| Cluster provisioning time | ~35–45 min | ~15–20 min | Faster environment turnaround |
| Identity model | Service principal or managed identity | Managed identity only | No secret rotation burden |
| Control plane scaling | Manual resize | Managed | One fewer sizing decision |
| Cost predictability | Varies with control plane VM size | Flat $182.50/cluster | Simpler chargeback |
| Subscription vCPU quota | Consumed by control plane | Not consumed | Quota freed for workloads |
| Karpenter / AutoNode | Not available | **Forthcoming**, subject to confirmation | Only path to bin-packing, Spot and scale-to-zero on ARO |

The quota point is concrete and worth quantifying: migration returns the full control plane vCPU count to the subscription quota.

## Optimization Levers (ARO-specific, ranked)

🟢 **Quick — no migration**

1. **Review non-production sizing.** Test and development frequently dominate fleet worker vCPU, and every worker vCPU carries a license charge. Needs no rebuild and compounds with everything else.
2. **Apply an Azure savings plan or reserved instances to VMs.** Applies to both architectures and to control plane VMs on Standard.
3. **Measure capacity headroom** on two or three representative clusters, covering CPU, memory, scheduling constraints and peaks. Can be done on Standard before any migration.

🟡 **Medium**

4. **Compare AMD (`Das_v5`, `Eas_v5`) against Intel equivalents.** Often cheaper at identical vCPU and memory.
5. **Consolidate small clusters.** Each Standard cluster carries three control plane VMs; each HCP cluster carries a $182.50 fee. Below a certain workload size, a namespace in a shared cluster is far cheaper than a dedicated one.
6. **Consolidate onto fewer, larger worker nodes** where workload shape allows. The license is charged on every provisioned worker vCPU, including capacity each node reserves for the kubelet and operating system. That reservation is broadly fixed per node, so the same total spread across fewer, larger nodes leaves more available for workloads. Quantifying it requires measured node allocatable figures — do not invent a percentage.

🔴 **Long-term**

7. **Standard→HCP migration.** HCP requires a **cluster rebuild**, not an in-place conversion: budget for workload migration, and note the identity model changes to managed identity only. Sequence on **workload risk, application compatibility and business criticality**, not version age alone — an old cluster that is also the most business-critical is a poor first candidate. Include migration effort and any parallel-running period before quoting payback.
8. **Fleet standardization** on a small number of VM sizes to simplify reservation coverage.
9. **Plan for Karpenter/AutoNode** once it ships on ARO HCP. Never quote a saving from it. See the Karpenter section, including the warning against double-counting it with right-sizing.

Deliberately absent, because they do not apply to ARO **today**: ARM/Graviton migration (no supported sizes, and none on the roadmap), Spot instances, and scale-to-zero. Do not recommend Spot or scale-to-zero as current actions. Both arrive with Karpenter on HCP; treat them as forthcoming rather than unavailable forever, and re-check status before each engagement.

## Confirmed Pricing Registry

Append confirmed rates after each engagement.

| Date | Region | VM size | $/hr | Source |
|---|---|---|---|---|
| 2026-10 | eastus2 | Standard_D4s_v5 | $0.1920 | Azure Retail Prices API |
| 2026-10 | eastus2 | Standard_D8s_v5 | $0.3840 | Azure Retail Prices API |
| 2026-10 | eastus2 | Standard_D16s_v5 | $0.7680 | Azure Retail Prices API |
| 2026-10 | eastus2 | Standard_D8s_v3 | $0.3840 | Azure Retail Prices API |
| 2026-10 | eastus2 | Standard_E8s_v5 | $0.5040 | Azure Retail Prices API |

## Engagement Lessons

Append observations from real engagements.

- 2026-10: ARO default control plane is `Standard_D8s_v5` and default worker is `Standard_D4s_v5` at 3 replicas, confirmed from a live 4.21.22 cluster. Guidance citing `Standard_D8s_v3` as the control plane default is stale.
- 2026-10: Microsoft does not publish reserved license rates on the pricing page. Always ask the customer.
- 2026-10: ARO HCP is not available in every region, and is described as public preview. Confirm regional availability and service status before scoping a migration, and expect source and target to need co-location for migration throughput.
- 2026-10: **ARO subscriptions transfer from Standard to HCP**, confirmed with ARO product management. Earlier guidance that a Standard license reservation is forfeited on HCP was wrong, and materially distorted migration recommendations. The license cancels out of the delta.
- 2026-10: A per-cluster saving computed from control plane vCPU alone understates the result, by ~38% for a default cluster at PAYGO and ~75% at 3-year RI. Control plane **disks** are a large, separately-priced component that reserved compute does not discount. Always include them.
- 2026-10: `az aro show` `workerProfiles` is install-time only. Live inventories must read `workerProfilesStatus`, across all pools, or scaled clusters are undercounted.
- 2026-10: Customer review feedback on a 15-cluster fleet report. The substantive asks were all about epistemic honesty rather than arithmetic: title it an estimate, distinguish modeled savings from reduced payments, do not treat planning multipliers as the customer's pricing, label subtotals, list exclusions, and keep conditional roadmap items out of the headline. Arithmetic errors in that report were minor by comparison. Budget review effort accordingly.
- 2026-10: Advice to "align worker vCPU to 4-vCPU block boundaries" does not survive contact with the supported VM list — every worker size except `Standard_NC6s_v3` is already a multiple of 4. Removed.

## Output Templates

### Comparison table

State the pricing basis immediately above every table, for example
"3-year Azure RI on compute, license at the customer's 3-year committed rate".
A table without a stated basis is not usable by the customer.

Where the customer is on reserved compute, also run and show the
pay-as-you-go case, so they can see how much of the migration case depends
on their commitment term.

```
| | Standard | HCP | Delta/mo | Delta/yr |
|---|---|---|---|---|
| Cluster management fee | $0 | $182.50 | ($182.50) | ($2,190) |
| OpenShift license (worker vCPU) | $X | $X | $0 | $0 |
| Control plane VMs | $X | $0 | $X | $X |
| Control plane disks | $X | $0 | $X | $X |
| Worker VMs | $X | $X | $0 | $0 |
| **Modeled cost subtotal** | **$X** | **$X** | **$X** | **$X** |
```

Show control plane VMs and disks on separate rows. The disk line is large enough at reserved pricing that collapsing it invites the customer to assume it was estimated rather than modeled.

### Phase 2: per-cluster optimization tables

`/aro:cost-optimize` adds these after the ranked fleet-level levers, in the same report file.

Open with confirmed pricing for every VM swap you recommend. Confirm each rate with the Azure Retail Prices API and add it to the Confirmed Pricing Registry:

```
## Confirmed VM pricing (<region>, pay-as-you-go)

| Current | vCPU | GiB | $/hr | Proposed | $/hr | Delta | Note |
|---|---|---|---|---|---|---|---|
| Standard_D8s_v5 | 8 | 32 | $0.3840 | Standard_D8as_v5 | $X | X% | AMD, same vCPU/GiB |
```

Then one section per cluster, most expensive first:

```
### <cluster-name> — ~$X,XXX/mo modeled (Standard | HCP)

| Pool | VM size | vCPU | GiB | Nodes min→max | Worker vCPU min→max | Notes |
|---|---|---|---|---|---|---|
| worker | Standard_D8s_v5 | 8 | 32 | 3→6 | 24→48 | autoscaling |
| **Worker total (licensed)** | | | | | **24→48** | |
| Control plane | Standard_D8s_v5 | 8 | 32 | 3 | — | Standard only; removed on HCP |

**Modeled cost:** License $X | Worker VMs $X | Control plane VMs + disks $X (Standard) or cluster fee $182.50 (HCP) | **Subtotal ~$X/mo**

**Optimizations:**
🟢 ...
🟡 ...
🔴 ...
```

Rules:

- The control plane row is a cost input. Never comment on its sizing (see **Never characterize control plane sizing**).
- Worker vCPU counts licensed capacity only. Take min→max from the MachineSet autoscaler on Standard or node pool autoscaling on HCP. For fixed pools, min equals max.
- Draw optimizations only from **Optimization Levers** above, ordered 🟢, 🟡, 🔴. Never ARM, Spot or scale-to-zero as current actions.
- Compare AMD against Intel in the customer's region before recommending either. Do not assume AMD is cheaper.
- For identical cluster profiles, document the first in full and give each duplicate one line: "Identical profile to <cluster>. Same optimizations."

Close with a fleet summary:

```
| Effort | Lever | Clusters | Modeled annual saving |
|---|---|---|---|
| 🟢 | ... | N | ~$X |
```

Do not total levers that overlap. Right-sizing and Karpenter recover the same capacity, and consolidating a cluster away removes its HCP migration saving.

### Report structure

For a fleet engagement:

1. Title as a **preliminary estimate**
2. **Basis and limitations** block, above the executive summary
3. Executive summary — headline saving rounded, with qualifications listed
4. Fleet inventory as supplied
5. Modeled cost comparison, labelled a subtotal, with exclusions named
6. Modeled savings versus reduced payments
7. Control plane disks, with the service-definition basis
8. Per-cluster modeled saving
9. Karpenter as a separate conditional section, excluded from the headline
10. Observations, recommendations (🟢/🟡/🔴), qualitative considerations
11. Assumptions table — assumption, basis, validation needed
12. Information required to firm up the estimate

### Narrative

Three to five sentences after any table:
- Modeled spend at the current configuration, monthly and annual, rounded
- Largest cost driver
- The modeled saving and what it is conditional on
- Top recommendation with estimated annual saving and implementation complexity (low / medium / high)

## File Output Conventions

All commands write their output to the `reports/` directory. Collect the customer name at the start of every command and use it to determine the output path.

Customer report directories hold commercially sensitive data: fleet inventories, negotiated rates, and commitment terms. **Before writing the first report for a customer, check that `reports/` is excluded from version control, and tell the user if it is not.** Do not assume it is — the exclusion exists in the mobb-skills repo, but not in an arbitrary working directory.

Never read another customer's report directory as a source. It will not exist for other users and is not authoritative. This skill contains every template needed.

### Directory structure

```
reports/
└── <customer-name>/
    ├── index.md                          # Customer profile and report history
    ├── YYYY-MM-DD-cost-estimate.md
    ├── YYYY-MM-DD-cost-compare.md
    ├── YYYY-MM-DD-cost-optimize.md
    └── YYYY-MM-DD-cost-report.md
```

### Customer setup — start of every command

1. Ask: "What's the customer name?" (use a slug-friendly form, e.g. `acme-corp`)
2. Check whether `reports/<customer-name>/index.md` exists.
   - If it exists: read it and surface the recorded values — the user confirms or overrides, rather than re-entering unchanged data.
   - If it does not exist: collect the data normally and create the index when done.
3. Propose the default output path and confirm: `reports/<customer-name>/YYYY-MM-DD-<report-name>.md`. Accept an alternative if the user supplies one.
4. Establish the pricing basis before calculating anything. Follow **Pricing term: ask before you calculate** above — both the Azure compute term and the ARO license commitment, asked as two separate questions. Also capture:

   | Parameter | Default | What to ask |
   |---|---|---|
   | Azure region | — ask, no default | "Which Azure region are the clusters in?" |
   | Azure reservation scope | — ask if compute is reserved | "Is the reservation shared or single-subscription, and what is its utilization?" |
   | Reservation expiry | — ask if compute is reserved | "When does the current commitment expire?" |

   Reservation scope, utilization and expiry are what decide whether a modeled saving becomes a reduced invoice. Without them the output can only claim a modeled saving. If `index.md` already records these, show them as proposed values and let the user correct them.

   **Do not start any calculation until the pricing basis is confirmed.** A single batch message listing each parameter and its proposed value is fine — the user can reply "all confirmed" or correct individual entries.

### Report file header

Begin every report file with:

```markdown
# Preliminary ARO <Report Type> Estimate — <Customer Name>

**Date:** YYYY-MM-DD
**Command:** /aro:<command-name>
**Basis:** <Azure compute term>, license at <license term>
**Rates:** current as of 2026-10 — verify at https://azure.microsoft.com/en-us/pricing/details/openshift/ before quoting

---
```

Follow with the basis-and-limitations block, then the full command output.

### index.md format

```markdown
# <Customer Name> — ARO Cost Estimates

**Last updated:** YYYY-MM-DD

## Fleet Profile

- **Cluster count:** N
- **Architecture:** Standard / HCP / Mixed
- **Azure region(s):** eastus2
- **Total worker vCPUs:** X
- **Total control plane vCPUs:** X
- **Azure compute term:** PAYGO / 1yr RI / 3yr RI / savings plan
- **ARO license term:** PAYGO / 1yr / 3yr
- **Reservation scope:** shared / single-subscription / none
- **Reservation utilization:** X%
- **Reservation expiry:** YYYY-MM

## Cluster Details

| Cluster Name or ID | Architecture | Region | CP VM size | Worker pools | Worker vCPU | CP vCPU |
|---|---|---|---|---|---|---|

## Pricing Overrides

- `azure_discount:` X% _(omit if not set)_
- `license_rate:` $X per 4-vCPU block _(omit if not set)_

## Generated Reports

| Date | Report | File |
|---|---|---|
| YYYY-MM-DD | Cost Estimate | YYYY-MM-DD-cost-estimate.md |
```

After every command run: refresh the Fleet Profile with any new data and append a row to the Generated Reports table.

### Recalculation workflow — when cluster sizes change

Whenever vCPU counts are recalculated for a customer (new inventory pull, changed pools, corrected data), apply this sequence **before** touching any report file:

1. **Update `index.md` first** — revise the Fleet Profile and the Cluster Details table. This is the single source of truth for the fleet.
2. **Update every report in the customer directory** — each `.md` must reflect the new vCPU basis across per-cluster tables, fleet summaries and narrative. Control plane vCPU drives the entire Standard→HCP delta, so a stale control plane count invalidates the headline figure, not just a detail row.
3. **Note the change** — add a `Revised: YYYY-MM-DD` line to the report header and a short methodology note saying what changed.

Do not update a report until `index.md` reflects the new data, so reports cannot diverge from the customer profile.
