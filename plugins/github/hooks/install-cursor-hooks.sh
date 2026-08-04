#!/usr/bin/env bash
# install-cursor-hooks.sh — install git-guard as a Cursor beforeShellExecution hook
#
# Run once per machine from the repo root:
#   bash plugins/github/hooks/install-cursor-hooks.sh
#
# Idempotent — safe to re-run after updates.

set -euo pipefail

HOOK_DIR="$HOME/.cursor/hooks"
HOOK_SCRIPT="$HOOK_DIR/git-guard.sh"
HOOKS_JSON="$HOME/.cursor/hooks.json"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing git-guard Cursor hook..."

# 1. Copy hook script
mkdir -p "$HOOK_DIR"
cp "$SCRIPT_DIR/git-guard.sh" "$HOOK_SCRIPT"
chmod +x "$HOOK_SCRIPT"
echo "  ✓ Hook script → $HOOK_SCRIPT"

# 2. Merge hook registration into hooks.json
HOOK_ENTRY=$(cat <<'EOF'
{
  "command": "bash ~/.cursor/hooks/git-guard.sh",
  "matcher": "git\\s+(commit|push)",
  "failClosed": false
}
EOF
)

if [[ ! -f "$HOOKS_JSON" ]]; then
  # No existing hooks.json — create it from scratch
  python3 - "$HOOKS_JSON" "$HOOK_ENTRY" <<'PYEOF'
import sys, json
path, entry = sys.argv[1], json.loads(sys.argv[2])
doc = {"version": 1, "hooks": {"beforeShellExecution": [entry]}}
with open(path, "w") as f:
    json.dump(doc, f, indent=2)
    f.write("\n")
PYEOF
  echo "  ✓ Created $HOOKS_JSON"
else
  # Existing hooks.json — merge our entry in, replacing any prior git-guard entry
  python3 - "$HOOKS_JSON" "$HOOK_ENTRY" <<'PYEOF'
import sys, json
path, entry = sys.argv[1], json.loads(sys.argv[2])
with open(path) as f:
    doc = json.load(f)
doc.setdefault("hooks", {}).setdefault("beforeShellExecution", [])
# Remove any existing git-guard entry, then append the current one
doc["hooks"]["beforeShellExecution"] = [
    h for h in doc["hooks"]["beforeShellExecution"]
    if "git-guard" not in h.get("command", "")
]
doc["hooks"]["beforeShellExecution"].append(entry)
with open(path, "w") as f:
    json.dump(doc, f, indent=2)
    f.write("\n")
PYEOF
  echo "  ✓ Updated $HOOKS_JSON"
fi

echo ""
echo "Done. Restart Cursor (or reload the Hooks settings tab) to activate."
echo ""
echo "The hook will block:"
echo "  • Commits directly to main/master"
echo "  • Hard force-pushes (--force / -f) on branches with open PRs"
echo "  • Staged secrets (API keys, tokens, private keys, .env files)"
