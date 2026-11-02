#!/usr/bin/env python3
# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0
"""Copy a generated Terraform stack to examples/, strip Terraform cache, anonymize identifiers."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

SKIP_DIR_NAMES = {".terraform", "__pycache__"}
SKIP_FILE_NAMES = {".terraform.lock.hcl"}

# Order matters: longer / more specific strings first.
REPLACEMENTS: list[tuple[str, str]] = [
    ("rosa-mta-classic-hcp", "demo-classic-hcp"),
    ("rosa-mta-hcp", "demo-hcp-public"),
    ("rosa-mta-classic", "demo-classic"),
    ("rosa-mta", "demo-workshop"),
    ("2to3km7cf2sr75o59veptkt6ua7dbc1o", "01234567-89ab-cdef-0123-456789abcd01"),
    ("2to3jese7egfaduk17hvpoh6hlnktc8v", "0demooidc000000000000000000000000"),
    ("enlm.p3.openshiftapps.com", "demo.p3.openshiftapps.com"),
    ("apps.rosa.demo-hcp-public", "apps.demo-hcp-public"),
    ("api.rosa.demo-hcp-public", "api.demo-hcp-public"),
    (
        "console-openshift-console.apps.rosa.demo-hcp-public",
        "console-openshift-console.apps.demo-hcp-public",
    ),
    ("2toldtrl7rkkjqcafq9db5jgutqn98u1", "01234567-89ab-cdef-0123-456789abcd01"),
    ("2to2df6dm3d11er92hnhh6d6j6n4cchd", "01234567-89ab-cdef-0123-456789abcdef"),
    ("2tolcs46935ad3i4agd47vbhs5qgnnh0", "0demooidc000000000000000000000000"),
    ("2JsvywBGBOA76M26WQyfUl1yel3", "00000000000000000000000000000000"),
    ("808082629126", "111111111111"),
    ("arn:aws:iam::111111111111:user/paulczar", "arn:aws:iam::111111111111:user/demo-operator"),
    ("paulczar", "demo-operator"),
    ("vpc-0322fff4145fb0c7b", "vpc-0a1b2c3d4e5f67890"),
    ("subnet-0eb14229cf45874cf", "subnet-0aaa1111private2a"),
    ("subnet-0ed28dc2f1a4d87e7", "subnet-0bbb2222public2a"),
    ("igw-0805329be6f4458a1", "igw-0example00000001"),
    ("nat-0e3db1639d7bdc464", "nat-0example00000001"),
    ("eipalloc-05a58ac71a0ed941f", "eipalloc-0example00001"),
    ("rtb-02a2791d8c27ed465", "rtb-0example00000001"),
    ("b451b5f8-8685-4b2f-bc87-991dc5c28f48", "00000000-0000-4000-8000-000000000001"),
    # HCP adopt skill fixture (demo-hcp-public) — keep in sync with fixtures/demo-hcp-public/
    ("vpc-03d8bae11cf90f803", "vpc-0a1b2c3d4e5f67890"),
    ("subnet-067fce73d1c149535", "subnet-0aaa1111private2a"),
    ("subnet-000183d72b45c3705", "subnet-0bbb2222public2a"),
    ("igw-0216575ef34f3a1bd", "igw-0example00000001"),
    ("nat-00ca511703cf7a196", "nat-0example00000001"),
    ("eipalloc-0d62d70bea68f5a2b", "eipalloc-0example00001"),
    ("rtb-08635b9a117308eae", "rtb-0example00000002"),
    ("rtb-04ac0d9744fb14a9a", "rtb-0example00000003"),
    ("rtb-00d107fbc8ec7a86c", "rtb-0example00000004"),
    ("vpce-0a10cfa748329e4eb", "vpce-0example00000001"),
    ("vpce-0eee42943025aef54", "vpce-0example00000002"),
    ("vpce-0a797abe8a76d255f", "vpce-0example00000003"),
    ("vpce-035f175b72d02ff2c", "vpce-0example00000004"),
    ("vpce-044cc407a78058d26", "vpce-0example00000005"),
    ("vpce-svc-050aa532764c11a72", "vpce-svc-00000000000000001"),
    ("sg-017ae12eb44e92a37", "sg-0example00000001"),
    ("sg-0e9216ce7cea4ef9b", "sg-0example00000002"),
    ("sg-0b7167e48a07def65", "sg-0example00000003"),
]


def _should_skip_path(path: Path) -> bool:
    return any(part in SKIP_DIR_NAMES for part in path.parts)


def _anonymize_text(text: str) -> str:
    out = text
    for old, new in REPLACEMENTS:
        out = out.replace(old, new)
    return out


def copy_stack(source: Path, dest: Path, *, skip_collect: bool) -> None:
    source = source.resolve()
    dest = dest.resolve()
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    for item in source.rglob("*"):
        if _should_skip_path(item.relative_to(source)):
            continue
        rel = item.relative_to(source)
        if skip_collect and rel.parts and rel.parts[0] == "_collect":
            continue
        if item.is_dir():
            continue
        if item.name in SKIP_FILE_NAMES:
            continue
        if item.suffix in {".pyc", ".tfstate", ".tfstate.backup"}:
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            raw = item.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        target.write_text(_anonymize_text(raw), encoding="utf-8")


PROVENANCE: dict[str, str] = {
    "hcp-adopt-split-stack": """\
