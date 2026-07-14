---
description: Show the currently authenticated ROSA user and account details.
argument-hint: ""
---

## Name

rosa:whoami

## Synopsis

```
/rosa:whoami
```

## Description

Displays the identity of the currently authenticated ROSA user: username, organization, account ID, and API endpoint. Useful to confirm which account is active before running cluster operations.

## Implementation

**Step 0: Auth / profile setup**

Follow the profile resolution process from the rosa-cli skill. The `rosa` CLI reads credentials from `$OCM_CONFIG` (default: `~/.config/ocm/ocm.json`). To use a non-default profile:

```bash
export OCM_CONFIG="$HOME/.config/ocm/<profile-name>.json"
```

**Step 1: Run whoami**

```bash
rosa whoami
```

**Step 2: Present**

Pass the output through as-is — `rosa whoami` output is already human-readable. Append the active `OCM_CONFIG` path so the user knows which profile is in use:

```
<rosa whoami output>

Active profile: /Users/<user>/.config/ocm/ocm.json
```

If `rosa whoami` fails with a credentials error, instruct the user to log in:

```bash
rosa login --token <token>
# Get token at: https://console.redhat.com/openshift/token
```
