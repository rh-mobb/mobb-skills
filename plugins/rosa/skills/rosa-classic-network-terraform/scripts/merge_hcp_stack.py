#!/usr/bin/env python3
# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0
"""Merge network-outputs.json into HCP cluster terraform.tfvars."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def _hcl_list(values: list[str]) -> str:
    inner = ", ".join(f'"{v}"' for v in values)
    return f"[{inner}]"


def merge_tfvars(
    tfvars_text: str,
    *,
    vpc_cidr: str,
    aws_subnet_ids: list[str],
    private_by_az: dict[str, str],
    allow_subnet_reuse: bool,
    classic_subnet_ids: list[str],
    cluster_state: str | None,
    mode: str,
) -> str:
    overlap = set(aws_subnet_ids) & set(classic_subnet_ids)
    if overlap and not allow_subnet_reuse:
        if cluster_state in (None, "ready", "installing", "pending"):
            raise SystemExit(
                "Refusing to merge Classic subnet IDs into HCP tfvars while Classic "
                f"cluster appears active (state={cluster_state!r}). Overlap: {sorted(overlap)}. "
                "Use copy-mode network Terraform for a new VPC, or pass --allow-subnet-reuse "
                "only when Classic is decommissioned."
            )
        if mode == "copy":
            pass  # copy mode should use new IDs after apply; static merge uses placeholders

    out = tfvars_text
    out = re.sub(
        r'^vpc_cidr\s*=.*$',
        f'vpc_cidr = "{vpc_cidr}"',
        out,
        count=1,
        flags=re.MULTILINE,
    )
    out = re.sub(
        r'^aws_subnet_ids\s*=.*$',
        f"aws_subnet_ids = {_hcl_list(aws_subnet_ids)}",
        out,
        count=1,
        flags=re.MULTILINE,
    )

    for az, subnet_id in private_by_az.items():
        pattern = (
            r'(machine_pools\s*=\s*\{[^}]*?#\s*private subnet AZ '
            + re.escape(az)
            + r'[^\n]*\n\s*subnet_id\s*=\s*)""'
        )
        if re.search(pattern, out, flags=re.DOTALL):
            out = re.sub(
                pattern,
                rf'\1"{subnet_id}"',
                out,
                count=1,
                flags=re.DOTALL,
            )

    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--network-outputs", type=Path, required=True)
    parser.add_argument("--hcp-tfvars", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--allow-subnet-reuse", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    net = json.loads(args.network_outputs.read_text(encoding="utf-8"))
    tfvars = args.hcp_tfvars.read_text(encoding="utf-8")

    aws_subnet_ids = net.get("aws_subnet_ids")
    if not isinstance(aws_subnet_ids, list) or not aws_subnet_ids:
        raise SystemExit("network-outputs.json missing aws_subnet_ids list")

    merged = merge_tfvars(
        tfvars,
        vpc_cidr=str(net["vpc_cidr"]),
        aws_subnet_ids=[str(x) for x in aws_subnet_ids],
        private_by_az={k: str(v) for k, v in net.get("private_subnet_ids_by_az", {}).items()},
        allow_subnet_reuse=args.allow_subnet_reuse,
        classic_subnet_ids=[str(x) for x in net.get("classic_subnet_ids", [])],
        cluster_state=net.get("cluster_state"),
        mode=str(net.get("mode", "")),
    )

    if args.dry_run:
        print(merged)
        return

    target = args.output or args.hcp_tfvars
    target.write_text(merged, encoding="utf-8")
    print(f"Wrote merged tfvars to {target.resolve()}")


if __name__ == "__main__":
    main()
