# ARO Cost Report — Example Corp

**Date:** 2026-10-20
**Command:** /aro:cost-report
**Basis:** 3-year Azure reserved instances on compute (0.38×), OpenShift license at the customer's 3-year committed rate
**Rates:** current as of 2026-10 — verify at https://azure.microsoft.com/en-us/pricing/details/openshift/ before quoting
**Scope:** 15 active Azure Red Hat OpenShift clusters

---

> ### Basis and limitations
>
> This analysis uses the supplied cluster inventory, publicly available pricing and product information, and modeling assumptions. The figures have not been reconciled to Example Corp's Azure billing records, negotiated discounts, reservation coverage, or OpenShift subscription terms. Example Corp should confirm the actual resource configurations, effective costs, remaining commitments, and applicable HCP pricing with its Microsoft and Red Hat account teams before using these estimates for budgeting or migration decisions. Savings represent potential ongoing cost reductions; their amount and timing depend on contract terms and implementation. Migration costs and temporary parallel operation are excluded.

---

## Executive summary

Example Corp runs 15 active ARO clusters on Standard architecture, totaling **2,340 provisioned vCPU** per the supplied inventory. Of that, **732 vCPU (31%) is control plane**, which runs no application workload.

Migrating to ARO with hosted control planes would remove the customer-managed control plane, replacing three control plane VMs per cluster with a cluster management fee of $182.50 per cluster per month.

> ### Modeled saving: approximately **$13,100/month, or $157,000/year**
> in the modeled 3-year reserved compute scenario, conditional on the assumptions below

The modeled saving is larger at lower compute commitment, because a reservation reduces the cost of the control plane being removed:

| Azure compute scenario | Monthly | Annual |
|---|---|---|
| Pay-as-you-go | ~$29,000 | ~$348,000 |
| 3-year reserved (modeled) | ~$13,100 | ~$157,000 |

Two qualifications belong alongside that figure:

1. **Modeled savings are not the same as reduced payments.** Removing control plane VMs does not by itself release an existing Azure reservation commitment.
2. **Migration costs are excluded**, including project effort and any period of parallel operation.

OpenShift licensing is not a qualification: ARO subscriptions transfer from Standard to HCP, confirmed with the ARO product management team, so the license applies at the same rate on both architectures and cancels out of the comparison.

---

## Fleet inventory

As supplied. Every cluster reports zero infrastructure nodes.

| Cluster | Version | Master | Compute | Worker vCPU | Total vCPU | CP vCPU |
|---|---|---|---|---|---|---|
| ocp-dev-01 | 4.21.28 | 3 | 8 | 40 | 100 | 60 |
| ocp-prd-01 | 4.18.48 | 3 | 37 | 272 | 320 | 48 |
| ocp-prd-02 | 4.19.30 | 3 | 14 | 88 | 136 | 48 |
| ocp-prd-03 | 4.21.25 | 3 | 4 | 64 | 88 | 24 |
| ocp-prd-04 | 4.20.15 | 3 | 11 | 64 | 112 | 48 |
| ocp-prd-05 | 4.21.27 | 3 | 11 | 64 | 112 | 48 |
| ocp-tst-01 | 4.18.48 | 3 | 45 | 336 | 408 | 72 |
| ocp-tst-02 | 4.20.32 | 3 | 18 | 120 | 168 | 48 |
| ocp-tst-03 | 4.20.32 | 3 | 8 | 64 | 88 | 24 |
| ocp-tst-04 | 4.18.48 | 3 | 27 | 192 | 240 | 48 |
| ocp-tst-05 | 4.21.21 | 3 | 12 | 72 | 120 | 48 |
| ocp-tst-06 | 4.21.24 | 3 | 11 | 64 | 112 | 48 |
| ocp-tst-07 | 4.19.30 | 3 | 12 | 72 | 144 | 72 |
| ocp-tst-08 | 4.19.30 | 3 | 7 | 32 | 80 | 48 |
| ocp-tst-09 | 4.21.21 | 3 | 11 | 64 | 112 | 48 |
| **Total** | | **45** | **236** | **1,608** | **2,340** | **732** |

