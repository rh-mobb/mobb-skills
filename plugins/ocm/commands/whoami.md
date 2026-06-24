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

Run the following and present the output to the user in a readable summary:

```bash
# Show active config file
echo "Config: ${OCM_CONFIG:-default (~/.config/ocm/ocm.json on Linux, ~/Library/Application Support/ocm/ocm.json on macOS)}"

# Current user details
ocm whoami

# API endpoint
ocm config get url
```

If `ocm whoami` returns an error about missing credentials, tell the user to run:
```bash
ocm login --token=<token>  # get token at https://console.redhat.com/openshift/token
```
