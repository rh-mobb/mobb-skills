# ARO Plugin

Azure Red Hat OpenShift (ARO) cost estimation, comparison, and optimization, covering both Standard architecture and ARO with hosted control planes (HCP).

## Commands

| Command | Purpose |
|---------|---------|
| `/aro:cost` | Guided wizard. Collects fleet data and routes to the right analysis |
| `/aro:cost-estimate` | Monthly and annual cost for a fleet at its current configuration |
| `/aro:cost-compare` | Standard vs HCP side-by-side with a savings delta |
| `/aro:cost-optimize` | Ranked savings opportunities by implementation effort |
| `/aro:cost-report` | Full strategic advisory report with a phased migration plan |

## What makes ARO costing different from ROSA

This plugin deliberately does not reuse ROSA cost logic. The differences that matter:

- **Control plane VMs and their disks are customer-billed on Standard.** Removing them is the entire Standard→HCP saving, roughly **$1,060/cluster/month** at default sizing and pay-as-you-go compute, offset by the $182.50/month cluster management fee. Control plane disks (~$405/month) are ~38% of that net saving, and are not covered by compute reservations, so their share grows on reserved compute.
- **No infrastructure nodes are deployed by default**, unlike ROSA Classic where they are mandatory. There is no infra-node line item to eliminate.
- **No ARM/Graviton VM sizes** are supported, so the ARM price-performance lever does not exist.
- **No Karpenter today**, and **scale-to-zero is unsupported**. Deallocating cluster VMs voids support. Karpenter/AutoNode is in active development for ARO HCP (`Azure/ARO-HCP` #7542, `openshift/hypershift` #9545) and will be HCP-only, which the skill treats as a sequencing argument for migration rather than a quotable saving.
- **ARO subscriptions transfer from Standard to HCP** (confirmed with ARO product management, 2026-10), so the license applies at the same rate on both architectures and cancels out of the migration delta. Do not model it as a forfeited benefit.
- **Outputs are preliminary estimates, not billing reconciliations.** The skill requires a basis-and-limitations block, modeled-versus-actual language, and an explicit distinction between a modeled saving and a reduction in what the customer actually pays.

The plugin encodes these so recommendations carried over from ROSA engagements are not applied incorrectly.

## Pricing basis

- OpenShift license: **$0.171/hr per 4 worker vCPUs**, flat regardless of VM series or size. Control plane nodes are never charged a license fee.
- HCP cluster management fee: **$0.25/cluster/hr** ($182.50/month), not discounted by any reservation.
- Azure VM and disk costs are billed separately at standard Linux VM pricing.

Rates are current as of 2026-10. The skill confirms live VM rates through the Azure Retail Prices API, which needs no authentication.

Source: https://azure.microsoft.com/en-us/pricing/details/openshift/

## Skills

| Skill | Scope |
|---|---|
| `skills/aro-cost/SKILL.md` | Cost reference, calculation formula, constraints, output templates, file output conventions, and a self-improving registry for confirmed pricing and engagement lessons |

Append to the registry and engagement-lesson sections after each engagement.
