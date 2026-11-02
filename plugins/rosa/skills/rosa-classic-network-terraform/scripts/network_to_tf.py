#!/usr/bin/env python3
# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0
"""Generate network Terraform and optional import blocks from network-inventory.json."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from ipaddress import ip_network
from pathlib import Path
from typing import Any

from tgw_terraform import generate_transit_gateway_optional_tf
from vpc_endpoints_terraform import (
    adoptable_vpc_endpoints,
    excluded_rosa_hcp_vpc_endpoints,
    generate_vpc_endpoints_adopt_tf,
)


def _hcl_string(val: str) -> str:
    escaped = val.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _hcl_bool(val: bool) -> str:
    return "true" if val else "false"


def _route_table_association_import_id(subnet_id: str, route_table_id: str) -> str:
    """Terraform AWS provider import id for aws_route_table_association (subnet route table)."""
    return f"{subnet_id}/{route_table_id}"


def _hcl_tags(tags: dict[str, str]) -> str:
    if not tags:
        return "{}"
    lines = ["{"]
    for key in sorted(tags):
        lines.append(f"    {_hcl_string(key)} = {_hcl_string(tags[key])}")
    lines.append("  }")
    return "\n".join(lines)


def _tag_expr_adopt(tags: dict[str, str]) -> str:
    inner = _hcl_tags(tags)
    if inner == "{}":
        return "var.common_tags"
    return f"merge(var.common_tags, {inner})"


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", s.lower()).strip("_") or "subnet"


def _sort_subnets(subnets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(subnets, key=lambda s: (s["availability_zone"], s["id"]))


def _route_table_for_subnet(inv: dict[str, Any], subnet_id: str) -> dict[str, Any] | None:
    for rt in inv.get("route_tables") or []:
        for assoc in rt.get("associations") or []:
            if assoc.get("subnet_id") == subnet_id and not assoc.get("main"):
                return rt
    return None


def _default_internet_route(rt: dict[str, Any]) -> dict[str, Any] | None:
    for route in rt.get("routes") or []:
        if route.get("destination_cidr") == "0.0.0.0/0":
            return route
    return None


def _nat_resource_by_az(inv: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for idx, ng in enumerate(inv.get("nat_gateways") or [], start=1):
        pub = next((s for s in inv["subnets"] if s["id"] == ng.get("subnet_id")), None)
        if pub:
            mapping[pub["availability_zone"]] = f"nat_{idx}"
    return mapping


def _append_rosa_routes(
    main_lines: list[str],
    imports: list[str],
    inv: dict[str, Any],
    *,
    copy: bool,
    name_prefix: str,
) -> None:
    """Per-subnet route tables matching terraform-rosa-networking (public→IGW, private→NAT/AZ)."""
    public_subnets = _sort_subnets([s for s in inv["subnets"] if s["public"]])
    private_subnets = _sort_subnets([s for s in inv["subnets"] if not s["public"]])
    nat_by_az = _nat_resource_by_az(inv)
    has_igw = copy or bool(inv.get("internet_gateways"))

    def rt_tag_line_copy(kind: str, az: str) -> str:
        return (
            "  tags = merge(local.common_tags, { "
            f'Name = "${{var.name_prefix}}-{kind}-{az}" '
            "})"
        )

    for subnet in public_subnets:
        az = subnet["availability_zone"]
        az_slug = _slug(az)
        sub_res = _subnet_resource_name(subnet, copy=copy)
        rt_res = f"rt_public_{az_slug}"
        route_res = f"route_public_{az_slug}"
        assoc_res = f"assoc_public_{az_slug}"
        rt = None if copy else _route_table_for_subnet(inv, subnet["id"])
        if not copy and rt is None:
            continue

        tag_line = rt_tag_line_copy("public", az) if copy else f"  tags = {_tag_expr_adopt((rt or {}).get('tags') or {})}"
        main_lines.extend(
            [
                f'resource "aws_route_table" "{rt_res}" {{',
                "  vpc_id = aws_vpc.this.id",
                tag_line,
                "  lifecycle {",
                "    ignore_changes = [tags]",
                "  }",
                "}",
                "",
            ]
        )
        if has_igw:
            main_lines.extend(
                [
                    f'resource "aws_route" "{route_res}" {{',
                    f"  route_table_id         = aws_route_table.{rt_res}.id",
                    '  destination_cidr_block = "0.0.0.0/0"',
                    "  gateway_id             = aws_internet_gateway.this.id",
                    "}",
                    "",
                ]
            )
        main_lines.extend(
            [
                f'resource "aws_route_table_association" "{assoc_res}" {{',
                f"  subnet_id      = aws_subnet.{sub_res}.id",
                f"  route_table_id = aws_route_table.{rt_res}.id",
                "}",
                "",
            ]
        )
        if not copy and rt:
            imports.extend(
                [
                    "import {",
                    f"  to = aws_route_table.{rt_res}",
                    f"  id = {_hcl_string(rt['id'])}",
                    "}",
                    "",
                ]
            )
            if has_igw and _default_internet_route(rt):
                imports.extend(
                    [
                        "import {",
                        f"  to = aws_route.{route_res}",
                        f"  id = {_hcl_string(rt['id'] + '_0.0.0.0/0')}",
                        "}",
                        "",
                    ]
                )
            assoc = next(
                (a for a in rt.get("associations") or [] if a.get("subnet_id") == subnet["id"]),
                None,
            )
            if assoc and subnet.get("id") and rt.get("id"):
                imports.extend(
                    [
                        "import {",
                        f"  to = aws_route_table_association.{assoc_res}",
                        f"  id = {_hcl_string(_route_table_association_import_id(subnet['id'], rt['id']))}",
                        "}",
                        "",
                    ]
                )

    for subnet in private_subnets:
        az = subnet["availability_zone"]
        az_slug = _slug(az)
        sub_res = _subnet_resource_name(subnet, copy=copy)
        rt_res = f"rt_private_{az_slug}"
        route_res = f"route_private_{az_slug}"
        assoc_res = f"assoc_private_{az_slug}"
        nat_res = nat_by_az.get(az)
        rt = None if copy else _route_table_for_subnet(inv, subnet["id"])
        if not copy and rt is None:
            continue

        tag_line = rt_tag_line_copy("private", az) if copy else f"  tags = {_tag_expr_adopt((rt or {}).get('tags') or {})}"
        main_lines.extend(
            [
                f'resource "aws_route_table" "{rt_res}" {{',
                "  vpc_id = aws_vpc.this.id",
                tag_line,
                "  lifecycle {",
                "    ignore_changes = [tags]",
                "  }",
                "}",
                "",
            ]
        )
        if nat_res:
            main_lines.extend(
                [
                    f'resource "aws_route" "{route_res}" {{',
                    f"  route_table_id         = aws_route_table.{rt_res}.id",
                    '  destination_cidr_block = "0.0.0.0/0"',
                    f"  nat_gateway_id         = aws_nat_gateway.{nat_res}.id",
                    "}",
                    "",
                ]
            )
        main_lines.extend(
            [
                f'resource "aws_route_table_association" "{assoc_res}" {{',
                f"  subnet_id      = aws_subnet.{sub_res}.id",
                f"  route_table_id = aws_route_table.{rt_res}.id",
                "}",
                "",
            ]
        )
        if not copy and rt:
            imports.extend(
                [
                    "import {",
                    f"  to = aws_route_table.{rt_res}",
                    f"  id = {_hcl_string(rt['id'])}",
                    "}",
                    "",
                ]
            )
            if nat_res and _default_internet_route(rt):
                imports.extend(
                    [
                        "import {",
                        f"  to = aws_route.{route_res}",
                        f"  id = {_hcl_string(rt['id'] + '_0.0.0.0/0')}",
                        "}",
                        "",
                    ]
                )
            assoc = next(
                (a for a in rt.get("associations") or [] if a.get("subnet_id") == subnet["id"]),
                None,
            )
            if assoc and subnet.get("id") and rt.get("id"):
                imports.extend(
                    [
                        "import {",
                        f"  to = aws_route_table_association.{assoc_res}",
                        f"  id = {_hcl_string(_route_table_association_import_id(subnet['id'], rt['id']))}",
                        "}",
                        "",
                    ]
                )


@dataclass
class GenerateResult:
    mode: str
    name_prefix: str
    vpc_cidr: str
    notes: list[str]
    unmapped: list[str]


def _copy_subnet_cidrs(
    vpc_cidr: str, subnets: list[dict[str, Any]]
) -> dict[str, str]:
    """Map existing subnet id -> new CIDR inside vpc_cidr preserving prefix lengths."""
    net = ip_network(vpc_cidr, strict=False)
    priv = _sort_subnets([s for s in subnets if not s["public"]])
    pub = _sort_subnets([s for s in subnets if s["public"]])
    ordered = priv + pub
    if not ordered:
        return {}
    prefix = ip_network(ordered[0]["cidr_block"], strict=False).prefixlen
    step = 2 ** (32 - prefix)
    base = int(net.network_address)
    mapping: dict[str, str] = {}
    offset = 0
    for s in ordered:
        new_net = ip_network((base + offset, prefix), strict=False)
        if not new_net.subnet_of(net):
            raise SystemExit(
                f"copy VPC CIDR {vpc_cidr} too small for {len(ordered)} /{prefix} subnets"
            )
        mapping[s["id"]] = str(new_net)
        offset += step
    return mapping


def _subnet_resource_name(subnet: dict[str, Any], *, copy: bool) -> str:
    az = _slug(subnet["availability_zone"].split("-")[-1])
    role = "public" if subnet["public"] else "private"
    return f"{role}_{az}"


def format_dry_run(inv: dict[str, Any], result: GenerateResult) -> str:
    src = inv["source"]
    lines = [
        f"Cluster: {src['cluster_name']} ({src['cluster_id']})",
        f"Region: {src['region']}",
        f"Mode: {result.mode}",
        f"VPC: {inv['vpc']['id']} ({inv['vpc']['cidr_block']})",
        f"Target VPC CIDR: {result.vpc_cidr}",
        f"Name prefix: {result.name_prefix}",
        f"Private cluster: {src['private_cluster']}",
        f"Subnets: {len(inv['subnets'])} (private "
        f"{sum(1 for s in inv['subnets'] if not s['public'])}, public "
        f"{sum(1 for s in inv['subnets'] if s['public'])})",
        f"NAT gateways: {len(inv.get('nat_gateways') or [])}",
        f"IGW: {len(inv.get('internet_gateways') or [])}",
        f"ROSA HCP aws_subnet_ids order: {', '.join(inv['rosa_hcp_wiring']['aws_subnet_ids'])}",
        "",
    ]
    excluded = excluded_rosa_hcp_vpc_endpoints(inv)
    if excluded:
        lines.append("ROSA HCP control-plane VPCE (do not adopt in network/):")
        for e in excluded:
            lines.append(f"  - {e['id']} {e.get('service_name') or ''}")
        lines.append("")
    adoptable = adoptable_vpc_endpoints(inv)
    if adoptable:
        lines.append("Customer VPC endpoints (ask operator before adopt):")
        for e in adoptable:
            lines.append(f"  - {e['id']} {e.get('type')} {e.get('service_name') or ''}")
        lines.append("")
    cp = inv.get("rosa_hcp_control_plane_vpc_endpoint")
    if cp and cp.get("additional_control_plane_security_group_ids"):
        lines.append(
            "Additional control-plane SGs (cluster adopt / additional-cp-sg module): "
            + ", ".join(cp["additional_control_plane_security_group_ids"])
        )
        lines.append("")
    lines.extend(
        [
        "",
        "Notes:",
    ]
    )
    lines.extend(f"  - {n}" for n in result.notes)
    if result.unmapped:
        lines.append("")
        lines.append("Unmapped / manual:")
        lines.extend(f"  - {u}" for u in result.unmapped)
    return "\n".join(lines)


def build_generate_result(
    inv: dict[str, Any],
    *,
    mode: str,
    vpc_cidr: str,
    name_prefix: str,
) -> GenerateResult:
    notes: list[str] = []
    unmapped: list[str] = []
    src = inv["source"]

    if mode == "adopt":
        notes.append("Adopt mode emits import blocks for existing AWS resource IDs.")
        notes.append("Resource tags are copied from inventory (merge with var.common_tags only).")
    else:
        notes.append("Copy mode plans net-new VPC resources (no import blocks).")
        if vpc_cidr == inv["vpc"]["cidr_block"]:
            unmapped.append(
                "Copy mode uses the same VPC CIDR as Classic — safe only when routing is isolated."
            )

    if src.get("cluster_state") == "ready" and mode == "adopt":
        notes.append(
            "Classic cluster is still ready — do not point a new HCP cluster at these subnet IDs."
        )

    if inv.get("route_tables"):
        notes.append(
            f"Route tables: {len(inv['route_tables'])} (per-subnet public→IGW, private→NAT/AZ; "
            "tags use lifecycle ignore_changes per terraform-rosa-networking)."
        )

    if excluded := excluded_rosa_hcp_vpc_endpoints(inv):
        notes.append(
            f"Excluded {len(excluded)} ROSA HCP control-plane VPC endpoint(s) from network adopt "
            f"({', '.join(e['id'] for e in excluded)})."
        )
    adoptable = adoptable_vpc_endpoints(inv)
    if adoptable:
        notes.append(
            f"Found {len(adoptable)} customer VPC endpoint(s) eligible for network adopt — "
            "ask operator; use --skip-endpoints to omit from generated files."
        )
    elif inv.get("vpc_endpoints"):
        notes.append("VPC endpoints present; none marked adoptable (ROSA HCP CP only).")
    if inv.get("transit_gateway_attachments"):
        notes.append(
            f"Found {len(inv['transit_gateway_attachments'])} TGW VPC attachment(s) — "
            "commented stubs in transit_gateway_optional.tf (hub TGW usually network-team owned)."
        )
    if inv.get("flow_logs"):
        notes.append(f"Found {len(inv['flow_logs'])} VPC flow log(s).")

    return GenerateResult(
        mode=mode,
        name_prefix=name_prefix,
        vpc_cidr=vpc_cidr,
        notes=notes,
        unmapped=unmapped,
    )


def write_stack(
    inv: dict[str, Any],
    output_dir: Path,
    *,
    mode: str,
    vpc_cidr: str,
    name_prefix: str,
    include_endpoints: bool,
    include_security_groups: bool,
    include_flow_logs: bool,
    include_tgw: bool,
) -> GenerateResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    result = build_generate_result(
        inv, mode=mode, vpc_cidr=vpc_cidr, name_prefix=name_prefix
    )
    region = inv["source"]["region"]
    copy = mode == "copy"
    cidr_map = _copy_subnet_cidrs(vpc_cidr, inv["subnets"]) if copy else {}

    tags_default = {
        "Project": inv["vpc"].get("tags", {}).get("Project", "rosa"),
        "ManagedBy": "rosa-classic-network-terraform",
    }
    if name_prefix:
        tags_default["NamePrefix"] = name_prefix

    (output_dir / "versions.tf").write_text(
        f'''terraform {{
  required_version = ">= 1.5.7"

  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = ">= 6.51.0"
    }}
  }}
}}

provider "aws" {{
  region = var.aws_region
}}
''',
        encoding="utf-8",
    )

    (output_dir / "variables.tf").write_text(
        '''variable "aws_region" {
  type        = string
  description = "AWS region for network resources."
}

variable "name_prefix" {
  type        = string
  description = "Prefix for Name tags on created resources (copy mode) or labels (adopt mode)."
}

variable "vpc_cidr" {
  type        = string
  description = "VPC CIDR block."
}

variable "common_tags" {
  type        = map(string)
  default     = {}
  description = "Tags applied to all resources."
}
''',
        encoding="utf-8",
    )

    vpc_tags = dict(tags_default)
    vpc_tags["Name"] = name_prefix or inv["vpc"].get("tags", {}).get("Name", "rosa-vpc")

    main_lines = [
        "locals {",
        f"  common_tags = merge(var.common_tags, {json.dumps(tags_default)})",
        "}",
        "",
        "resource \"aws_vpc\" \"this\" {",
        "  cidr_block           = var.vpc_cidr",
        "  enable_dns_hostnames = true",
        "  enable_dns_support   = true",
    ]
    if copy:
        main_lines.append(
            '  tags                 = merge(local.common_tags, { Name = var.name_prefix != "" ? var.name_prefix : "rosa-vpc" })'
        )
    else:
        main_lines.append(f"  tags                 = {_tag_expr_adopt(inv['vpc'].get('tags') or {})}")
    main_lines.extend(["}", ""])

    if not copy and inv.get("internet_gateways"):
        igw = inv["internet_gateways"][0]
        igw_tags = _tag_expr_adopt(igw.get("tags") or {})
        main_lines.extend(
            [
                "resource \"aws_internet_gateway\" \"this\" {",
                "  vpc_id = aws_vpc.this.id",
                f"  tags   = {igw_tags}",
                "}",
                "",
            ]
        )

    subnets_sorted = _sort_subnets(inv["subnets"])
    imports: list[str] = []

    for subnet in subnets_sorted:
        rname = _subnet_resource_name(subnet, copy=copy)
        cidr = cidr_map.get(subnet["id"], subnet["cidr_block"]) if copy else subnet["cidr_block"]
        cidr_hcl = _hcl_string(cidr)
        if copy:
            tag_line = (
                "  tags = merge(local.common_tags, {"
                f' Name = "${{var.name_prefix}}-{_slug(subnet["availability_zone"])}-'
                f"{'public' if subnet['public'] else 'private'}\" "
                "})"
            )
        else:
            tag_line = f"  tags = {_tag_expr_adopt(subnet.get('tags') or {})}"
        main_lines.extend(
            [
                f"resource \"aws_subnet\" \"{rname}\" {{",
                "  vpc_id                  = aws_vpc.this.id",
                f"  availability_zone       = {_hcl_string(subnet['availability_zone'])}",
                f"  cidr_block              = {cidr_hcl}",
                f"  map_public_ip_on_launch = {_hcl_bool(subnet['public'])}",
                tag_line,
                "}",
                "",
            ]
        )

    if not copy and inv.get("nat_gateways"):
        for idx, ng in enumerate(inv["nat_gateways"], start=1):
            sub = next((s for s in inv["subnets"] if s["id"] == ng["subnet_id"]), None)
            sub_res = _subnet_resource_name(sub, copy=False) if sub else "public_a"
            eip_tags = _tag_expr_adopt(ng.get("tags") or {})
            main_lines.extend(
                [
                    f"resource \"aws_eip\" \"nat_{idx}\" {{",
                    "  domain = \"vpc\"",
                    f"  tags   = {eip_tags}",
                    "}",
                    "",
                    f"resource \"aws_nat_gateway\" \"nat_{idx}\" {{",
                    f"  allocation_id = aws_eip.nat_{idx}.id",
                    f"  subnet_id     = aws_subnet.{sub_res}.id",
                    f"  tags          = {eip_tags}",
                    "}",
                    "",
                ]
            )

    if copy:
        main_lines.extend(
            [
                "resource \"aws_internet_gateway\" \"this\" {",
                "  vpc_id = aws_vpc.this.id",
                "  tags   = merge(local.common_tags, { Name = var.name_prefix })",
                "}",
                "",
            ]
        )
        public_sorted = _sort_subnets([s for s in inv["subnets"] if s["public"]])
        for idx, ng in enumerate(inv.get("nat_gateways") or [], start=1):
            pub = next((s for s in inv["subnets"] if s["id"] == ng.get("subnet_id")), None)
            if pub is None and idx <= len(public_sorted):
                pub = public_sorted[idx - 1]
            sub_res = _subnet_resource_name(pub, copy=True) if pub else f"public_{idx}"
            main_lines.extend(
                [
                    f"resource \"aws_eip\" \"nat_{idx}\" {{",
                    "  domain = \"vpc\"",
                    f"  tags   = merge(local.common_tags, {{ Name = \"${{var.name_prefix}}-nat-eip-{idx}\" }})",
                    "}",
                    "",
                    f"resource \"aws_nat_gateway\" \"nat_{idx}\" {{",
                    f"  allocation_id = aws_eip.nat_{idx}.id",
                    f"  subnet_id     = aws_subnet.{sub_res}.id",
                    f"  tags          = merge(local.common_tags, {{ Name = \"${{var.name_prefix}}-nat-{idx}\" }})",
                    "}",
                    "",
                ]
            )
        _append_rosa_routes(main_lines, imports, inv, copy=True, name_prefix=name_prefix)

    if not copy:
        imports.append("import {")
        imports.append("  to = aws_vpc.this")
        imports.append(f"  id = {_hcl_string(inv['vpc']['id'])}")
        imports.append("}")
        imports.append("")
        if inv.get("internet_gateways"):
            imports.append("import {")
            imports.append("  to = aws_internet_gateway.this")
            imports.append(f"  id = {_hcl_string(inv['internet_gateways'][0]['id'])}")
            imports.append("}")
            imports.append("")
        for subnet in subnets_sorted:
            rname = _subnet_resource_name(subnet, copy=False)
            imports.append("import {")
            imports.append(f"  to = aws_subnet.{rname}")
            imports.append(f"  id = {_hcl_string(subnet['id'])}")
            imports.append("}")
            imports.append("")
        for idx, ng in enumerate(inv.get("nat_gateways") or [], start=1):
            eip_id = ng.get("eip_allocation_id")
            if eip_id:
                imports.append("import {")
                imports.append(f"  to = aws_eip.nat_{idx}")
                imports.append(f"  id = {_hcl_string(eip_id)}")
                imports.append("}")
                imports.append("")
            imports.append("import {")
            imports.append(f"  to = aws_nat_gateway.nat_{idx}")
            imports.append(f"  id = {_hcl_string(ng['id'])}")
            imports.append("}")
            imports.append("")

        if inv.get("route_tables"):
            _append_rosa_routes(main_lines, imports, inv, copy=False, name_prefix=name_prefix)

    wiring = inv["rosa_hcp_wiring"]
    if copy:
        priv_refs = []
        pub_refs = []
        for subnet in _sort_subnets([s for s in inv["subnets"] if not s["public"]]):
            priv_refs.append(f"aws_subnet.{_subnet_resource_name(subnet, copy=True)}.id")
        for subnet in _sort_subnets([s for s in inv["subnets"] if s["public"]]):
            pub_refs.append(f"aws_subnet.{_subnet_resource_name(subnet, copy=True)}.id")
        ordered_expr = "concat([" + ", ".join(priv_refs) + "]"
        if pub_refs and not inv["source"]["private_cluster"]:
            ordered_expr += ", [" + ", ".join(pub_refs) + "]"
        ordered_expr += ")"
        by_az_lines = []
        for subnet in _sort_subnets([s for s in inv["subnets"] if not s["public"]]):
            by_az_lines.append(
                f"    {_hcl_string(subnet['availability_zone'])} = aws_subnet."
                f"{_subnet_resource_name(subnet, copy=True)}.id"
            )
        outputs_subnet_ids = ordered_expr
    else:
        by_az_lines = [
            f"    {_hcl_string(az)} = {_hcl_string(sid)}"
            for az, sid in wiring["private_subnet_ids_by_az"].items()
        ]
        outputs_subnet_ids = json.dumps(wiring["aws_subnet_ids"])

    (output_dir / "main.tf").write_text("\n".join(main_lines), encoding="utf-8")

    (output_dir / "outputs.tf").write_text(
        f'''output "vpc_id" {{
  value = aws_vpc.this.id
}}

output "vpc_cidr" {{
  value = aws_vpc.this.cidr_block
}}

output "aws_subnet_ids" {{
  description = "Subnet IDs in ROSA HCP order (private per AZ, then public per AZ when not private)."
  value       = {outputs_subnet_ids}
}}

output "private_subnet_ids_by_az" {{
  value = {{
{chr(10).join(by_az_lines)}
  }}
}}
''',
        encoding="utf-8",
    )

    tfvars = f'''aws_region  = {_hcl_string(region)}
name_prefix = {_hcl_string(name_prefix)}
vpc_cidr    = {_hcl_string(vpc_cidr)}

common_tags = {{
  Project = {_hcl_string(tags_default.get("Project", "rosa"))}
}}
'''
    (output_dir / "terraform.tfvars").write_text(tfvars, encoding="utf-8")

    if not copy:
        (output_dir / "imports.tf").write_text("\n".join(imports) + "\n", encoding="utf-8")
    elif (output_dir / "imports.tf").exists():
        (output_dir / "imports.tf").unlink()

    inv_md = [
        f"# Network inventory: `{inv['source']['cluster_name']}`",
        "",
        f"- VPC `{inv['vpc']['id']}` — `{inv['vpc']['cidr_block']}`",
        f"- Mode: **{mode}**",
        "",
        "## Subnets",
        "",
    ]
    for s in subnets_sorted:
        inv_md.append(
            f"- `{s['id']}` — {s['availability_zone']} — `{s['cidr_block']}` — "
            f"{'public' if s['public'] else 'private'}"
        )
    inv_md.extend(["", "## ROSA HCP wiring", ""])
    inv_md.append(f"`aws_subnet_ids`: `{', '.join(wiring['aws_subnet_ids'])}`")
    if result.unmapped:
        inv_md.extend(["", "## Follow-up", ""])
        inv_md.extend(f"- {u}" for u in result.unmapped)
    (output_dir / "INVENTORY.md").write_text("\n".join(inv_md) + "\n", encoding="utf-8")

    outputs_json = {
        "vpc_id": inv["vpc"]["id"] if not copy else "${aws_vpc.this.id}",
        "vpc_cidr": vpc_cidr,
        "aws_subnet_ids": wiring["aws_subnet_ids"] if not copy else "see terraform outputs after apply",
        "private_subnet_ids_by_az": wiring["private_subnet_ids_by_az"],
        "mode": mode,
        "classic_subnet_ids": [s["id"] for s in inv["subnets"]],
        "cluster_state": inv["source"].get("cluster_state"),
    }
    (output_dir / "network-outputs.json").write_text(
        json.dumps(outputs_json, indent=2) + "\n", encoding="utf-8"
    )

    optional_tgw = output_dir / "transit_gateway_optional.tf"
    if include_tgw:
        tgw_body = generate_transit_gateway_optional_tf(
            inv, copy=copy, name_prefix=name_prefix
        )
        if tgw_body.strip():
            optional_tgw.write_text(tgw_body, encoding="utf-8")
            inv_md.extend(
                [
                    "",
                    "## Transit Gateway",
                    "",
                    "See **`transit_gateway_optional.tf`** (commented). Coordinate with the team that "
                    "owns the shared TGW before attachment or hub route changes.",
                ]
            )
            (output_dir / "INVENTORY.md").write_text("\n".join(inv_md) + "\n", encoding="utf-8")
        elif optional_tgw.is_file():
            optional_tgw.unlink()

    endpoints_adopt = output_dir / "vpc_endpoints_adopt.tf"
    if include_endpoints and mode == "adopt":
        body = generate_vpc_endpoints_adopt_tf(inv, mode=mode)
        if body.strip():
            endpoints_adopt.write_text(body, encoding="utf-8")
            inv_md.extend(
                [
                    "",
                    "## VPC endpoints",
                    "",
                    "Customer endpoints in **`vpc_endpoints_adopt.tf`**. ROSA HCP control-plane VPCE "
                    "is excluded — ROSA manages that endpoint.",
                ]
            )
            (output_dir / "INVENTORY.md").write_text("\n".join(inv_md) + "\n", encoding="utf-8")
        elif endpoints_adopt.is_file():
            endpoints_adopt.unlink()
    elif endpoints_adopt.is_file():
        endpoints_adopt.unlink()

    _ = (include_security_groups, include_flow_logs)
    from stack_readme import refresh_after_network_write

    refresh_after_network_write(
        output_dir,
        mode=mode,
        cluster_name=str(inv["source"]["cluster_name"]),
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--mode", choices=("adopt", "copy"), required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("network"))
    parser.add_argument("--vpc-cidr", default="")
    parser.add_argument("--name-prefix", default="")
    parser.add_argument("--name-suffix", default="-hcp")
    parser.add_argument("--skip-endpoints", action="store_true")
    parser.add_argument("--skip-security-groups", action="store_true")
    parser.add_argument("--skip-flow-logs", action="store_true")
    parser.add_argument("--skip-tgw", action="store_true")
    args = parser.parse_args()

    if args.dry_run == args.write:
        raise SystemExit("Specify exactly one of --dry-run or --write.")

    inv = json.loads(args.inventory.read_text(encoding="utf-8"))
    if inv.get("schema_version") != 1:
        raise SystemExit(f"Unsupported inventory schema_version {inv.get('schema_version')}")

    default_prefix = inv["source"]["cluster_name"]
    if args.mode == "copy" and not args.name_prefix:
        name_prefix = default_prefix + args.name_suffix
    else:
        name_prefix = args.name_prefix or default_prefix

    vpc_cidr = args.vpc_cidr or inv["vpc"]["cidr_block"]

    result = build_generate_result(
        inv, mode=args.mode, vpc_cidr=vpc_cidr, name_prefix=name_prefix
    )
    if args.dry_run:
        print(format_dry_run(inv, result))
        return

    write_stack(
        inv,
        args.output_dir,
        mode=args.mode,
        vpc_cidr=vpc_cidr,
        name_prefix=name_prefix,
        include_endpoints=not args.skip_endpoints,
        include_security_groups=not args.skip_security_groups,
        include_flow_logs=not args.skip_flow_logs,
        include_tgw=not args.skip_tgw,
    )
    print(f"Wrote network Terraform to {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
