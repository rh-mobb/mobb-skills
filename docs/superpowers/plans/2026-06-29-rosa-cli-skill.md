# ROSA CLI Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `plugins/rosa/skills/rosa-cli/` containing a self-contained SKILL.md covering every `rosa` CLI subcommand with Classic/HCP parallel lifecycle sequences and a full command reference.

**Architecture:** Two new files — `SKILL.md` (AI guidance content) and `AGENTS.md` (developer reference for the upstream clone) — plus a version bump to `plugin.json`. The SKILL.md content is fully specified in the design spec at `docs/superpowers/specs/2026-06-29-rosa-cli-skill-design.md`. The implementer's job is faithful transcription and formatting, not design decisions.

**Tech Stack:** Markdown, YAML frontmatter. Validation via `make lint` (skillsaw in Docker/Podman) and `make update`.

## Global Constraints

- Skill directory: `plugins/rosa/skills/rosa-cli/`
- SKILL.md frontmatter `name:` must be `rosa-cli`
- SKILL.md frontmatter `user_invocable:` must be `false`
- SKILL.md frontmatter `color:` must be `"#cc0000"` (matches plugin brand)
- SKILL.md frontmatter `allowed-tools:` must be `[]`
- SKILL.md frontmatter `license:` must be `Apache-2.0`
- `plugin.json` version bump: `0.3.1` → `0.4.0`
- `make lint` must pass before any commit
- No cross-references to the ocm-cli skill in SKILL.md content
- Content source of truth: `docs/superpowers/specs/2026-06-29-rosa-cli-skill-design.md` — read this file before writing any SKILL.md content

---

### Task 1: Scaffold — AGENTS.md and plugin.json version bump

**Files:**
- Create: `plugins/rosa/skills/rosa-cli/AGENTS.md`
- Modify: `plugins/rosa/.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: nothing (first task)
- Produces: `plugins/rosa/skills/rosa-cli/` directory containing `AGENTS.md`; `plugin.json` at version `0.4.0`

- [ ] **Step 1: Read the spec Implementation Notes section**

  Read `docs/superpowers/specs/2026-06-29-rosa-cli-skill-design.md` and locate the "Implementation Notes" section near the bottom. It contains the exact content for AGENTS.md.

- [ ] **Step 2: Create `plugins/rosa/skills/rosa-cli/AGENTS.md`**

  Write the following content exactly:

  ```markdown
  # rosa-cli Skill — Developer Reference

  This skill was built from the ROSA CLI source. For major updates (new subcommands, API changes, flag changes), clone the reference first:

  ```bash
  git clone https://github.com/openshift/rosa references/rosa-cli
  ```

  The reference is gitignored. Do not commit it.

  ## When to load the reference

  - Adding coverage for a new `rosa` subcommand
  - Reconciling the skill against a new ROSA CLI release
  - Verifying exact flag names or output formats before updating SKILL.md

  ## Key paths in the reference

  | Path | What to find there |
  |---|---|
  | `cmd/` | All subcommands — one directory per command group |
  | `cmd/create/cluster/cmd.go` | Cluster creation flags (most complex command) |
  | `cmd/create/machinepool/` | Machine pool / node pool flags |
  | `cmd/login/cmd.go` | Login flow and token auth |
  | `CHANGELOG.md` | Release history — scan this first for new versions |
  | `pkg/arguments/` | Common flag definitions shared across commands |

  ## Checking the installed version

  ```bash
  rosa version
  ```

  Compare against https://github.com/openshift/rosa/releases to determine whether the skill needs reconciliation.
  ```

- [ ] **Step 3: Bump plugin.json version**

  Read `plugins/rosa/.claude-plugin/plugin.json`. Change `"version": "0.3.1"` to `"version": "0.4.0"`. The rest of the file is unchanged:

  ```json
  {
    "name": "rosa",
    "description": "ROSA cost estimation, comparison, and optimization for Classic and HCP clusters.",
    "version": "0.4.0",
    "author": {
      "name": "github.com/rh-mobb"
    }
  }
  ```

- [ ] **Step 4: Verify with make lint**

  Run: `make lint`

  Expected: PASS (lint validates plugin structure; it may warn about missing SKILL.md but must not error on existing files).

  If lint fails because `plugins/rosa/skills/rosa-cli/SKILL.md` is missing, create a temporary SKILL.md stub:

  ```markdown
  ---
  name: rosa-cli
  description: ROSA CLI command reference — stub, Task 2 will complete this.
  license: Apache-2.0
  user_invocable: false
  model: inherit
  color: "#cc0000"
  allowed-tools: []
  ---

  # stub
  ```

  Re-run `make lint`. It must pass before committing.

- [ ] **Step 5: Commit**

  ```bash
  git add plugins/rosa/skills/rosa-cli/AGENTS.md plugins/rosa/.claude-plugin/plugin.json
  # Include stub SKILL.md if it was created in step 4
  git add plugins/rosa/skills/rosa-cli/SKILL.md 2>/dev/null || true
  git commit -m "feat(rosa): scaffold rosa-cli skill directory and bump plugin version to 0.4.0"
  ```

---

### Task 2: Write SKILL.md — Auth & Config, Classic Lifecycle, HCP Lifecycle (Sections 1–3)

**Files:**
- Create or overwrite: `plugins/rosa/skills/rosa-cli/SKILL.md`

**Interfaces:**
- Consumes: spec at `docs/superpowers/specs/2026-06-29-rosa-cli-skill-design.md` (read it fully before writing)
- Produces: `plugins/rosa/skills/rosa-cli/SKILL.md` containing the frontmatter + Sections 1, 2, 3 of the spec, with a `<!-- SECTIONS 4-5 TBD -->` placeholder comment at the end so `make lint` can still parse it

- [ ] **Step 1: Read the full spec**

  Read `docs/superpowers/specs/2026-06-29-rosa-cli-skill-design.md`. Identify:
  - "SKILL.md Frontmatter" block in the Implementation Notes section → this is the exact YAML frontmatter to use
  - Section 1 "Authentication & Config" → verbatim content for SKILL.md Section 1
  - Section 2 "Classic Cluster Lifecycle" → verbatim content for SKILL.md Section 2
  - Section 3 "HCP Cluster Lifecycle" → verbatim content for SKILL.md Section 3

- [ ] **Step 2: Write SKILL.md with frontmatter + Sections 1-3**

  Create `plugins/rosa/skills/rosa-cli/SKILL.md`. The file must begin with this exact frontmatter:

  ```yaml
  ---
  name: rosa-cli
  description: |
    Command reference, lifecycle sequences, and Classic/HCP behavioral differences for the ROSA CLI.

    Use when:
    - Creating, managing, or deleting ROSA Classic or HCP clusters
    - Setting up STS roles, OIDC configs, and operator roles
    - Working with node pools, IDPs, ingress, or autoscaler
    - Scheduling or monitoring cluster upgrades
    - Troubleshooting ROSA CLI commands

    Covers all rosa subcommands with exact flags and Classic/HCP parallel sections.
    NOT for: ROSA cost estimation (use rosa-cost skill).
  license: Apache-2.0
  user_invocable: false
  model: inherit
  color: "#cc0000"
  allowed-tools: []
  ---
  ```

  After the frontmatter, write the body heading and cite the AWS ROSA docs:

  ```markdown
  # ROSA CLI Reference

  Cite https://docs.openshift.com/rosa/rosa_cli/rosa-cli-about.html when presenting CLI guidance. Commands in this skill are current as of ROSA CLI v1.2 — run `rosa version` and compare against https://github.com/openshift/rosa/releases to verify currency before advising customers.
  ```

  Then copy Sections 1, 2, and 3 verbatim from the spec (everything from `## Section 1: Authentication & Config` through the end of `## Section 3: HCP Cluster Lifecycle`). Do not paraphrase — the flag tables and command examples must be character-for-character identical to the spec.

  End the file with this line so the linter can parse a complete file:

  ```markdown
  <!-- sections 4 and 5 follow in the next commit -->
  ```