# Example: HCP adopt (split stack)

| Field | Value |
|-------|--------|
| **Skills** | `rosa-hcp-adopt-terraform`, `rosa-classic-network-terraform` |
| **Command** | `/rosa:hcp-adopt` |
| **Workflow** | Live cluster JSON → `hcp_adopt_to_tf.py --write` + `network_to_tf.py --mode adopt --write` → `network/` + cluster root |
| **Scenario** | Public ROSA HCP cluster with BYO VPC (single-AZ); import blocks, Makefile, README |

Identifiers and ARNs are **fictional** (account `111111111111`). Do not apply against production without replacing values from your environment.

Discovery JSON under `_collect/` is omitted — regenerate locally with `discover_cluster_network.py`.
""",
    "classic-to-hcp-full-combined": """\
# Example: Classic → HCP (combined stack)

| Field | Value |
|-------|--------|
| **Skills** | `rosa-classic-to-hcp-terraform`, `rosa-classic-network-terraform` |
| **Command** | `/rosa:classic-to-hcp-full` |
| **Workflow** | Classic JSON + network discover → `classic_to_hcp.py --write` + `network_to_tf.py --mode copy` + `combine_stack.py` |
| **Scenario** | New VPC (`network/` copy) + greenfield HCP module in one root (`module.network` → `module.rosa_hcp`) |

Identifiers are **fictional**. Review `terraform.tfvars` (admin password, CIDRs) before any apply.

Supporting JSON in `json/` is anonymized **skill fixture** data (see `json/README.md`), not live exports.
""",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--dest", type=Path, required=True)
    parser.add_argument(
        "--provenance",
        choices=sorted(PROVENANCE.keys()),
        required=True,
    )
    parser.add_argument(
        "--skip-collect",
        action="store_true",
        help="Omit _collect/ (live discovery JSON)",
    )
    args = parser.parse_args()
    copy_stack(args.source, args.dest, skip_collect=args.skip_collect)
    (args.dest / "EXAMPLE.md").write_text(
        PROVENANCE[args.provenance] + "\n",
        encoding="utf-8",
    )
    readme = args.dest / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        if "EXAMPLE.md" not in text.split("\n", 1)[0]:
            readme.write_text(
                "> **Committed example** — provenance in [EXAMPLE.md](EXAMPLE.md). "
                "IDs and ARNs are fictional.\n\n" + text,
                encoding="utf-8",
            )
    print(f"Published anonymized example to {args.dest.resolve()}")


if __name__ == "__main__":
    main()
