# github

Claude Code plugin for GitHub distributed workflow best practices.

## Skills

### `github-distributed-workflow`

Auto-invoked whenever the agent interacts with Git or GitHub. Enforces:

- **Branching strategy** — never on `main`, `<type>/<issue>-<desc>` naming, always pull latest before branching.
- **Conventional Commits** — `type(scope): description`, atomic commits, no AI co-author trailers.
- **Pull request generation** — structured body (Motivation / Changes / Testing), linked issue, CI verified before merge.
- **Conflict resolution** — semantic analysis of both sides, no blind accepts, human confirmation for ambiguous cases.
- **Security** — no secrets, no force-pushes to shared branches, sensitive files require explicit confirmation.

## Commands

### `/github:create-pr`

Creates a pull request from the current branch following the workflow rules above.

```
/github:create-pr [branch-or-issue-context]
```

## Cursor Install

Skills work in Cursor as-is — commands are Claude Code only.

```bash
for skill in github-distributed-workflow github-branching github-commits github-pull-requests github-security github-conflict-resolution; do
  mkdir -p ~/.cursor/skills/$skill
  cp plugins/github/skills/$skill/SKILL.md ~/.cursor/skills/$skill/
done
```

Restart Cursor. The `github-distributed-workflow` skill auto-invokes on git/GitHub work; the others load on demand as detail references.

## Source

Skill adapted from [cursor-github-best-practices-skill](https://github.com/manujoy7/cursor-github-best-practices-skill) (MIT).
