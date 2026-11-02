#!/usr/bin/env python3
# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0
"""Write root main.tf wiring network submodule outputs into rosa-hcp module (copy VPC + HCP)."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def write_combined_root(
    stack_dir: Path,
    *,
    rosa_hcp_version: str,
    machine_pools_from_tfvars: bool = True,
) -> None:
    """Expect stack_dir/network/ submodule and cluster variables.tf + terraform.tfvars at stack_dir."""
    main = f'''module "network" {{
  source = "./network"

  aws_region  = var.aws_region
  name_prefix = var.network_name_prefix
  vpc_cidr    = var.network_vpc_cidr
  common_tags = var.network_common_tags
}}

locals {{
  machine_pools_wired = {{
    for k, v in var.machine_pools : k => merge(v, {{
      subnet_id = try(v.subnet_id, "") != "" ? v.subnet_id : try(
        module.network.private_subnet_ids_by_az[
          var.aws_availability_zones[tonumber(regex("-([0-9]+)$", v.name)[0]) - 1]
        ],
        try(v.subnet_id, "")
      )
    }})
  }}
}}

module "rosa_hcp" {{
  source  = "terraform-redhat/rosa-hcp/rhcs"
  version = "{rosa_hcp_version}"

  depends_on = [module.network]

  cluster_name      = var.cluster_name
  openshift_version = var.openshift_version
  channel           = var.channel

  aws_subnet_ids         = module.network.aws_subnet_ids
  aws_availability_zones = var.aws_availability_zones

  private                          = var.private
  default_ingress_listening_method = var.default_ingress_listening_method

  machine_cidr = var.machine_cidr
  pod_cidr     = var.pod_cidr
  service_cidr = var.service_cidr
  host_prefix  = var.host_prefix

  replicas             = var.replicas
  compute_machine_type = var.compute_machine_type
  worker_disk_size     = var.worker_disk_size

  create_account_roles  = true
  account_role_prefix   = var.account_role_prefix
  create_oidc           = true
  managed_oidc          = true
  create_operator_roles = true
  operator_role_prefix  = var.operator_role_prefix

  admin_credentials_username = var.admin_credentials_username
  admin_credentials_password = var.admin_credentials_password

  machine_pools = local.machine_pools_wired
  identity_providers = merge(var.identity_providers, local.identity_providers_classic)
}}

output "network_vpc_id" {{
  value = module.network.vpc_id
}}

output "network_aws_subnet_ids" {{
  value = module.network.aws_subnet_ids
}}

output "hcp_cluster_id" {{
  value = module.rosa_hcp.cluster_id
}}
'''
    (stack_dir / "main.tf").write_text(main, encoding="utf-8")

    extra_vars = '''

variable "aws_region" {
  type        = string
  description = "AWS region for VPC and cluster."
}

variable "network_name_prefix" {
  type        = string
  description = "Name prefix for copied VPC resources."
}

variable "network_vpc_cidr" {
  type        = string
  description = "CIDR for the new VPC (copy mode)."
}

variable "network_common_tags" {
  type        = map(string)
  default     = {}
}
'''
    vars_path = stack_dir / "variables.tf"
    text = vars_path.read_text(encoding="utf-8")
    if "network_name_prefix" not in text:
        vars_path.write_text(text.rstrip() + extra_vars, encoding="utf-8")

    versions = stack_dir / "versions.tf"
    if versions.exists():
        vtext = versions.read_text(encoding="utf-8")
        vtext = re.sub(
            r'provider "aws" \{[^}]*\}',
            'provider "aws" {\n  region = var.aws_region\n}',
            vtext,
            count=1,
            flags=re.DOTALL,
        )
        if 'provider "rhcs"' not in vtext:
            vtext = vtext.rstrip() + '''

provider "rhcs" {
  # Set RHCS_TOKEN in the environment.
}
'''
        versions.write_text(vtext + "\n", encoding="utf-8")

    net_versions = stack_dir / "network" / "versions.tf"
    if net_versions.exists():
        ntext = net_versions.read_text(encoding="utf-8")
        lines = []
        skip = False
        for line in ntext.splitlines():
            if line.strip().startswith('provider "aws"'):
                skip = True
                continue
            if skip:
                if line.strip() == "}":
                    skip = False
                continue
            lines.append(line)
        net_versions.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_stack_tfvars(
    stack_dir: Path,
    *,
    aws_region: str,
    network_name_prefix: str,
    network_vpc_cidr: str,
    machine_cidr: str,
) -> None:
    tfvars = stack_dir / "terraform.tfvars"
    body = tfvars.read_text(encoding="utf-8")
    if "network_vpc_cidr" not in body:
        prefix = f'''
aws_region          = "{aws_region}"
network_name_prefix = "{network_name_prefix}"
network_vpc_cidr    = "{network_vpc_cidr}"
network_common_tags = {{
  Project = "rosa-mta"
}}

'''
        body = prefix + body
    body = re.sub(
        r'^machine_cidr\s*=.*$',
        f'machine_cidr = "{machine_cidr}"',
        body,
        count=1,
        flags=re.MULTILINE,
    )
    body = re.sub(
        r'^vpc_cidr\s*=.*$',
        'vpc_cidr = "" # optional; combined stack uses network_vpc_cidr + module.network',
        body,
        count=1,
        flags=re.MULTILINE,
    )
    body = re.sub(
        r'^aws_subnet_ids\s*=.*$',
        "aws_subnet_ids = [] # wired from module.network in main.tf",
        body,
        count=1,
        flags=re.MULTILINE,
    )
    tfvars.write_text(body, encoding="utf-8")


def ensure_idp_locals(stack_dir: Path) -> None:
    classic = stack_dir / "identity_providers_classic.tf"
    if not classic.is_file():
        classic.write_text("locals {\n  identity_providers_classic = {}\n}\n", encoding="utf-8")


def _cluster_name_from_tfvars(stack_dir: Path) -> str:
    text = (stack_dir / "terraform.tfvars").read_text(encoding="utf-8")
    m = re.search(r'^\s*cluster_name\s*=\s*"([^"]+)"', text, re.M)
    return m.group(1) if m else "rosa-hcp"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stack-dir", type=Path, required=True)
    parser.add_argument("--module-version", default="1.7.6")
    parser.add_argument("--aws-region", required=True)
    parser.add_argument("--network-name-prefix", required=True)
    parser.add_argument("--network-vpc-cidr", required=True)
    parser.add_argument("--machine-cidr", required=True)
    args = parser.parse_args()

    write_combined_root(args.stack_dir, rosa_hcp_version=args.module_version)
    ensure_idp_locals(args.stack_dir)
    append_stack_tfvars(
        args.stack_dir,
        aws_region=args.aws_region,
        network_name_prefix=args.network_name_prefix,
        network_vpc_cidr=args.network_vpc_cidr,
        machine_cidr=args.machine_cidr,
    )
    cluster_name = _cluster_name_from_tfvars(args.stack_dir)
    import sys

    scripts = Path(__file__).resolve().parent
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from stack_readme import StackMeta, write_stack_readme

    write_stack_readme(
        args.stack_dir,
        StackMeta(
            kind="combined_hcp",
            aws_region=args.aws_region,
            cluster_name=cluster_name,
            target_cluster_name=cluster_name,
            module_version=args.module_version,
        ),
    )
    print(f"Wrote combined root stack to {args.stack_dir.resolve()}")


if __name__ == "__main__":
    main()
