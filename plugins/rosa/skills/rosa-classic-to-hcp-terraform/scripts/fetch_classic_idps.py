#!/usr/bin/env python3
# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0
"""List Classic cluster IdPs and fetch full OCM describe JSON for each (plus htpasswd users)."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from shutil import which
from typing import Any


def _items(doc: Any) -> list[dict[str, Any]]:
    if isinstance(doc, list):
        return doc
    if isinstance(doc, dict):
        for key in ("items", "Items"):
            if key in doc and isinstance(doc[key], list):
                return doc[key]
    return []


def _ocm_get_json(href: str) -> dict[str, Any] | None:
    if not href.startswith("/"):
        href = f"/{href}"
    try:
        proc = subprocess.run(
            ["ocm", "get", href],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    return json.loads(proc.stdout)


def _idp_type_short(ocm_type: str) -> str:
    mapping = {
        "HTPasswdIdentityProvider": "htpasswd",
        "GithubIdentityProvider": "github",
        "GitlabIdentityProvider": "gitlab",
        "GoogleIdentityProvider": "google",
        "LDAPIdentityProvider": "ldap",
        "OpenIDIdentityProvider": "openid",
    }
    return mapping.get(ocm_type, ocm_type.replace("IdentityProvider", "").lower() or "unknown")


def _htpasswd_users(cluster_href: str, idp_id: str) -> list[dict[str, Any]]:
    base = cluster_href.rstrip("/")
    if "/clusters/" in base:
        path = f"{base}/identity_providers/{idp_id}/htpasswd_users"
    else:
        return []
    doc = _ocm_get_json(path)
    if not doc:
        return []
    users = []
    for u in _items(doc):
        users.append(
            {
                "id": u.get("id"),
                "username": u.get("username") or u.get("id"),
            }
        )
    return users


def enrich_idps(list_doc: Any, *, cluster_id: str | None = None) -> dict[str, Any]:
    idps_out: list[dict[str, Any]] = []
    for item in _items(list_doc):
        name = str(item.get("name") or "idp")
        href = str(item.get("href") or "")
        detail = _ocm_get_json(href) if href else dict(item)
        if detail is None:
            detail = dict(item)
        idp_id = str(detail.get("id") or item.get("id") or "")
        short = _idp_type_short(str(detail.get("type") or item.get("type") or ""))
        entry: dict[str, Any] = {
            "name": name,
            "id": idp_id,
            "type": short,
            "ocm_type": detail.get("type"),
            "mapping_method": detail.get("mapping_method"),
            "href": href,
            "detail": _public_idp_detail(detail, short),
        }
        if short == "htpasswd":
            cluster_path = href.rsplit("/identity_providers/", 1)[0] if href else ""
            if cluster_path:
                entry["htpasswd_users"] = _htpasswd_users(cluster_path, idp_id)
            else:
                entry["htpasswd_users"] = []
        idps_out.append(entry)
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cluster_id": cluster_id,
        "identity_providers": idps_out,
    }


def _public_idp_detail(detail: dict[str, Any], short: str) -> dict[str, Any]:
    """Strip secrets; keep fields useful for commented Terraform."""
    if short == "htpasswd":
        return {}
    if short == "github":
        gh = detail.get("github") or {}
        return {
            "client_id": gh.get("client_id"),
            "hostname": gh.get("hostname"),
            "organizations": gh.get("organizations"),
            "teams": gh.get("teams"),
        }
    if short == "gitlab":
        gl = detail.get("gitlab") or {}
        return {
            "client_id": gl.get("client_id"),
            "url": gl.get("url"),
        }
    if short == "google":
        gg = detail.get("google") or {}
        return {
            "client_id": gg.get("client_id"),
            "hosted_domain": gg.get("hosted_domain"),
        }
    if short == "ldap":
        ld = detail.get("ldap") or {}
        return {
            "url": ld.get("url"),
            "bind_dn": ld.get("bind_dn"),
            "insecure": ld.get("insecure"),
            "attributes": ld.get("attributes"),
        }
    if short == "openid":
        oid = detail.get("openid") or {}
        return {
            "client_id": oid.get("client_id"),
            "issuer": oid.get("issuer"),
            "claims": oid.get("claims"),
            "extra_scopes": oid.get("extra_scopes"),
            "extra_authorize_parameters": oid.get("extra_authorize_parameters"),
        }
    return {k: v for k, v in detail.items() if k not in ("client_secret", "bind_password")}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cluster", required=True, help="Classic cluster name or ID")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--list-json", type=Path, default=None, help="Existing rosa list idps JSON")
    args = parser.parse_args()

    if args.list_json:
        list_doc = json.loads(args.list_json.read_text(encoding="utf-8"))
        cluster_id = None
    else:
        proc = subprocess.run(
            ["rosa", "list", "idps", "-c", args.cluster, "-o", "json"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise SystemExit(proc.stderr or proc.stdout or "rosa list idps failed")
        list_doc = json.loads(proc.stdout)
        cluster_id = args.cluster

    inv = enrich_idps(list_doc, cluster_id=cluster_id)
    args.output.write_text(json.dumps(inv, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(inv['identity_providers'])} IdP(s) to {args.output.resolve()}")
    if not which("ocm"):
        print("Note: `ocm` not on PATH; output uses list JSON only (no per-IdP describe).", file=sys.stderr)


if __name__ == "__main__":
    main()
