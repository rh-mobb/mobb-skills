# Share Button — ROSA Cost Explorer

**Date:** 2026-07-02

## Problem

The local cost-explorer HTML files contain per-cluster PII (cluster names, IDs). The public ROSA Fleet Optimizer at `https://cloud.redhat.com/experts/rosa/cost-explorer/` accepts an aggregated, PII-free share payload via a URL hash. We want a Share button in the local explorer that opens the public app pre-populated with the current lever state and baseline, so the customer can explore scenarios themselves.

## Decisions

- **Interaction:** Opens public URL in a new tab (not copy-to-clipboard). User can inspect the URL, copy from the address bar, or re-share from the public app's own share button.
- **Baseline:** Always encode the baseline config as `b` in the payload when it differs from current config, so the recipient sees the same before/after delta.
- **AZ topology:** Add `az: "single" | "multi"` to Classic cluster entries in CLUSTERS (HCP omits the field). Derived from `index.md`'s Fleet Profile at generation time.

## Changes

### 1. CLUSTERS schema — add `az` field

Add `"az": "single"` or `"az": "multi"` to every Classic cluster entry. HCP clusters omit the field.

```js
{ id:'...', name:'...', type:'classic', az:'multi', nodes:75, steady:1000, burst:200, inst:'r5_4xl', cat:'memory' }
```

The `rosa-cost` skill reads AZ topology from `index.md` Fleet Profile (`**AZ topology:** Multi-AZ...`) and emits `az` when generating the CLUSTERS JSON. Existing reports should be back-filled manually.

### 2. Baseline settings tracking

Add `baselineSettings` ref alongside `baselineSnapshot`. Updated in `setBaseline()`:

```js
const baselineSettings = ref(null);

function setBaseline() {
  baselineSnapshot.value = calcFleet(s);
  baselineSettings.value = { ...s };
}
```

`setBaseline()` is already called `onMounted`, so `baselineSettings` is always populated.

### 3. Payload aggregation — `buildShareCfg(settings)`

Converts local lever state + CLUSTERS into the public app config format.

```js
function buildShareCfg(settings) {
  const classic = CLUSTERS.filter(c => c.type === 'classic');
  const hcp     = CLUSTERS.filter(c => c.type === 'hcp');

  const sumSteady = (cat) =>
    CLUSTERS.filter(c => c.cat === cat).reduce((s, c) => s + c.steady, 0);

  const burstByCat = (cat) =>
    CLUSTERS.filter(c => c.cat === cat).reduce((s, c) => s + c.burst, 0);

  const totalBurst = CLUSTERS.reduce((s, c) => s + c.burst, 0);

  const burstProfile = (() => {
    if (!totalBurst) return 'general';
    const g = burstByCat('general'), m = burstByCat('memory'), c = burstByCat('compute');
    if (m >= g && m >= c) return 'memory';
    if (c >= g && c >= m) return 'compute';
    return 'general';
  })();

  const weightedRate = (cat, fallback) => {
    const clusters = CLUSTERS.filter(c => c.cat === cat);
    const totalVCPU = clusters.reduce((s, c) => s + c.steady, 0);
    if (!totalVCPU) return fallback;
    const totalCost = clusters.reduce((s, c) => s + c.steady * EC2[c.inst], 0);
    return parseFloat((totalCost / totalVCPU).toFixed(4));
  };

  const totalVCPU  = CLUSTERS.reduce((s, c) => s + c.steady, 0);
  const totalNodes = CLUSTERS.reduce((s, c) => s + c.nodes,  0);

  return {
    singleAZClusters: classic.filter(c => c.az === 'single').length,
    multiAZClusters:  classic.filter(c => c.az !== 'single').length,
    hcpClusters:      hcp.length,
    generalVCPU:      sumSteady('general'),
    memoryVCPU:       sumSteady('memory'),
    computeVCPU:      sumSteady('compute'),
    burstVCPU:        totalBurst,
    burstProfile,
    burstAwsDiscount: settings.burstEC2Discount,
    burstUsagePct:    settings.burstUtilPct,
    avgVCPUPerNode:   totalNodes > 0 ? Math.round(totalVCPU / totalNodes) : 8,
    rateGeneral:      weightedRate('general', 0.048),
    rateMemory:       weightedRate('memory',  0.063),
    rateCompute:      weightedRate('compute', 0.043),
    rosaContract:     settings.contractTerm,
    awsDiscountPct:   settings.ec2Discount,
    hcpMigrated:      settings.hcpMigrated,
    karpenter:        settings.karpenter,
    burstSpot:        settings.spotForBurst,
    armPct:           settings.armPct,
  };
}
```

