---
name: github-distributed-workflow
description: |
  Enforces GitHub best practices for distributed development — strict branching, semantic commits, and Pull Request generation.

  Use whenever:
  - Interacting with Git (committing, branching, pushing, merging)
  - Creating or reviewing pull requests
  - Resolving merge conflicts
  - Working with CI/CD workflows or security-sensitive files
license: MIT
user_invocable: true
model: inherit
color: "#24292f"
allowed-tools: []
---

# GitHub Distributed Workflow Rules

You are operating in a distributed development environment. Your primary goal when interacting with Git and GitHub is to make your work highly visible, easily auditable, and safe for human review.

## Hard rules (never violate)

- Never work directly on `main` or `master`. Always branch first.
- Never commit secrets, credentials, or `.env*` files.
- Never force-push (`--force`/`-f`) a branch that has an open PR; use `--force-with-lease` only on your own unshared branch.
- Never amend a commit you did not create in the current session, or one that has already been pushed.
- Never merge your own PR, or claim CI passed, without actually checking.
- Never add a `Co-authored-by: Claude` (or any other AI-agent) trailer to a commit. Commits are attributed solely to the human contributor's own configured git identity.

## 1. Branching strategy

- Always branch from the latest upstream `main` before starting work. Run `git fetch origin` and `git pull`.
- **Naming convention:** `<type>/<issue-number>-<short-description>` (e.g., `feat/142-auth-tokens`, `fix/89-race-condition`).
- Full detail, including worktree isolation for risky/exploratory changes: see `github-branching` skill.

## 2. Verification (the pre-commit loop)

- **Test before commit:** run the project's test suite or linter before staging files. Do not commit failing code.
- **Diff review:** always run `git diff` before creating a commit. Verify you are not leaving behind debugging artifacts (e.g., `console.log`, temporary comments) or unrelated files.

## 3. Commit conventions

- Use Conventional Commits format: `type(scope): description`.
- Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`.
- **Keep commits atomic.** If a change does two different things, split it into two separate commits.
- Full detail, including single-author attribution and amend rules: see `github-commits` skill.

## 4. Pull request generation

- When creating a PR (e.g., via `gh pr create`), you MUST include:
  - **Motivation:** why the change was made.
  - **Changes:** a high-level summary of what files/logic were altered.
  - **Testing:** explicit evidence of how the changes were verified (e.g., "Ran `make lint` successfully").
- Always link the relevant issue in the description (e.g., "Closes #142").
- Prefer several small, reviewable PRs over one large one.
- Verify CI is green (`gh pr checks`) before proposing a merge; never self-merge without explicit human confirmation.
- Full detail, including the PR body template and review process: see `github-pull-requests` skill.

## 5. Conflict resolution

- If you encounter a merge conflict, do NOT blindly accept "ours" or "theirs".
- Analyze the semantic intent of both changes.
- Propose and implement a resolution that preserves the intended functionality of both branches.
- Full detail: see `github-conflict-resolution` skill.

## Additional resources

- Security checklist and trust boundaries: `github-security` skill
- Branching detail: `github-branching` skill
- Commit detail: `github-commits` skill
- Pull request detail: `github-pull-requests` skill
- Conflict resolution detail: `github-conflict-resolution` skill
