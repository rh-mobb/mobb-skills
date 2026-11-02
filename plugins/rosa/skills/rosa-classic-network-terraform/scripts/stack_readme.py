#!/usr/bin/env python3
# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0
"""Generate README.md (and stack metadata) for MOBB ROSA Terraform output directories."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

StackKind = Literal[
    "hcp_adopt",
    "classic_hcp",
    "combined_hcp",
    "network_only",
]

META_FILE = ".mobb-stack.json"


@dataclass
class StackMeta:
    kind: StackKind
    aws_region: str
    cluster_name: str = ""
    cluster_id: str = ""
    module_version: str = "1.7.6"
    source_cluster_name: str = ""
    target_cluster_name: str = ""
    account_role_prefix: str = ""
    network_mode: str = ""
    notes: list[str] = field(default_factory=list)
    unmapped: list[str] = field(default_factory=list)
    extra_sections: list[str] = field(default_factory=list)

    def write(self, stack_dir: Path) -> None:
        stack_dir = stack_dir.resolve()
        stack_dir.mkdir(parents=True, exist_ok=True)
        (stack_dir / META_FILE).write_text(
            json.dumps(asdict(self), indent=2) + "\n",
            encoding="utf-8",
        )

    @classmethod
    def load(cls, stack_dir: Path) -> StackMeta | None:
        path = stack_dir.resolve() / META_FILE
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        from dataclasses import fields

        allowed = {f.name for f in fields(cls)}
        kwargs = {k: data[k] for k in allowed if k in data}
        if "kind" not in kwargs or "aws_region" not in kwargs:
            return None
        return cls(**kwargs)


def has_network_stack(stack_dir: Path) -> bool:
    return (stack_dir / "network" / "main.tf").is_file()


def write_stack_readme(stack_dir: Path, meta: StackMeta) -> Path:
    """Write README.md at stack root; refreshes split-stack section from disk."""
    stack_dir = stack_dir.resolve()
    meta.write(stack_dir)
    has_net = has_network_stack(stack_dir)
    lines = _readme_lines(meta, has_network=has_net, for_network_subdir=False)
    path = stack_dir / "README.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_network_subdir_readme(network_dir: Path, *, mode: str, cluster_name: str) -> Path:
    """README for a network/ Terraform root (split stack or standalone)."""
    network_dir = network_dir.resolve()
    stack_root = network_dir.parent if network_dir.name == "network" else network_dir
    meta = StackMeta.load(stack_root) if network_dir.name == "network" else None
    region = meta.aws_region if meta else "us-east-1"
    if meta:
        lines = _readme_lines(meta, has_network=True, for_network_subdir=True, network_mode=mode)
    else:
        lines = _standalone_network_readme(
            cluster_name=cluster_name,
            aws_region=region,
            mode=mode,
        )
    path = network_dir / "README.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def refresh_after_network_write(network_dir: Path, *, mode: str, cluster_name: str) -> None:
    """Update network/README.md, parent README/Makefile when stack metadata exists."""
    from stack_makefile import write_split_stack_makefile

    network_dir = network_dir.resolve()
    write_network_subdir_readme(network_dir, mode=mode, cluster_name=cluster_name)
    if network_dir.name != "network":
        return
    stack_root = network_dir.parent
    meta = StackMeta.load(stack_root)
    if meta:
        meta.network_mode = mode
        write_stack_readme(stack_root, meta)
        write_split_stack_makefile(stack_root, aws_region=meta.aws_region, has_network=True)


def _prerequisites(region: str, *, rhcs: bool) -> list[str]:
    lines = [
        "## Prerequisites",
        "",
        "- [ROSA CLI](https://docs.openshift.com/rosa/) — `rosa login` (and OCM token for cluster stacks)",
        f"- AWS credentials with access to **`{region}`** (read for plan; write for apply)",
        "- [Terraform](https://developer.hashicorp.com/terraform) ≥ 1.5",
    ]
    if rhcs:
        lines.append("- Set `RHCS_TOKEN` from `rosa token` before cluster `plan`/`apply`")
    lines.append("")
    return lines


def _make_section(has_network: bool) -> list[str]:
    lines = [
        "## Makefile shortcuts",
        "",
        "From this directory (stack root):",
        "",
        "```bash",
        "make help",
        "make init",
        "make plan",
        "make apply   # review plan first; adopt binds import state",
        "```",
        "",
    ]
    if has_network:
        lines.extend(
            [
                "Split stack order: **`make apply`** runs **network → cluster**; **`make destroy`** runs **cluster → network**.",
                "",
                "| Target | Purpose |",
                "|--------|---------|",
                "| `make network-plan` / `make network-apply` | VPC/subnets only (`network/`) |",
                "| `make cluster-plan` / `make cluster-apply` | ROSA HCP module (this root) |",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "Cluster-only stack (no `network/` yet). After adding `network/`, re-run network generation to refresh this README and Makefile.",
                "",
            ]
        )
    return lines


def _manual_cluster_steps(has_network: bool) -> list[str]:
    lines = [
        "## Manual Terraform (cluster root)",
        "",
        "Set **`RHCS_TOKEN`** in the environment (from `rosa token`) before plan/apply.",
        "",
        "```bash",
        "export AWS_DEFAULT_REGION=<region>",
        "terraform init",
        "terraform fmt",
        "terraform validate",
        "terraform plan",
        "terraform apply",
        "```",
        "",
    ]
    if has_network:
        lines.extend(
            [
                "Run **`network/`** init/plan/apply first when adopting both stacks (see `network/README.md`).",
                "",
            ]
        )
    return lines


def _manual_network_steps(region: str) -> list[str]:
    return [
        "## Manual Terraform (`network/`)",
        "",
        "```bash",
        "cd network",
        f"export AWS_DEFAULT_REGION={region}",
        "terraform init",
        "terraform fmt",
        "terraform validate",
        "terraform plan",
        "terraform apply",
        "```",
        "",
    ]


def _readme_lines(
    meta: StackMeta,
    *,
    has_network: bool,
    for_network_subdir: bool,
    network_mode: str = "",
) -> list[str]:
    mode = network_mode or meta.network_mode or "adopt"
    if for_network_subdir:
        return _network_subdir_lines(meta, mode=mode)

    title_name = meta.cluster_name or meta.target_cluster_name or "ROSA stack"
    lines: list[str] = []

    if meta.kind == "hcp_adopt":
        lines.extend(
            [
                f"# Terraform adopt: `{title_name}` (ROSA HCP)",
                "",
                f"- OCM cluster ID: `{meta.cluster_id}`",
                f"- Module: [`terraform-redhat/rosa-hcp/rhcs`](https://registry.terraform.io/modules/terraform-redhat/rosa-hcp/rhcs/latest) `{meta.module_version}`",
                f"- Region: **{meta.aws_region}**",
                "",
                "Import an **existing** ROSA HCP cluster into Terraform (`create_* = false` on IAM/OIDC/operator roles).",
                "",
            ]
        )
    elif meta.kind == "classic_hcp":
        lines.extend(
            [
                f"# Terraform: Classic → HCP `{meta.target_cluster_name}`",
                "",
                f"- Source Classic cluster: `{meta.source_cluster_name}` (`{meta.cluster_id}`)",
                f"- Module: [`terraform-redhat/rosa-hcp/rhcs`](https://registry.terraform.io/modules/terraform-redhat/rosa-hcp/rhcs/latest) `{meta.module_version}`",
                f"- Region: **{meta.aws_region}**",
                f"- IAM prefix: `{meta.account_role_prefix}` (new HCP roles on apply)",
                "",
                "Creates a **new** HCP cluster. Fill subnet IDs in `terraform.tfvars` or generate **`network/`** and merge wiring.",
                "",
            ]
        )
    elif meta.kind == "combined_hcp":
        lines.extend(
            [
                f"# Terraform: combined network + HCP `{title_name}`",
                "",
                f"- Module: [`terraform-redhat/rosa-hcp/rhcs`](https://registry.terraform.io/modules/terraform-redhat/rosa-hcp/rhcs/latest) `{meta.module_version}`",
                f"- Region: **{meta.aws_region}**",
                "",
                "Single root: `module.network` (local `./network`) then `module.rosa_hcp`. One `terraform apply` after VPC is planned.",
                "",
            ]
        )

    lines.extend(_prerequisites(meta.aws_region, rhcs=True))

    if meta.kind != "combined_hcp":
        lines.extend(_make_section(has_network))
    else:
        lines.extend(
            [
                "## Apply",
                "",
                "Single Terraform root (network module + HCP module). Set **`RHCS_TOKEN`** from `rosa token`, then:",
                "",
                "```bash",
                f"export AWS_DEFAULT_REGION={meta.aws_region}",
                "terraform init && terraform plan && terraform apply",
                "```",
                "",
            ]
        )

    if meta.kind != "combined_hcp":
        lines.extend(_manual_cluster_steps(has_network))

    if has_network:
        lines.extend(
            [
                "## Network stack (`network/`)",
                "",
                f"- Mode: **{mode}** — see [`network/README.md`](network/README.md) and `network/INVENTORY.md`.",
                "- Adopt: imports in `network/imports.tf`. Copy: new VPC CIDR; no imports.",
                "- ROSA HCP **control-plane VPCE** is never adopted in `network/`. Customer VPC endpoints only when generated.",
                "",
            ]
        )

    if meta.kind == "hcp_adopt":
        lines.extend(
            [
                "## Adopt notes",
                "",
                "1. Review `imports.tf` — adjust import IDs if the provider rejects them.",
                "2. Expect plan drift on read-only API fields (`state`, URLs).",
                "3. Node pool import IDs use `{cluster_id},{pool_name}`.",
                "4. Do not commit `RHCS_TOKEN` or production admin passwords.",
                "",
            ]
        )
    elif meta.kind == "classic_hcp":
        lines.extend(
            [
                "## Migration notes",
                "",
                "See **`MIGRATION.md`** for translations, IdPs, and unmapped fields.",
                "",
                "Review **`terraform.tfvars`**: admin password, CIDRs, `aws_subnet_ids`, machine pools.",
                "",
            ]
        )

    if meta.notes:
        lines.extend(["## Generator notes", ""])
        lines.extend(f"- {n}" for n in meta.notes)
        lines.append("")

    if meta.unmapped:
        lines.extend(["## Manual follow-up", ""])
        lines.extend(f"- {u}" for u in meta.unmapped)
        lines.append("")

    for section in meta.extra_sections:
        if section.strip():
            lines.append(section.rstrip())
            lines.append("")

    lines.extend(
        [
            "## Related MOBB skills",
            "",
            "- `/rosa:hcp-adopt`, `/rosa:classic-to-hcp`, `/rosa:classic-to-hcp-full`",
            "- `plugins/rosa/terraform.md` in [mobb-skills](https://github.com/rh-mobb/mobb-skills)",
            "",
        ]
    )
    return lines


def _network_subdir_lines(meta: StackMeta, *, mode: str) -> list[str]:
    name = meta.cluster_name or meta.source_cluster_name or "cluster"
    lines = [
        f"# Network Terraform (`network/`) — `{name}`",
        "",
        f"- Region: **{meta.aws_region}**",
        f"- Mode: **{mode}**",
        "",
        "AWS VPC/subnets/IGW/NAT/routes for ROSA. This directory is a **separate Terraform root** from the cluster stack in the parent folder.",
        "",
        "See **[../README.md](../README.md)** for split-stack apply/destroy order and Makefile targets.",
        "",
    ]
    lines.extend(_prerequisites(meta.aws_region, rhcs=False))
    lines.extend(_manual_network_steps(meta.aws_region))
    lines.extend(
        [
            "## Files",
            "",
            "- `INVENTORY.md` — discovered resources and wiring",
            "- `network-outputs.json` — subnet order for `merge_hcp_stack.py`",
            "- `imports.tf` — adopt mode only",
            "",
        ]
    )
    return lines


def _standalone_network_readme(*, cluster_name: str, aws_region: str, mode: str) -> list[str]:
    lines = [
        f"# Network Terraform — `{cluster_name}`",
        "",
        f"- Region: **{aws_region}**",
        f"- Mode: **{mode}**",
        "",
        "Standalone network stack (no cluster root in parent). Wire outputs into HCP `terraform.tfvars` or run **`merge_hcp_stack.py`**.",
        "",
    ]
    lines.extend(_prerequisites(aws_region, rhcs=False))
    lines.extend(_manual_network_steps(aws_region))
    lines.extend(
        [
            "## Files",
            "",
            "- `INVENTORY.md`, `network-outputs.json`, `imports.tf` (adopt)",
            "",
        ]
    )
    return lines
