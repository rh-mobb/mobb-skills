# Share Button — ROSA Cost Explorer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Share button to the local ROSA Cost Explorer HTML that opens the public ROSA Fleet Optimizer pre-populated with the current lever state and baseline comparison.

**Architecture:** All changes live inside self-contained HTML files (no build step). The template is the canonical source; existing rendered reports are updated separately. Share state is encoded as base64url JSON and passed via URL hash to the public app.

**Tech Stack:** Vanilla JS + Vue 3 (CDN), no bundler, no test framework — verification is browser console + manual inspection.

## Global Constraints

- Public app URL: `https://cloud.redhat.com/experts/rosa/cost-explorer/#s=<code>`
- Encoding: `btoa(unescape(encodeURIComponent(json)))` then `+`→`-`, `/`→`_`, strip trailing `=`
- Boolean fields in packed payload: `0` or `1`, never `true`/`false`
- CLUSTERS `az` field: `"single"` or `"multi"` on Classic clusters; HCP clusters omit it
- All 4 existing reports are multi-AZ — back-fill `az: "multi"` on all Classic entries
- `s` (sync EC2) payload field mirrors local `s.syncEC2` state, not hardcoded

---

### Task 1: CLUSTERS schema — add `az` field to template and SKILL.md

**Files:**
- Modify: `plugins/rosa/skills/rosa-cost/cost-explorer-template.html:474-479`
- Modify: `plugins/rosa/skills/rosa-cost/SKILL.md` (CLUSTERS generation instruction)

**Interfaces:**
- Produces: CLUSTERS entries with `az` field, consumed by `buildShareCfg` in Task 3

- [ ] **Step 1: Update CLUSTERS comment in template**

In `cost-explorer-template.html`, replace the existing CLUSTERS comment block (lines 474–479):

```js
// ── Fleet data ──────────────────────────────────────────────────────────────
// inst key must match a key in EC2 below.
// cat: 'memory' for R-family, 'general' for M/T-family.
// az:  'single' or 'multi' — Classic clusters only (omit for HCP).
// steady: autoscaling min vCPUs (fall back to total vCPU if unknown).
// burst: autoscaling max − min vCPUs (0 if no autoscaling data).
const CLUSTERS = __CLUSTERS_JSON__;
```

- [ ] **Step 2: Update SKILL.md — CLUSTERS generation instruction**

In `plugins/rosa/skills/rosa-cost/SKILL.md`, find the `### Live Mode — Cluster IDs` section. After the bullet list of fields to extract, add:

```markdown
- AZ topology per cluster — add `az: "single"` or `az: "multi"` to each Classic cluster entry.
  Read from `index.md` Fleet Profile (`**AZ topology:**` line). HCP clusters omit this field.
```

Also add to the `### Recalculation workflow` section, step 2 ("Update all reports"):

```markdown
  If a cost explorer HTML file exists, update its `CLUSTERS` JS array to match — including
  the `az` field on any Classic clusters.
```

- [ ] **Step 3: Commit**

```bash
git add plugins/rosa/skills/rosa-cost/cost-explorer-template.html \
        plugins/rosa/skills/rosa-cost/SKILL.md
git commit -m "feat(rosa-cost): add az field to CLUSTERS schema; update skill generation instructions"
```

---

### Task 2: Back-fill `az: "multi"` in all existing reports

**Files:**
- Modify: `reports/example/cost-explorer.html`
- Modify: `reports/red-truck-logistics/cost-explorer.html`
- Modify: `reports/suncorp/cost-explorer.html`
- Modify: `reports/cathay-pacific/cost-explorer.html`

All four reports are confirmed multi-AZ from their `index.md` files.

**Interfaces:**
- Produces: CLUSTERS entries with `az: "multi"` on Classic entries, consumed by `buildShareCfg` in Task 5

- [ ] **Step 1: Back-fill `reports/example/cost-explorer.html`**

The CLUSTERS array uses JSON format (pretty-printed). Add `"az": "multi"` to every object where `"type": "classic"`. Example — change:

```json
  {
    "id": "a3f4c2e1",
    "name": "prod-core-1",
    "type": "classic",
    "nodes": 75,
```

to:

```json
  {
    "id": "a3f4c2e1",
    "name": "prod-core-1",
    "type": "classic",
    "az": "multi",
    "nodes": 75,
```

Apply to all Classic entries. HCP entries (`"type": "hcp"`) do not get the `az` field.

- [ ] **Step 2: Back-fill `reports/red-truck-logistics/cost-explorer.html`**

