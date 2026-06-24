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

## Rules

- Every plugin needs `plugin.json`, at least one `commands/*.md`, `OWNERS`, `README.md`
- OWNERS must list at least one GitHub username
- MCP servers that your plugin depends on go in `.mcp.json` — skillsaw will flag any not in the allowlist in `.skillsaw.yaml`
- Command frontmatter must have `description:` and `argument-hint:` (if the command takes args)
- Skills must have `name:` and `description:` in frontmatter
