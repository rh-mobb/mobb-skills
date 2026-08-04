#!/usr/bin/env bash
# git-guard.sh — deterministic backstop for github-distributed-workflow
#
# Runs as a Cursor beforeShellExecution hook on git commit/push.
# Blocks: commits to main/master, hard force-pushes, staged secrets.
# Fails open on any unexpected error (failClosed: false in hooks.json).

set -uo pipefail

allow() { printf '{"permission":"allow"}\n'; exit 0; }
deny()  {
  local agent_msg="$1" user_msg="$2"
  printf '{"permission":"deny","agent_message":"%s","user_message":"%s"}\n' \
    "$agent_msg" "$user_msg"
  exit 0
}

# Parse stdin — fail open if we can't read it
input=$(cat 2>/dev/null) || allow
command=$(printf '%s' "$input" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('command',''))" 2>/dev/null) || allow
cwd=$(printf '%s' "$input" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('cwd',''))" 2>/dev/null) || allow

[[ -z "$command" ]] && allow
[[ -z "$cwd" || ! -d "$cwd" ]] && allow

cd "$cwd" || allow

# 1. Block commits directly to main/master
if printf '%s' "$command" | grep -qE 'git[[:space:]]+commit'; then
  branch=$(git branch --show-current 2>/dev/null || true)
  if [[ "$branch" == "main" || "$branch" == "master" ]]; then
    deny \
      "Blocked by git-guard: attempted to commit directly to '$branch'. Create a feature branch first, e.g. git checkout -b feat/<issue>-<description>, per the github-distributed-workflow skill." \
      "git-guard blocked a commit to '$branch'. Switch to a feature branch before committing."
  fi
fi

# 2. Block hard force-pushes (--force / -f); allow --force-with-lease
if printf '%s' "$command" | grep -qE 'git[[:space:]]+push'; then
  if printf '%s' "$command" | grep -qE '(^|[[:space:]])(--force|-f)([[:space:]]|$)' && \
     ! printf '%s' "$command" | grep -q 'force-with-lease'; then
    deny \
      "Blocked by git-guard: hard force-push detected. Never force-push a branch with an open PR. Use --force-with-lease on branches you own exclusively." \
      "git-guard blocked a hard force-push. Use --force-with-lease instead."
  fi
fi

# 3. Scan staged diff and command text for secret patterns before commit
if printf '%s' "$command" | grep -qE 'git[[:space:]]+commit'; then
  diff=$(git diff --cached 2>/dev/null || true)
  scan_target="$diff
$command"

  secret_patterns=(
    'AKIA[0-9A-Z]{16}'
    'gh[pousr]_[A-Za-z0-9]{20,}'
    'xox[baprs]-[A-Za-z0-9-]{10,}'
    'BEGIN[[:space:]][A-Z ]*PRIVATE KEY'
    '(password|secret|token|api_key)[[:space:]]*[:=][[:space:]]*['"'"'"][^'"'"'"]{8,}['"'"'"]'
  )

  for pattern in "${secret_patterns[@]}"; do
    if printf '%s' "$scan_target" | grep -qiE "$pattern"; then
      deny \
        "Blocked by git-guard: possible secret pattern detected in staged changes or command. Unstage the affected file and confirm with the user if this is a false positive." \
        "git-guard flagged a possible secret in this commit. Please review staged changes."
    fi
  done

  # Block staged .env files
  staged_files=$(git diff --cached --name-only 2>/dev/null || true)
  if printf '%s' "$staged_files" | grep -qE '(^|/)\.env(\.|$)'; then
    deny \
      "Blocked by git-guard: a .env file is staged for commit. Remove it, add it to .gitignore, and never commit environment files with real values." \
      "git-guard blocked: a .env file was staged. Remove it before committing."
  fi
fi

allow
