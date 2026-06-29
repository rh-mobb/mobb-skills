# AGENTS.md

Claude Code plugins repository for the MOBB team. Plugins live under `plugins/`.

## Structure

```text
plugins/{plugin-name}/
├── .claude-plugin/
│   └── plugin.json               # Required: name, description, version, author
├── commands/
│   └── {command-name}.md         # Required: at least one command
├── skills/                        # Optional: AI guidance skills
│   └── {skill-name}/
│       └── SKILL.md
├── .mcp.json                      # Optional: MCP servers to bundle with this plugin
├── OWNERS                         # Required: GitHub usernames of approvers
└── README.md                      # Required: plugin docs
```

Canonical example: `plugins/ocm/`

## Development Commands

| Command | When |
|---------|------|
| `make lint` | Before every commit — validates structure, format, and marketplace registration |
| `make update` | After adding/changing plugins — syncs docs and marketplace |
| Bump `version` in `plugin.json` | When modifying commands or skills (not README-only changes) |

## Skill References

Some skills are built from or maintained against an upstream CLI or SDK source tree. These source trees live under `references/` and are **gitignored** — they are never committed to this repo. Anyone doing major skill development must clone the relevant reference locally before starting.

### How it works

- `references/<tool-name>/` — a full clone of the upstream repo, used as source material when writing or updating a skill.
- Each skill that has a reference documents the exact clone command in its own `AGENTS.md` file, located alongside `SKILL.md` (e.g. `plugins/ocm/skills/ocm-cli/AGENTS.md`).
- For routine edits (fixing a flag, adding a note) you do **not** need to clone the reference — the `SKILL.md` is self-contained. Clone only when doing a major update: new subcommand coverage, API version changes, or reconciling the skill against a new CLI release.

### Loading a reference

Before starting a major skill update, check the skill's `AGENTS.md` for the exact clone command and run it. The reference directory will appear locally but is gitignored.

### Pattern for new skills with references

When creating a new skill that is based on an upstream CLI or SDK, create `plugins/<plugin>/skills/<skill>/AGENTS.md`:

```markdown
# <Skill Name> — Developer Reference

This skill was built from <upstream repo>. For major updates, clone the reference first:

    git clone <upstream-url> references/<tool-name>

Then consult:
- <path> — <what to find there>
- <path> — <what to find there>

The reference is gitignored. Do not commit it.
```

## Rules

- Every plugin needs `plugin.json`, at least one `commands/*.md`, `OWNERS`, `README.md`
- OWNERS must list at least one GitHub username
- MCP servers that your plugin depends on go in `.mcp.json` — skillsaw will flag any not in the allowlist in `.skillsaw.yaml`
- Command frontmatter must have `description:` and `argument-hint:` (if the command takes args)
- Skills must have `name:` and `description:` in frontmatter
- Skills with upstream references must include an `AGENTS.md` alongside `SKILL.md` with the clone command and key paths (see Skill References above)