Nine further subscriptions are Archived or Stale and are excluded from all figures.

| Prefix | Environment | Clusters | Worker vCPU | Share |
|---|---|---|---|---|
| ocp-dev | Development | 1 | 40 | 2.5% |
| ocp-prd | Production | 5 | 552 | 34.3% |
| ocp-tst | Test | 9 | 1,016 | 63.2% |

**Non-production (development and test) totals 10 clusters and 1,056 worker vCPU, 65.7% of the fleet.**

---

## Modeled cost comparison

Azure compute at a 3-year reserved instance multiplier of 0.38×. OpenShift license modeled at Example Corp's 3-year committed rate, which applies on both architectures. Reserved instances cover VM compute only, not managed disks.

| | Standard | HCP | Delta/month | Delta/year |
|---|---|---|---|---|
| OpenShift license (402 × 4-vCPU blocks) | $22,343 | $22,343 | $0 | $0 |
| Worker VMs (1,608 vCPU) | $21,411 | $21,411 | $0 | $0 |
| **Control plane VMs (732 vCPU)** | **$9,747** | **$0** | **$9,747** | **$116,964** |
| **Control plane disks (45 × Premium SSD)** | **$6,083** | **$0** | **$6,083** | **$72,996** |
| Cluster management fee (15 × $182.50) | $0 | $2,738 | ($2,738) | ($32,850) |
| **Modeled cost subtotal** | **$59,584** | **$46,492** | **$13,092** | **$157,104** |

This is a **subtotal of the modeled line items only**, not total platform spend. It excludes worker node disks, application and persistent storage, networking and egress, load balancers, backup, logging and monitoring data costs, and any Azure services consumed by the applications. Those costs are broadly unchanged by the architecture decision, which is why they are omitted, but the subtotal should not be read as Example Corp's ARO bill.

### OpenShift licensing

ARO subscriptions transfer from ARO Standard to ARO HCP, confirmed with the ARO product management team. The license is charged per worker vCPU on both architectures, so the modeled license cost is identical on both sides of the comparison. It cancels out and does not contribute to the $13,092 figure.

Example Corp should still confirm its effective rate and remaining commitment terms with its Microsoft and Red Hat account teams as part of normal migration planning.

### Modeled savings versus reduced payments

Removing control plane VMs reduces modeled consumption, but does not automatically reduce what Example Corp pays:

- **Azure reservations are a commitment, not a per-resource discount.** Deleting the VMs a reservation was sized for does not cancel the commitment. Azure may apply the benefit to other matching resources within the reservation's scope; where no matching resource exists, those reserved hours go unused. Example Corp should establish whether freed reservation capacity can be absorbed elsewhere, and what the reservation expiry dates are.
- **The same applies to licensing.** Reducing licensed worker vCPU may lower future requirements without immediately reducing prepaid or committed license costs.

The practical consequence is that **the timing of any realized saving depends on reservation scope, utilization and expiry**, not only on when clusters are migrated.

### Control plane disks

Modeled at 1,024 GiB Premium SSD LRS per control plane node, approximately $135 per disk per month, 45 disks.

Microsoft's ARO service definition documents 1,024 GiB Premium SSD LRS disks for Standard architecture control plane nodes, which is the basis for this figure. A reference cluster was observed using `Premium_LRS`, consistent with that.

This line is approximately **38% of the gross control plane saving** ($15,830/month) and 46% of the net after the management fee. It is significant partly because **reserved instances do not cover managed disks**: when compute is reserved, VM cost falls while disk cost does not, so disks become a larger proportion of the saving.

Example Corp should reconcile disk configurations and actual charges across all 15 clusters. Inspecting one cluster does not validate the fleet, and clusters built at different times or versions may differ.

### Modeled saving by cluster