The CLUSTERS array uses single-line JS object format. Add `az:'multi',` after `type:'classic',` on each Classic entry. Example — change:

```js
{ id:'rosa1-cp1', name:'rosa1-cp1', type:'classic', vCPU:1296, nodes:87, ...
```

to:

```js
{ id:'rosa1-cp1', name:'rosa1-cp1', type:'classic', az:'multi', vCPU:1296, nodes:87, ...
```

Apply to all Classic entries. Skip HCP entries.

- [ ] **Step 3: Back-fill `reports/suncorp/cost-explorer.html`**

JSON format. Add `"az": "multi"` after `"type": "classic"` on each Classic entry (all clusters in this report are Classic).

- [ ] **Step 4: Back-fill `reports/cathay-pacific/cost-explorer.html`**

Single-line format. Add `az:'multi',` after `type:'classic',` on each Classic entry. Skip HCP entries.

- [ ] **Step 5: Verify in browser**

Open each HTML file directly in a browser. Open the console and run:

```js
console.log(CLUSTERS.filter(c => c.type === 'classic').map(c => c.az));
// Expected: ["multi", "multi", ...] — all entries should be "multi", none undefined
console.log(CLUSTERS.filter(c => c.type === 'hcp').map(c => c.az));
// Expected: [undefined, undefined, ...] — HCP entries have no az field
```

- [ ] **Step 6: Commit**

```bash
git add reports/example/cost-explorer.html \
        reports/red-truck-logistics/cost-explorer.html \
        reports/suncorp/cost-explorer.html \
        reports/cathay-pacific/cost-explorer.html
git commit -m "feat(reports): back-fill az field on Classic clusters in all existing cost-explorer reports"
```

---

### Task 3: Baseline settings tracking — template

**Files:**
- Modify: `plugins/rosa/skills/rosa-cost/cost-explorer-template.html:596-600`

**Interfaces:**
- Produces: `baselineSettings` ref (plain object mirroring `s`), consumed by `openPublicApp` in Task 4

- [ ] **Step 1: Add `baselineSettings` ref and update `setBaseline`**

In `cost-explorer-template.html`, replace the existing baseline block (lines 596–600):

```js
    // Baseline: frozen snapshot, initialized on mount, updated by setBaseline()
    const baselineSnapshot = ref({ total: 0, rosaFee: 0, ec2Ebs: 0, overhead: 0, rows: null });
    function setBaseline() {
      baselineSnapshot.value = calcFleet(s);
    }
```

with:

```js
    // Baseline: frozen snapshot, initialized on mount, updated by setBaseline()
    const baselineSnapshot = ref({ total: 0, rosaFee: 0, ec2Ebs: 0, overhead: 0, rows: null });
    const baselineSettings = ref(null);
    function setBaseline() {
      baselineSnapshot.value = calcFleet(s);
      baselineSettings.value = { ...s };
    }
```

- [ ] **Step 2: Verify `baselineSettings` is always populated**

`setBaseline()` is called inside `onMounted()` (line 691), so `baselineSettings` will be non-null from page load. No null guard needed in `openPublicApp`.

- [ ] **Step 3: Commit**

```bash
git add plugins/rosa/skills/rosa-cost/cost-explorer-template.html
git commit -m "feat(rosa-cost): track baseline lever settings alongside baseline snapshot"
```

---

### Task 4: Share payload + encoding functions — template

**Files:**
- Modify: `plugins/rosa/skills/rosa-cost/cost-explorer-template.html`

Add three functions after the `calcFleet` function (around line 555) and before the `createApp` block. Also update the `return {}` at the end of `setup()`.

**Interfaces:**
- Consumes: `CLUSTERS`, `EC2`, `s` (reactive), `baselineSettings` (ref) from Task 3
- Produces: `openPublicApp()` function exposed on Vue app instance

- [ ] **Step 1: Add `buildShareCfg`, `packCfg`, `openPublicApp` to template**

In `cost-explorer-template.html`, insert the following block immediately before the `// ── Vue app` comment line (line 557):

