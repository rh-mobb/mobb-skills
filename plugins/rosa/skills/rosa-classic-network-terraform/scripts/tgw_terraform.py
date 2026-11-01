#!/usr/bin/env python3
# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0
"""Commented Transit Gateway Terraform stubs from network-inventory.json."""

from __future__ import annotations

import re
from typing import Any


def _hcl_string(val: str) -> str:
    escaped = val.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", s.lower()).strip("_") or "az"


def _subnet_resource_name(subnet: dict[str, Any]) -> str:
    az = _slug(subnet["availability_zone"].split("-")[-1])
    role = "public" if subnet["public"] else "private"
    return f"{role}_{az}"


def _unique_tgw_routes(route_tables: list[dict[str, Any]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, str]] = []
    for rt in route_tables:
        for route in rt.get("routes") or []:
            tgw = route.get("transit_gateway_id")
            dest = route.get("destination_cidr")
            if not tgw or not dest:
                continue
            key = (str(tgw), str(dest))
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "transit_gateway_id": str(tgw),
                    "destination_cidr": str(dest),
                    "example_route_table_id": str(rt.get("id") or ""),
                }
            )
    return sorted(out, key=lambda x: (x["transit_gateway_id"], x["destination_cidr"]))


def generate_transit_gateway_optional_tf(
    inv: dict[str, Any],
    *,
    copy: bool,
    name_prefix: str,
) -> str:
    attachments = inv.get("transit_gateway_attachments") or []
    routes = _unique_tgw_routes(inv.get("route_tables") or [])
    if not attachments and not routes:
        return ""

    lines = [
        "# Optional Transit Gateway wiring — Classic pattern reference only.",
        "# The TGW itself and many route table updates are usually owned by a central network team.",
        "# Coordinate before uncommenting: attachment approval, propagation, and return paths.",
        "#",
        "# Classic VPC reference:",
        f"#   {inv['vpc']['id']} ({inv['vpc']['cidr_block']})",
        "",
    ]

    for att in attachments:
        tgw_id = str(att.get("transit_gateway_id") or "tgw-xxxxxxxx")
        att_name = (att.get("tags") or {}).get("Name") or f"{name_prefix}-tgw-attachment"
        lines.append(f"# --- TGW VPC attachment (Classic: {att.get('id', '?')}) ---")
        if copy:
            priv = sorted(
                [s for s in inv["subnets"] if not s["public"]],
                key=lambda s: s["availability_zone"],
            )
            subnet_exprs = [
                f"aws_subnet.{_subnet_resource_name(s)}.id" for s in priv
            ]
            subnet_block = ", ".join(subnet_exprs)
            vpc_expr = "aws_vpc.this.id"
        else:
            subnet_block = ", ".join(_hcl_string(s) for s in att.get("subnet_ids") or [])
            vpc_expr = _hcl_string(inv["vpc"]["id"])

        lines.extend(
            [
                "# resource \"aws_ec2_transit_gateway_vpc_attachment\" \"hcp\" {",
                f"#   transit_gateway_id = {_hcl_string(tgw_id)}",
                f"#   vpc_id             = {vpc_expr}",
                f"#   subnet_ids         = [{subnet_block}]",
                "#   dns_support        = \"enable\"",
                "#   ipv6_support       = \"disable\"",
                "#   tags = {",
                f"#     Name = {_hcl_string(str(att_name))}",
                "#   }",
                "# }",
                "",
            ]
        )

    if routes:
        lines.append("# --- VPC routes via TGW (mirror on each affected route table) ---")
        for idx, route in enumerate(routes, start=1):
            tgw_id = route["transit_gateway_id"]
            dest = route["destination_cidr"]
            rt_hint = route.get("example_route_table_id") or "rtb-xxxxxxxx"
            lines.append(
                f"# Classic example route table: {rt_hint} → {dest} via {tgw_id}"
            )
            if copy:
                rt_example = "aws_route_table.rt_private_a.id  # repeat per private RT / AZ"
            else:
                rt_example = _hcl_string(rt_hint)
            lines.extend(
                [
                    f"# resource \"aws_route\" \"tgw_{idx}\" {{",
                    f"#   route_table_id         = {rt_example}",
                    f"#   destination_cidr_block = {_hcl_string(dest)}",
                    f"#   transit_gateway_id     = {_hcl_string(tgw_id)}",
                    "# }",
                    "",
                ]
            )

    lines.append(
        "# TGW *route table* entries (hub side) are not in this VPC stack — network team only."
    )
    lines.append("")
    return "\n".join(lines)


def format_tgw_briefing(inv: dict[str, Any]) -> str:
    attachments = inv.get("transit_gateway_attachments") or []
    routes = _unique_tgw_routes(inv.get("route_tables") or [])
    if not attachments and not routes:
        return ""
    lines = ["", "## Transit Gateway (Classic VPC)", ""]
    for att in attachments:
        lines.append(
            f"- Attachment `{att.get('id', '?')}` → TGW `{att.get('transit_gateway_id', '?')}` "
            f"({len(att.get('subnet_ids') or [])} subnet(s))"
        )
    for route in routes:
        lines.append(
            f"- VPC route `{route['destination_cidr']}` → `{route['transit_gateway_id']}` "
            f"(example RT `{route.get('example_route_table_id', '?')}`)"
        )
    lines.extend(
        [
            "",
            "Generated **`transit_gateway_optional.tf`** (commented). Hub TGW changes typically "
            "require a **network / cloud foundation** team.",
        ]
    )
    return "\n".join(lines)
