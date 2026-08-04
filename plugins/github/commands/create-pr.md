---
description: Create a pull request following the team's GitHub distributed workflow best practices.
argument-hint: [branch-or-issue-context]
---

## Name

github:create-pr

## Synopsis

```
/github:create-pr [branch-or-issue-context]
```

## Description

Creates a pull request from the current branch using `gh pr create`, following the team's GitHub distributed workflow: conventional commits, structured PR body (Motivation / Changes / Testing), linked issue, and CI verification before proposing merge.

## Implementation

1. Confirm the current branch (`git branch --show-current`) — abort if on `main`/`master`.
2. Run `git status` and `git log origin/main..HEAD --oneline` to summarize what's being proposed.
3. Check for open PRs/issues to avoid duplicating in-flight work: `gh pr list`, `gh issue list`.
4. Draft a PR body using the template from the `github-distributed-workflow` skill:

   ```markdown
   ## Motivation
   [Why this change was made]

   ## Changes
   - [High-level change 1]

   ## Testing
   - [How this was verified]

   Closes #<issue-number>
   ```

5. Create the PR: `gh pr create --title "<type>(scope): description" --body "..."`.
6. After creation, run `gh pr checks <number>` and report CI status to the user.
7. Remind the user that merge requires explicit human approval — do not self-merge.
