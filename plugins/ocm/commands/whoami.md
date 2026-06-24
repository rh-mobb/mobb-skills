---
description: Show the current OCM user, environment, and active profile.
---

## Name
ocm:whoami

## Synopsis
```
/ocm:whoami
```

## Description

The `ocm:whoami` command displays the current authenticated OCM user and the environment they are connected to. Useful to confirm which account and API endpoint are active before running cluster operations.

It shows:
- Username and account ID
- Organization name
- API URL (production vs staging)
- Active config profile path (`OCM_CONFIG` or default)

## Implementation

**Step 1: Resolve the active profile**

If the user specifies a profile name (e.g., "use my `ocm-rh` profile"), resolve it to a file path before running any `ocm` command:

```bash
# Detect OS
uname   # Darwin = macOS, Linux = Linux

# macOS config directory
OCM_DIR="$HOME/Library/Application Support/ocm"

# Linux config directory
OCM_DIR="$HOME/.config/ocm"

# Build full path for the named profile
export OCM_CONFIG="$OCM_DIR/<profile-name>.json"
```

If the user does not specify a profile, check whether `OCM_CONFIG` is already set. If it is not set, the `ocm` CLI uses the default profile (`ocm.json` in the platform config directory).

**Step 2: List available profiles (if needed)**

If the user is unsure which profile to use, list the available config files:

```bash
# macOS
ls "$HOME/Library/Application Support/ocm/"

# Linux
ls "$HOME/.config/ocm/"
```

Each `.json` file is a profile. The file stem (e.g., `ocm-rh`) is the profile name.

**Step 3: Confirm the active account**

```bash
ocm whoami        # current user, org, and account ID
ocm config get url  # confirm API endpoint (production vs staging)
```

Present the output as a concise summary: username, organization, API URL, and the resolved `OCM_CONFIG` path.

**If `ocm whoami` fails with a credentials error:**

```bash
ocm login --token=<token>  # get token at https://console.redhat.com/openshift/token
```

To log in to a named profile without overwriting the default:

```bash
OCM_CONFIG="$OCM_DIR/<profile-name>.json" ocm login --token=<token>
```