Note: `hcpClusters` always uses the original count — the public app applies `hcpMigrated` itself.

### 4. Encoding — `openPublicApp()`

```js
const SHARE_PACK = {
  singleAZClusters:'sa', multiAZClusters:'ma', hcpClusters:'hc',
  generalVCPU:'gv', memoryVCPU:'mv', computeVCPU:'cv',
  burstVCPU:'bv', burstProfile:'bp', burstAwsDiscount:'bd',
  burstUsagePct:'bu', avgVCPUPerNode:'vn',
  rateGeneral:'rg', rateMemory:'rm', rateCompute:'rc',
  rosaContract:'rcn', awsDiscountPct:'ad',
  hcpMigrated:'hm', karpenter:'kp', burstSpot:'bs', armPct:'ap',
};
const SHARE_BOOLS = new Set(['burstAwsDiscount','hcpMigrated','karpenter','burstSpot']);

function packCfg(cfg) {
  const out = {};
  for (const [k, short] of Object.entries(SHARE_PACK)) {
    out[short] = SHARE_BOOLS.has(k) ? (cfg[k] ? 1 : 0) : cfg[k];
  }
  return out;
}

function openPublicApp() {
  const curr     = buildShareCfg(s);
  const baseline = buildShareCfg(baselineSettings.value);
  const packedC  = packCfg(curr);
  const packedB  = packCfg(baseline);

  const payload = { v: 1, c: packedC, s: s.syncEC2 ? 1 : 0 };
  if (JSON.stringify(packedB) !== JSON.stringify(packedC)) {
    payload.b = packedB;
  }

  const json    = JSON.stringify(payload);
  const encoded = btoa(unescape(encodeURIComponent(json)))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

  window.open(
    `https://cloud.redhat.com/experts/rosa/cost-explorer/#s=${encoded}`,
    '_blank'
  );
}
```

### 5. Share button — header

Added to the header bar, right-aligned after the meta line:

```html
<div class="header">
  <h1><span>__CUSTOMER_NAME__</span> — ROSA Cost Explorer</h1>
  <div class="header-meta">
    __CLUSTER_COUNT__ clusters &bull; __REGION__ &bull; ...
  </div>
  <button class="share-btn" @click="openPublicApp()">&#8599; Share</button>
</div>
```

```css
.share-btn {
  font-family: inherit;
  font-size: 0.78rem;
  font-weight: 600;
  color: #ccc;
  background: none;
  border: 1px solid #444;
  border-radius: 4px;
  padding: 0.3rem 0.75rem;
  cursor: pointer;
  white-space: nowrap;
}
.share-btn:hover { border-color: #aaa; color: white; }
```

## Files Changed

| File | Change |
|------|--------|
| `plugins/rosa/skills/rosa-cost/cost-explorer-template.html` | Add `az` to CLUSTERS comment, add `baselineSettings`, `buildShareCfg`, `packCfg`, `openPublicApp`, share button + CSS |
| `plugins/rosa/skills/rosa-cost/SKILL.md` | Instruct skill to emit `az` field when generating CLUSTERS JSON |
| `reports/*/cost-explorer.html` | Back-fill `az` field on existing Classic cluster entries |

## Out of Scope

- Back-filling the `s` (sync EC2) payload field dynamically — `s.syncEC2 ? 1 : 0` is passed directly from the local app's sync checkbox state
- Handling mixed-AZ fleets where individual clusters differ — per-cluster `az` field covers this