```js
// ── Share link ───────────────────────────────────────────────────────────────
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
    const g = burstByCat('general'), m = burstByCat('memory'), co = burstByCat('compute');
    if (m >= g && m >= co) return 'memory';
    if (co >= g && co >= m) return 'compute';
    return 'general';
  })();

  const weightedRate = (cat, fallback) => {
    const cs = CLUSTERS.filter(c => c.cat === cat);
    const totalVCPU = cs.reduce((s, c) => s + c.steady, 0);
    if (!totalVCPU) return fallback;
    return parseFloat((cs.reduce((s, c) => s + c.steady * EC2[c.inst], 0) / totalVCPU).toFixed(4));
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

function packCfg(cfg) {
  const out = {};
  for (const [k, short] of Object.entries(SHARE_PACK)) {
    out[short] = SHARE_BOOLS.has(k) ? (cfg[k] ? 1 : 0) : cfg[k];
  }
  return out;
}
```

- [ ] **Step 2: Add `openPublicApp` inside the Vue `setup()` function**

Inside the `setup()` function, add `openPublicApp` just before the `return {}` statement (line 702):

```js
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

- [ ] **Step 3: Expose `openPublicApp` in the `return {}` statement**

Change the existing `return` at line 702 from:

```js
    return { s, hasHCP, fleet, baselineSnapshot, leverSavings, delta, deltaPct, chartEl, fmt, fmtK, setBaseline };
```

to:

```js
    return { s, hasHCP, fleet, baselineSnapshot, leverSavings, delta, deltaPct, chartEl, fmt, fmtK, setBaseline, openPublicApp };
```

- [ ] **Step 4: Verify encoding in browser console**

Open the template (or any report) in a browser. Open the console and paste:

```js
// Verify buildShareCfg returns expected shape
const cfg = buildShareCfg({ contractTerm: '1yr', ec2Discount: 40, syncEC2: true,
  hcpMigrated: false, karpenter: false, armPct: 0,
  spotForBurst: false, burstUtilPct: 20, burstEC2Discount: false });
console.assert(typeof cfg.generalVCPU === 'number', 'generalVCPU must be a number');
console.assert(typeof cfg.memoryVCPU === 'number', 'memoryVCPU must be a number');
console.assert(['general','memory','compute'].includes(cfg.burstProfile), 'burstProfile must be valid');
console.assert(cfg.rosaContract === '1yr', 'rosaContract must match');

// Verify packCfg produces short keys
const packed = packCfg(cfg);
console.assert('sa' in packed, 'packed must have sa');
console.assert('gv' in packed, 'packed must have gv');
console.assert(packed.hm === 0, 'hcpMigrated bool must be 0');

