#!/usr/bin/env python3
# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0
"""Customer VPC endpoint adopt stubs (excludes ROSA HCP control-plane VPCE)."""

from __future__ import annotations

import re
from typing import Any


def _hcl_string(val: str) -> str:
    escaped = val.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _slug(service_name: str, endpoint_id: str) -> str:
    base = service_name.split(".")[-1] if service_name else endpoint_id
    return re.sub(r"[^a-z0-9_]", "_", base.lower()).strip("_") or "endpoint"


def adoptable_vpc_endpoints(inv: dict[str, Any]) -> list[dict[str, Any]]:
    return [e for e in inv.get("vpc_endpoints") or [] if e.get("adoptable")]


def excluded_rosa_hcp_vpc_endpoints(inv: dict[str, Any]) -> list[dict[str, Any]]:
    return [e for e in inv.get("vpc_endpoints") or [] if e.get("rosa_hcp_control_plane")]


def generate_vpc_endpoints_adopt_tf(inv: dict[str, Any], *, mode: str) -> str:
    """Emit adopt Terraform for customer VPC endpoints only (not ROSA HCP control-plane VPCE)."""
    if mode != "adopt":
        return ""
    endpoints = adoptable_vpc_endpoints(inv)
    if not endpoints:
        return ""

    lines = [
        "# Customer VPC endpoints (adopt) — ROSA HCP control-plane VPCE is excluded (ROSA-managed).",
        "# Uncomment and align resources after operator confirms endpoint adopt.",
        "",
    ]

    for ep in endpoints:
        eid = str(ep["id"])
        svc = str(ep.get("service_name") or "")
        etype = str(ep.get("type") or "Gateway")
        res = _slug(svc, eid)
        lines.extend(
            [
                f"# Endpoint {eid} — {svc} ({etype})",
                "# import {",
                f'#   to = aws_vpc_endpoint.{res}',
                f"#   id = {_hcl_string(eid)}",
                "# }",
                f'resource "aws_vpc_endpoint" "{res}" {{',
                f"  vpc_id       = aws_vpc.this.id",
                f"  service_name = {_hcl_string(svc)}",
                f"  vpc_endpoint_type = {_hcl_string(etype)}",
                "  # TODO: copy route_table_ids / subnet_ids / security_group_ids from AWS console or inventory",
                "  lifecycle {",
                "    ignore_changes = [tags]",
                "  }",
                "}",
                "",
            ]
        )

    return "\n".join(lines)
