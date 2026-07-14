# ROSA CLI Commands — Design Spec

**Date:** 2026-07-14
**Author:** Paul Czarkowski

---

## Context

The `rosa` plugin currently contains cost-focused commands and skills. ROSA customers typically have the `rosa` CLI available but not the `ocm` CLI. The `ocm` plugin has four commands (`cluster-describe`, `cluster-owner`, `org-clusters`, `whoami`) that are only usable by Red Hat employees with cross-account access.

This spec adds three ROSA-native equivalents — covering the subset that works without cross-account privileges. `cluster-owner` is intentionally excluded: it requires cross-account OCM API calls that the `rosa` CLI cannot perform.

---

## Commands

### `rosa:cluster-describe <cluster-name-or-id>`

Comprehensive description of a single ROSA cluster using only the `rosa` CLI.

**Implementation steps:**

1. **Auth** — follow profile resolution from the `rosa-cli` skill (`OCM_CONFIG` env var for profile switching).
2. **Base describe** — `rosa describe cluster <cluster> --output json`; extract name, ID, state, version, region, cloud provider, network type. Detect Classic vs HCP from the `hypershift.enabled` field (or equivalent rosa output).
3. **Pools**
   - Classic: `rosa list machinepools --cluster <cluster> --output json`
   - HCP: `rosa list nodepools --cluster <cluster> --output json`
4. **Identity Providers** — `rosa list idps --cluster <cluster>`
5. **Ingresses** — `rosa list ingresses --cluster <cluster>`
6. **Upgrades**
   - Classic: `rosa list upgrade-policies --cluster <cluster>`
   - HCP: `rosa list upgrades --cluster <cluster>`
7. **Present** — structured summary with a header block (metadata) followed by labelled sections for each resource type. If a section returns no results, show "None" rather than omitting it.

**Frontmatter:**
```yaml
description: Describe a ROSA cluster in detail — metadata, machine/node pools, IDPs, ingresses, and upgrade policies.
argument-hint: <cluster-name-or-id>
```

---

### `rosa:list-clusters`

Lists all ROSA clusters accessible to the logged-in user.

**Implementation steps:**

1. **Auth** — follow profile resolution from the `rosa-cli` skill.
2. **List** — `rosa list clusters --output json`
3. **Present** — tabular output with columns: Name, ID, State, Version, Region, Type (Classic / HCP). Sort by Name. If no clusters are found, say so explicitly.

**Frontmatter:**
```yaml
description: List all ROSA clusters for the logged-in user.
argument-hint: ""
```

---

### `rosa:whoami`

Displays the identity of the currently authenticated user.

**Implementation steps:**

1. **Auth** — follow profile resolution from the `rosa-cli` skill.
2. **Run** — `rosa whoami`
3. **Present** — pass through `rosa whoami` output as-is; it is already human-readable.

**Frontmatter:**
```yaml
description: Show the currently authenticated ROSA user and account details.
argument-hint: ""
```

---

## Placement

All three files go in `plugins/rosa/commands/`:

```
plugins/rosa/commands/
├── cluster-describe.md   ← new
├── cost-compare.md
├── cost-estimate.md
├── cost-optimize.md
├── cost-report.md
├── cost.md
├── list-clusters.md      ← new
└── whoami.md             ← new
```

---

## Skill Dependency

All three commands reference the `rosa-cli` skill for auth/profile setup. No new skills are needed.

---

## Out of Scope

- `rosa:cluster-owner` — requires cross-account OCM API access; not possible with the `rosa` CLI alone.
- Any command that requires AWS credentials beyond what `rosa login` establishes.
- OSD, ARO, or self-managed OCP clusters — the `rosa` CLI only covers ROSA.