// Verify encoding produces a non-empty string without +, /, or =
const json = JSON.stringify({ v:1, c:packed, s:1 });
const encoded = btoa(unescape(encodeURIComponent(json))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
console.assert(encoded.length > 0, 'encoded must be non-empty');
console.assert(!encoded.includes('+') && !encoded.includes('/') && !encoded.includes('='), 'must be URL-safe');
console.log('All assertions passed. URL:', `https://cloud.redhat.com/experts/rosa/cost-explorer/#s=${encoded}`);
```

Expected: "All assertions passed." followed by a URL.

- [ ] **Step 5: Commit**

```bash
git add plugins/rosa/skills/rosa-cost/cost-explorer-template.html
git commit -m "feat(rosa-cost): add share payload encoding functions to template"
```

---

### Task 5: Share button CSS + HTML — template

**Files:**
- Modify: `plugins/rosa/skills/rosa-cost/cost-explorer-template.html:13-212` (CSS block)
- Modify: `plugins/rosa/skills/rosa-cost/cost-explorer-template.html:216-221` (header HTML)

**Interfaces:**
- Consumes: `openPublicApp()` from Task 4

- [ ] **Step 1: Add `.share-btn` CSS**

In `cost-explorer-template.html`, add the following inside the `<style>` block, after the `.header-meta` rule (around line 34):

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
      flex-shrink: 0;
    }
    .share-btn:hover { border-color: #aaa; color: white; }
```

- [ ] **Step 2: Add share button to header HTML**

In `cost-explorer-template.html`, find the header div (lines 216–221):

```html
  <div class="header">
    <h1><span>__CUSTOMER_NAME__</span> — ROSA Cost Explorer</h1>
    <div class="header-meta">
      __CLUSTER_COUNT__ clusters &bull; __REGION__ &bull; EC2 from AWS Pricing API __EC2_API_DATE__ &bull; ROSA fees __ROSA_FEES_DATE__
    </div>
  </div>
```

Replace with:

```html
  <div class="header">
    <h1><span>__CUSTOMER_NAME__</span> — ROSA Cost Explorer</h1>
    <div class="header-meta">
      __CLUSTER_COUNT__ clusters &bull; __REGION__ &bull; EC2 from AWS Pricing API __EC2_API_DATE__ &bull; ROSA fees __ROSA_FEES_DATE__
    </div>
    <button class="share-btn" @click="openPublicApp()">&#8599; Share</button>
  </div>
```

- [ ] **Step 3: Verify in browser**

Open the template in a browser (it will show `__CUSTOMER_NAME__` literally — that's fine for layout verification). Confirm:
- The Share button appears in the top-right of the dark header bar
- Hovering lightens the border and text to white
- (Cannot click yet in the raw template since `openPublicApp` references `CLUSTERS` / `EC2` which are placeholder strings — test clicking in a real report after Task 6)

- [ ] **Step 4: Commit**

```bash
git add plugins/rosa/skills/rosa-cost/cost-explorer-template.html
git commit -m "feat(rosa-cost): add Share button to cost-explorer template header"
```

---

### Task 6: Propagate JS + UI changes to all existing reports

**Files:**
- Modify: `reports/example/cost-explorer.html`
- Modify: `reports/red-truck-logistics/cost-explorer.html`
- Modify: `reports/suncorp/cost-explorer.html`
- Modify: `reports/cathay-pacific/cost-explorer.html`

Each report needs: `baselineSettings` ref, updated `setBaseline()`, `SHARE_PACK`/`SHARE_BOOLS`/`buildShareCfg`/`packCfg` module-level functions, `openPublicApp` inside `setup()`, updated `return {}`, `.share-btn` CSS, and the share button in the header HTML.

Apply the same edits from Tasks 3–5 to each report. The changes are identical across all four reports — the only report-specific content (`CLUSTERS`, `EC2`, `CLASSIC_OH`) is untouched.

- [ ] **Step 1: Update `reports/example/cost-explorer.html`**

  - **CSS**: Add `.share-btn` and `.share-btn:hover` rules inside `<style>`, after `.header-meta` rule
  - **Header HTML**: Add `<button class="share-btn" @click="openPublicApp()">&#8599; Share</button>` as last child of `.header` div
  - **Module-level JS**: Add `SHARE_PACK`, `SHARE_BOOLS`, `buildShareCfg`, `packCfg` block immediately before the `// ── Vue app` comment
  - **`baselineSnapshot` block**: Replace with version that includes `baselineSettings`:
    ```js
    const baselineSnapshot = ref({ total: 0, rosaFee: 0, ec2Ebs: 0, overhead: 0, rows: null });
    const baselineSettings = ref(null);
    function setBaseline() {
      baselineSnapshot.value = calcFleet(s);
      baselineSettings.value = { ...s };
    }
    ```
  - **`openPublicApp`**: Add inside `setup()` before the `return {}` statement (same code as Task 4 Step 2)
  - **`return {}`**: Add `openPublicApp` to the returned object

- [ ] **Step 2: Update `reports/red-truck-logistics/cost-explorer.html`**

  Apply the same five edits as Step 1.

- [ ] **Step 3: Update `reports/suncorp/cost-explorer.html`**

  Apply the same five edits as Step 1.

- [ ] **Step 4: Update `reports/cathay-pacific/cost-explorer.html`**

  Apply the same five edits as Step 1.

  Note: cathay-pacific uses `c.oh ?? CLASSIC_OH` per cluster for overhead — this does not affect `buildShareCfg` which reads only `c.type`, `c.az`, `c.cat`, `c.steady`, `c.burst`, `c.nodes`, `c.inst`.

- [ ] **Step 5: End-to-end test in browser**

Open `reports/example/cost-explorer.html` in a browser. Verify:

1. Share button is visible in the header top-right
2. Hover shows border/text lighten to white
3. Click opens a new tab to `https://cloud.redhat.com/experts/rosa/cost-explorer/#s=...`
4. Inspect the URL hash — it should start with `#s=` followed by a base64url string (no `+`, `/`, or `=`)
5. In the public app, verify the vCPU counts and lever settings match what was set locally
6. Set levers in the local app (e.g., enable HCP Migration), click Share again — verify the new tab shows the updated configuration
7. Click "Set current as baseline" in the local app, then change levers, then click Share — verify the public app shows the before/after delta (baseline bar vs configured bar differ)

- [ ] **Step 6: Commit**

```bash
git add reports/example/cost-explorer.html \
        reports/red-truck-logistics/cost-explorer.html \
        reports/suncorp/cost-explorer.html \
        reports/cathay-pacific/cost-explorer.html
git commit -m "feat(reports): add Share button to all existing cost-explorer reports"
```