Each figure is control plane VMs plus three control plane disks, less the cluster management fee.

| Cluster | CP vCPU | Modeled saving/month |
|---|---|---|
| ocp-tst-01, ocp-tst-07 | 72 | ~$1,182 each |
| ocp-dev-01 | 60 | ~$1,022 |
| ocp-prd-01, prd-02, prd-04, prd-05, tst-02, tst-04, tst-05, tst-06, tst-08, tst-09 | 48 | ~$862 each |
| ocp-prd-03, ocp-tst-03 | 24 | ~$543 each |

Control plane vCPU varies across the fleet, from 24 to 72 per cluster. Red Hat SRE sizes and operates these control planes, and the inventory carries no control plane utilization data, so this analysis draws no conclusion about how any given cluster is sized. The relevance here is purely financial: the larger the control plane, the more cost HCP removes, whatever the sizing reflects.

---

## Karpenter node auto-provisioning — separate, conditional opportunity

Karpenter node auto-provisioning is anticipated for ARO with hosted control planes in **early 2027, subject to confirmation**, and is understood to be **HCP-only, also subject to confirmation**. Both the timing and the architecture restriction should be verified against an approved Red Hat roadmap source before being presented to Example Corp.

This is **not** included in the savings headline. It is a separate opportunity that depends on availability, applicability to Example Corp's workloads, and successful implementation.

### Illustrative worker-capacity reduction scenarios

Karpenter provisions nodes from workload requirements rather than fixed machine sets, and consolidates under-utilized nodes. Where that reduces provisioned worker capacity, it reduces both the Azure VM cost and the OpenShift license, since the license is charged per worker vCPU.

The percentages below are **reductions in provisioned worker vCPU**, applied to the modeled worker VM and license lines:

| Reduction in provisioned worker vCPU | Monthly | **Annual** |
|---|---|---|
| 10% | ~$4,375 | ~$52,500 |
| 20% | ~$8,751 | ~$105,000 |
| 30% | ~$13,126 | ~$157,500 |
| 40% | ~$17,502 | ~$210,000 |

**These overlap with the right-sizing opportunity below and should not be added to it.** Capacity recovered by right-sizing today is capacity Karpenter cannot recover again later. Treat them as alternative routes to the same reduction, with Karpenter automating what would otherwise be manual and ongoing.

If both the migration saving and a capacity reduction were realized, the combined effect at a 30% reduction would be in the order of $314,000 per year. That figure is deliberately kept out of the headline: it depends on two independent conditions, neither yet established.

### Establishing a realistic reduction

The achievable reduction depends on Example Corp's actual resource requests versus usage, which the supplied inventory does not show.

Measuring on two or three representative clusters would **produce a better-supported estimate**, and can be done on Standard before any migration. That assessment should consider **memory as well as CPU**, together with scheduling constraints, anti-affinity and availability requirements, workload peaks, and any node-level requirements such as taints or specialized hardware. Reductions achievable on paper from CPU requests alone frequently do not survive those constraints.

---

## Observations

**1. Non-production dominates the footprint.** Ten development and test clusters hold 1,056 worker vCPU, 65.7% of the fleet. `ocp-tst-01` at 336 worker vCPU and 45 compute nodes is the largest cluster in the inventory, larger than any production cluster; `ocp-tst-04` at 192 vCPU is third largest. Reviewing non-production sizing requires no architecture change.

**2. Per-cluster saving tracks control plane vCPU**, which ranges from 24 to 72 across the fleet. Clusters at the upper end return the most on migration, because there is simply more control plane cost to eliminate. See the per-cluster table.

**3. Version spread is wide**, 4.18.48 through 4.21.28. Three clusters are on 4.18 and will need upgrading regardless. Version age is one input to migration sequencing, but **workload risk, application compatibility and business criticality should carry more weight** than version alone.

