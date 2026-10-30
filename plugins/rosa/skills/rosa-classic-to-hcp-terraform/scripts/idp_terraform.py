#!/usr/bin/env python3
# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0
"""Map Classic IdP inventory JSON to HCP module identity_providers Terraform artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _tf_key(name: str) -> str:
    key = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    key = re.sub(r"_+", "_", key).strip("_").lower()
    return key or "idp"


def _hcl_string(val: str) -> str:
    escaped = val.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _hcl_list_strings(values: list[str]) -> str:
    if not values:
        return "[]"
    inner = ", ".join(_hcl_string(v) for v in values)
    return f"[{inner}]"


def generate_idp_artifacts(
    inventory: dict[str, Any],
    *,
    target_cluster_name: str,
) -> tuple[dict[str, Any], str, str, str, bool]:
    """Return (active_identity_providers map, htpasswd_tf, optional_tf, migration_md, needs_random)."""
    idps = inventory.get("identity_providers") or []
    active: dict[str, Any] = {}
    htpasswd_lines: list[str] = []
    optional_lines: list[str] = [
        "# Optional Classic IdPs — uncomment and complete secrets after coordinating with the provider.",
        "# OAuth redirect (public cluster):",
        "#   https://oauth-openshift.apps.<apps-domain>/oauth2callback/<idp-name>",
        "# Replace <apps-domain> once the HCP cluster exists (rosa describe cluster / console URL).",
        "",
        "# Merge into module.roa_hcp identity_providers or var.identity_providers, e.g.:",
        "# identity_providers = merge(var.identity_providers, { ... })",
        "",
    ]
    migration: list[str] = ["## Identity providers (Classic → HCP)", ""]

    needs_random = False
    pwd_resources: list[str] = []

    for idp in idps:
        name = str(idp.get("name") or "idp")
        key = _tf_key(name)
        idp_type = str(idp.get("type") or "unknown")
        mapping = idp.get("mapping_method")
        migration.append(f"### `{name}` ({idp_type})")

        if idp_type == "htpasswd":
            users = idp.get("htpasswd_users") or []
            user_specs: list[str] = []
            user_json_parts: list[str] = []
            for u in users:
                uname = str(u.get("username") or "user")
                safe = re.sub(r"[^a-z0-9_]", "_", uname.lower())
                res = f"idp_{key}_{safe}"
                needs_random = True
                pwd_resources.append(
                    f'resource "random_password" "{res}" {{\n'
                    f"  length      = 14\n"
                    f"  special     = true\n"
                    f"  min_lower   = 1\n"
                    f"  min_numeric = 1\n"
                    f"  min_special = 1\n"
                    f"  min_upper   = 1\n"
                    f"}}\n"
                )
                user_json_parts.append(
                    f"{{ username = {_hcl_string(uname)}, "
                    f"password = random_password.{res}.result }}"
                )
            htpasswd_jsonencode = ""
            if user_json_parts:
                htpasswd_jsonencode = f"jsonencode([{', '.join(user_json_parts)}])"
            if user_json_parts:
                migration.append(
                    f"- Replicated **{len(users)}** htpasswd user(s) with **new** random passwords "
                    "(Classic passwords are not exported from OCM)."
                )
                active[key] = {
                    "name": name,
                    "idp_type": "htpasswd",
                    "htpasswd_jsonencode": htpasswd_jsonencode,
                    "mapping_method": mapping,
                }
            else:
                migration.append(
                    "- OCM listed no htpasswd users — commented stub in "
                    "`identity_providers_optional.tf` (module rejects empty htpasswd at apply)."
                )
                optional_lines.append(f"# --- {name} (htpasswd) ---")
                optional_lines.append(f"# {key} = {{")
                optional_lines.append(f'#   name         = {_hcl_string(name)}')
                optional_lines.append(f'#   idp_type     = "htpasswd"')
                if mapping:
                    optional_lines.append(f'#   mapping_method = {_hcl_string(str(mapping))}')
                optional_lines.append("#   htpasswd_idp_users = jsonencode([")
                optional_lines.append(
                    '#     { username = "user", password = random_password.example.result },'
                )
                optional_lines.append("#   ])")
                optional_lines.append("# }")
                optional_lines.append("")
            continue

        migration.append(
            "- Generated commented Terraform stub in `identity_providers_optional.tf`. "
            "Register a **new** OAuth/OIDC client for the HCP cluster callback URL before enabling."
        )
        detail = idp.get("detail") or {}
        optional_lines.append(f"# --- {name} ({idp_type}) ---")
        optional_lines.append(f"# {key} = {{")
        optional_lines.append(f'#   name         = {_hcl_string(name)}')
        optional_lines.append(f'#   idp_type     = {_hcl_string(idp_type)}')
        if mapping:
            optional_lines.append(f'#   mapping_method = {_hcl_string(str(mapping))}')
        optional_lines.extend(_commented_type_fields(idp_type, detail))
        optional_lines.append("# }")
        optional_lines.append("")

    htpasswd_tf = "\n".join(pwd_resources) if pwd_resources else ""
    optional_tf = "\n".join(optional_lines) + "\n"
    migration_md = "\n".join(migration) + "\n"
    return active, htpasswd_tf, optional_tf, migration_md, needs_random


def _commented_type_fields(idp_type: str, detail: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    if idp_type == "openid":
        if detail.get("issuer"):
            lines.append(f'#   openid_idp_issuer = {_hcl_string(str(detail["issuer"]))}')
        if detail.get("client_id"):
            lines.append(f'#   openid_idp_client_id = {_hcl_string(str(detail["client_id"]))}')
        lines.append('#   openid_idp_client_secret = "<from IdP admin / vault>"')
        claims = detail.get("claims") or {}
        for claim_key, var in (
            ("email", "openid_idp_claims_email"),
            ("name", "openid_idp_claims_name"),
            ("preferred_username", "openid_idp_claims_preferred_username"),
            ("groups", "openid_idp_claims_groups"),
        ):
            val = claims.get(claim_key)
            if isinstance(val, list) and val:
                lines.append(f"#   {var} = {_hcl_list_strings([str(x) for x in val])}")
    elif idp_type == "github":
        if detail.get("client_id"):
            lines.append(f'#   github_idp_client_id = {_hcl_string(str(detail["client_id"]))}')
        lines.append('#   github_idp_client_secret = "<from GitHub OAuth app>"')
        if detail.get("hostname"):
            lines.append(f'#   github_idp_hostname = {_hcl_string(str(detail["hostname"]))}')
    elif idp_type == "gitlab":
        if detail.get("url"):
            lines.append(f'#   gitlab_idp_url = {_hcl_string(str(detail["url"]))}')
        if detail.get("client_id"):
            lines.append(f'#   gitlab_idp_client_id = {_hcl_string(str(detail["client_id"]))}')
        lines.append('#   gitlab_idp_client_secret = "<from GitLab application>"')
    elif idp_type == "google":
        if detail.get("client_id"):
            lines.append(f'#   google_idp_client_id = {_hcl_string(str(detail["client_id"]))}')
        lines.append('#   google_idp_client_secret = "<from Google Cloud console>"')
        if detail.get("hosted_domain"):
            lines.append(
                f'#   google_idp_hosted_domain = {_hcl_string(str(detail["hosted_domain"]))}'
            )
    elif idp_type == "ldap":
        if detail.get("url"):
            lines.append(f'#   ldap_idp_url = {_hcl_string(str(detail["url"]))}')
        if detail.get("bind_dn"):
            lines.append(f'#   ldap_idp_bind_dn = {_hcl_string(str(detail["bind_dn"]))}')
        lines.append('#   ldap_idp_bind_password = "<set at apply time>"')
    return lines


def format_identity_providers_tfvars(active: dict[str, Any]) -> str:
    """Operator tfvars: literals only. Htpasswd with random_password lives in .tf locals."""
    return "identity_providers = {}\n"


def format_identity_providers_classic_tf(active: dict[str, Any]) -> str:
    if not active:
        return ""
    lines = [
        "# Replicated from Classic (--idps-json). Passwords are new random values.",
        "locals {",
        "  identity_providers_classic = {",
    ]
    for key, spec in active.items():
        lines.append(f"    {key} = {{")
        lines.append(f"      name     = {_hcl_string(spec['name'])}")
        lines.append(f"      idp_type = {_hcl_string(spec['idp_type'])}")
        if spec.get("mapping_method"):
            lines.append(f"      mapping_method = {_hcl_string(str(spec['mapping_method']))}")
        enc = spec.get("htpasswd_jsonencode")
        if enc:
            lines.append(f"      htpasswd_idp_users = {enc}")
        lines.append("    }")
    lines.append("  }")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def load_inventory(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def format_idp_briefing(inventory: dict[str, Any]) -> str:
    idps = inventory.get("identity_providers") or []
    lines = ["## Identity providers (Classic)", ""]
    if not idps:
        lines.append("_No IdPs on Classic cluster._")
        return "\n".join(lines)
    lines.extend(["| Name | Type | Users / notes |", "|------|------|---------------|"])
    for idp in idps:
        name = idp.get("name", "?")
        typ = idp.get("type", "?")
        note = ""
        if typ == "htpasswd":
            users = idp.get("htpasswd_users") or []
            note = f"{len(users)} htpasswd user(s)" if users else "no users listed"
        elif typ in ("openid", "github", "gitlab", "google"):
            note = "OAuth/OIDC — needs new client + callback for HCP"
        lines.append(f"| `{name}` | {typ} | {note} |")
    lines.extend(
        [
            "",
            "HCP mapper **replicates htpasswd** IdPs (new random passwords). "
            "Other types land in commented `identity_providers_optional.tf`.",
        ]
    )
    return "\n".join(lines)