- [ ] **Step 3: Verify with make lint**

  Run: `make lint`

  Expected: PASS. If it fails with a YAML parse error, check that the frontmatter block uses `---` delimiters and no tab characters.

- [ ] **Step 4: Commit**

  ```bash
  git add plugins/rosa/skills/rosa-cli/SKILL.md
  git commit -m "feat(rosa-cli): add auth, Classic, and HCP lifecycle sections to rosa-cli skill"
  ```

---

### Task 3: Complete SKILL.md — Command Reference + Self-Improvement, then lint and update

**Files:**
- Modify: `plugins/rosa/skills/rosa-cli/SKILL.md` (append Sections 4 and 5, remove the placeholder comment)

**Interfaces:**
- Consumes: `plugins/rosa/skills/rosa-cli/SKILL.md` from Task 2 (read it to find the `<!-- sections 4 and 5 follow -->` comment)
- Produces: complete `plugins/rosa/skills/rosa-cli/SKILL.md` with all 5 sections; `make lint` and `make update` both pass

- [ ] **Step 1: Read the spec Section 4**

  Read `docs/superpowers/specs/2026-06-29-rosa-cli-skill-design.md`. Locate Section 4 "Command Reference" — it starts with `## Section 4: Command Reference` and runs to the end of the alphabetical command listing. This section is the largest (60+ command entries). Copy it verbatim.

- [ ] **Step 2: Read the spec Section 5**

  In the same spec file, locate Section 5 "Self-Improvement Principle". Copy it verbatim. Stop before the `## Implementation Notes` heading — that section is for this plan, not for SKILL.md.

- [ ] **Step 3: Replace placeholder comment and append sections 4-5**

  Read `plugins/rosa/skills/rosa-cli/SKILL.md`. Remove the `<!-- sections 4 and 5 follow in the next commit -->` line. Append Section 4 (Command Reference) and then Section 5 (Self-Improvement Principle) from the spec, verbatim.

  The final structure of SKILL.md must be:

  ```
  [frontmatter]
  # ROSA CLI Reference
  [cite line]
  ## Section 1: Authentication & Config
  ## Section 2: Classic Cluster Lifecycle
  ## Section 3: HCP Cluster Lifecycle
  ## Section 4: Command Reference
  ## Section 5: Self-Improvement Principle
  ```

- [ ] **Step 4: Verify with make lint**

  Run: `make lint`

  Expected: PASS with no errors. If there are warnings, read them — fix any that are errors. Warnings about non-critical style issues are acceptable.

- [ ] **Step 5: Run make update**

  Run: `make update`

  Expected: regenerates `docs/` marketplace files without errors.

- [ ] **Step 6: Commit**

  ```bash
  git add plugins/rosa/skills/rosa-cli/SKILL.md docs/
  git commit -m "feat(rosa-cli): complete command reference and self-improvement sections; update marketplace docs"
  ```