**4. Node sizing affects license efficiency.** The license is charged on every provisioned worker vCPU, including capacity each node reserves for the kubelet and operating system. That reservation is broadly fixed per node, so a given total spread across fewer, larger nodes leaves more capacity available for workloads. Quantifying the effect for Example Corp requires measured node allocatable figures.

---

## Recommendations

🟢 **Available now, no migration required**

1. **Review non-production sizing.** 65.7% of worker vCPU is development and test. `ocp-tst-01` and `ocp-tst-04` are the largest opportunities.
2. **Review worker node sizing** where workload shape allows consolidation onto fewer, larger nodes.
3. **Measure capacity headroom** on two or three representative clusters, covering CPU, memory, scheduling constraints and peaks.

🟡 **Validation**

4. **Confirm the effective OpenShift license rate and remaining commitment terms** with the Microsoft and Red Hat account teams. Subscription transfer to HCP is already confirmed; what remains is reconciling Example Corp's actual rate against the modeled one.
5. **Confirm reservation scope, utilization and expiry**, and whether capacity freed by migration can be applied elsewhere.
6. **Reconcile disk configuration and actual charges** across all 15 clusters.
7. **Confirm ARO HCP regional availability and current service status** for Example Corp's regions.

🔴 **Subject to validation**

8. **Consider migration to ARO HCP**, modeled at approximately $157,000 per year in the 3-year reserved scenario. HCP requires a cluster rebuild rather than an in-place conversion, and the identity model moves to managed identity only. Sequencing should weigh workload risk and application compatibility alongside version age. A migration plan should include project effort, any period of parallel operation, and the reservation and licensing questions above before first-year savings or payback are quoted.
9. **Track Karpenter availability** for ARO HCP, and revisit the capacity-reduction opportunity once timing and applicability are confirmed.

---

## Qualitative considerations

These apply independently of the cost estimate.

| Feature | Standard | HCP |
|---|---|---|
| Control plane management | Customer subscription | Hosted |
| Control plane fault domain | Shares customer subscription | Isolated |
| Cluster provisioning time | Longer | Shorter |
| Identity model | Service principal or managed identity | Managed identity only |
| Subscription vCPU quota | 732 vCPU consumed by control plane | Not consumed |
| Cost predictability | Varies with control plane size | Flat per-cluster fee |

The quota point is concrete: migration would return **732 vCPU of subscription quota** currently allocated to control planes, subject to confirmation of Example Corp's quota position.

---

## Assumptions

Every figure in this document rests on one or more of the following. None has been reconciled to Example Corp's billing records.

| Assumption | Basis | Validation needed |
|---|---|---|
| Azure compute $0.048/vCPU/hr, 730 hrs/month | Public East US general purpose list rate | Actual region and negotiated rate |
| 3-year reserved multiplier 0.38× | Typical planning figure | Example Corp's reservation terms and coverage |
| Control plane disks 1,024 GiB Premium SSD LRS | Microsoft ARO service definition | Per-cluster disk inventory and charges |
| VM sizes derived from reported vCPU totals | Supplied inventory | Actual SKUs per cluster |
| OpenShift license charged at Example Corp's 3-year committed rate | Supplied rate; subscription transfer to HCP confirmed with ARO product management | Effective rate and remaining commitment term |
| HCP cluster management fee $0.25/cluster/hr | Public information | Current HCP pricing at general availability |
| Memory-optimized workers priced as general purpose | Simplification | Actual worker SKU mix; E-series is ~31% higher |

---

## Information required to firm up this estimate

To convert this into a defensible business case, the following from Example Corp would be needed:

1. Azure **actual and amortized cost exports** for the relevant subscriptions, covering a representative period
2. **VM and disk inventory by cluster and region**, including SKUs and disk sizes
3. **Reservation utilization and expiration dates**, with scope
4. **Example Corp's effective OpenShift license rate and remaining commitment term**, from the Microsoft and Red Hat account teams
5. **Resource request versus usage data** from two or three representative clusters, covering CPU and memory
6. Any **migration constraints** such as change windows, compliance requirements or application dependencies
