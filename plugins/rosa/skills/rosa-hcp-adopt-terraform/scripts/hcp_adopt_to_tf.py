#!/usr/bin/env python3
# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0
"""Generate adopt Terraform for an existing ROSA HCP cluster (terraform-redhat/rosa-hcp/rhcs)."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _network_skill_scripts() -> Path:
    return Path(__file__).resolve().parents[2] / "rosa-classic-network-terraform" / "scripts"


def _write_stack_makefile(stack_dir: Path, aws_region: str) -> None:
    import sys

    scripts = _network_skill_scripts()
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from stack_makefile import write_split_stack_makefile

    write_split_stack_makefile(stack_dir, aws_region=aws_region)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _optional_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    doc = json.loads(text)
    return doc if isinstance(doc, dict) else None


def _items(doc: Any) -> list[dict[str, Any]]:
    if isinstance(doc, list):
        return doc
    if isinstance(doc, dict):
        for key in ("items", "Items", "body"):
            if key in doc and isinstance(doc[key], list):
                return doc[key]
    return []


def _hcl_string(val: str) -> str:
    escaped = val.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _format_string_map_hcl(values: dict[str, str]) -> str:
    if not values:
        return "{}"
    lines = ["{"]
    for key in sorted(values):
        lines.append(f"  {_hcl_string(key)} = {_hcl_string(str(values[key]))}")
    lines.append("}")
    return "\n".join(lines)


def _pool_autoscaling_active(pools_doc: Any) -> bool:
    for pool in _items(pools_doc):
        scaling = pool.get("autoscaling") or {}
        if not scaling:
            continue
        min_r = int(scaling.get("min_replicas") or scaling.get("min_replica") or 0)
        max_r = int(scaling.get("max_replicas") or scaling.get("max_replica") or 0)
        enabled = scaling.get("enabled")
        if enabled is None:
            enabled = min_r > 0 or max_r > 0
        if enabled:
            return True
    return False


def _resolve_cluster_autoscaler(
    cluster: dict[str, Any],
    pools_doc: Any,
    autoscaler_doc: dict[str, Any] | None,
) -> tuple[bool, int | None, list[str]]:
    notes: list[str] = []
    if _pool_autoscaling_active(pools_doc):
        notes.append(
            "Node pool autoscaling is active — `cluster_autoscaler_enabled` is false (HCP scales via node pools)."
        )
        return False, None, notes

    if autoscaler_doc:
        limits = autoscaler_doc.get("resource_limits") or {}
        max_total = limits.get("max_nodes_total")
        if max_total is not None and int(max_total) > 0:
            return True, int(max_total), notes

    nodes = cluster.get("nodes") or {}
    autoscale = nodes.get("autoscale_compute") or {}
    max_r = autoscale.get("max_replicas")
    if max_r is not None and int(max_r) > 0:
        notes.append("Cluster autoscaler enabled from `nodes.autoscale_compute` (embedded workers, no pool autoscaling).")
        return True, int(max_r), notes

    return False, None, notes


_RESERVED_CLUSTER_PROPERTIES = frozenset({"rosa_tf_version", "rosa_tf_commit"})


def _cluster_properties(cluster: dict[str, Any]) -> dict[str, str]:
    raw = cluster.get("properties") or {}
    if not isinstance(raw, dict):
        return {}
    return {
        str(k): str(v)
        for k, v in raw.items()
        if v is not None
        and str(v) != ""
        and str(k) not in _RESERVED_CLUSTER_PROPERTIES
    }


def _cluster_is_hcp(cluster: dict[str, Any]) -> bool:
    return bool((cluster.get("hypershift") or {}).get("enabled"))


def _region(cluster: dict[str, Any]) -> str:
    region = cluster.get("region") or {}
    if isinstance(region, dict):
        return str(region.get("id") or region.get("name") or "")
    return str(region)


def _openshift_version(cluster: dict[str, Any]) -> str:
    version = cluster.get("version") or {}
    if isinstance(version, dict):
        return str(version.get("raw_id") or version.get("id") or "")
    return str(version) if version else ""


def _channel(cluster: dict[str, Any]) -> str | None:
    ch = cluster.get("channel")
    if ch:
        return str(ch)
    version = cluster.get("version") or {}
    if isinstance(version, dict) and version.get("channel"):
        return str(version["channel"])
    return None


def _private_cluster(cluster: dict[str, Any], ingress_doc: Any) -> bool:
    api = cluster.get("api") or {}
    if api.get("listening") == "internal":
        return True
    for ing in _items(ingress_doc):
        if ing.get("default") and ing.get("listening") == "internal":
            return True
    return False


def _default_ingress_listening(ingress_doc: Any, private: bool) -> str:
    for ing in _items(ingress_doc):
        if ing.get("default"):
            return str(ing.get("listening") or ("internal" if private else "external"))
    return "internal" if private else "external"


def _account_role_prefix(installer_role_arn: str, cluster_name: str) -> str:
    name = installer_role_arn.split("/")[-1]
    suffix = "-HCP-ROSA-Installer-Role"
    if name.endswith(suffix):
        return name[: -len(suffix)]
    return cluster_name


def _sts_arns(cluster: dict[str, Any]) -> tuple[str, str, str, str]:
    sts = (cluster.get("aws") or {}).get("sts") or {}
    installer = str(sts.get("role_arn") or "")
    oidc_id = str((sts.get("oidc_config") or {}).get("id") or "")
    op_prefix = str(sts.get("operator_role_prefix") or cluster.get("name") or "rosa")
    if not installer or not oidc_id:
        raise SystemExit("Cluster JSON missing STS role_arn or oidc_config.id for adopt.")
    acct_prefix = _account_role_prefix(installer, str(cluster.get("name") or "cluster"))
    return installer, oidc_id, op_prefix, acct_prefix


def _subnet_by_az_from_inventory(inv: dict[str, Any]) -> dict[str, str]:
    wiring = inv.get("rosa_hcp_wiring") or {}
    by_az = wiring.get("private_subnet_ids_by_az") or {}
    return {str(k): str(v) for k, v in by_az.items()}


def _pick_subnet_for_az(
    az: str,
    cluster: dict[str, Any],
    subnet_by_az: dict[str, str],
) -> str:
    if az in subnet_by_az:
        return subnet_by_az[az]
    for sid in (cluster.get("aws") or {}).get("subnet_ids") or []:
        return str(sid)
    return ""


@dataclass
class AdoptMapping:
    cluster_name: str
    cluster_id: str
    region: str
    module_version: str
    openshift_version: str
    channel: str | None
    private: bool
    default_ingress_listening: str
    aws_subnet_ids: list[str]
    machine_cidr: str | None
    pod_cidr: str | None
    service_cidr: str | None
    host_prefix: int | None
    installer_role_arn: str
    oidc_config_id: str
    operator_role_prefix: str
    account_role_prefix: str
    compute_machine_type: str
    worker_disk_size: int | None
    replicas: int | None
    cluster_autoscaler_enabled: bool
    autoscaler_min: int | None
    autoscaler_max: int | None
    machine_pools: dict[str, dict[str, Any]]
    import_pool_keys: list[tuple[str, str]]
    availability_zones: list[str]
    ec2_metadata_http_tokens: str
    aws_billing_account_id: str | None
    properties: dict[str, str]
    additional_control_plane_security_group_ids: list[str]
    control_plane_vpce_id: str | None
    notes: list[str] = field(default_factory=list)


def build_mapping(
    cluster: dict[str, Any],
    pools_doc: Any,
    ingress_doc: Any,
    *,
    module_version: str,
    network_inventory: dict[str, Any] | None = None,
    autoscaler_doc: dict[str, Any] | None = None,
) -> AdoptMapping:
    if not _cluster_is_hcp(cluster):
        raise SystemExit("Cluster is not ROSA HCP (hypershift.enabled must be true).")

    name = str(cluster.get("name") or "cluster")
    cid = str(cluster.get("id") or "")
    if not cid:
        raise SystemExit("Cluster JSON missing id")

    net = cluster.get("network") or {}
    subnet_by_az = _subnet_by_az_from_inventory(network_inventory) if network_inventory else {}
    aws_subnets = [str(s) for s in (cluster.get("aws") or {}).get("subnet_ids") or []]
    if network_inventory:
        order = (network_inventory.get("rosa_hcp_wiring") or {}).get("aws_subnet_ids") or []
        if order:
            aws_subnets = [str(s) for s in order]

    private = _private_cluster(cluster, ingress_doc)
    ingress_method = _default_ingress_listening(ingress_doc, private)
    installer, oidc_id, op_prefix, acct_prefix = _sts_arns(cluster)

    nodes = cluster.get("nodes") or {}
    compute_type = "m5.xlarge"
    cmt = nodes.get("compute_machine_type")
    if isinstance(cmt, dict) and cmt.get("id"):
        compute_type = str(cmt["id"])
    disk = None
    root = (nodes.get("compute_root_volume") or {}).get("aws") or {}
    if root.get("size"):
        disk = int(root["size"])

    aws_block = cluster.get("aws") or {}
    ec2_imds = str(aws_block.get("ec2_metadata_http_tokens") or "optional")
    billing_id = aws_block.get("billing_account_id")
    billing_str = str(billing_id) if billing_id else None
    props = _cluster_properties(cluster)

    add_cp_sgs: list[str] = []
    cp_vpce_id: str | None = None
    if network_inventory and private:
        cp_meta = network_inventory.get("rosa_hcp_control_plane_vpc_endpoint") or {}
        cp_vpce_id = str(cp_meta["id"]) if cp_meta.get("id") else None
        add_cp_sgs = [
            str(s) for s in (cp_meta.get("additional_control_plane_security_group_ids") or [])
        ]

    cluster_autoscaler, autoscaler_max, autoscaler_notes = _resolve_cluster_autoscaler(
        cluster, pools_doc, autoscaler_doc
    )

    pools = _items(pools_doc)
    machine_pools: dict[str, dict[str, Any]] = {}
    import_pools: list[tuple[str, str]] = []
    ocp = _openshift_version(cluster)
    ch = _channel(cluster)

    for pool in pools:
        pool_id = str(pool.get("id") or pool.get("name") or "pool")
        tf_key = re.sub(r"[^a-zA-Z0-9_]", "_", pool_id).strip("_").lower() or "pool"
        az = str(pool.get("availability_zone") or "")
        subnet_id = _pick_subnet_for_az(az, cluster, subnet_by_az)
        anp = pool.get("aws_node_pool") or {}
        inst = str(anp.get("instance_type") or compute_type)
        rv = (anp.get("root_volume") or {}).get("size")
        raw_tags = anp.get("tags") or {}
        pool_tags = (
            {str(k): str(v) for k, v in raw_tags.items() if v is not None and str(v) != ""}
            if isinstance(raw_tags, dict)
            else {}
        )
        spec: dict[str, Any] = {
            "name": pool_id,
            "subnet_id": subnet_id,
            "openshift_version": ocp,
            "auto_repair": pool.get("auto_repair", True),
            "aws_node_pool": {"instance_type": inst, "tags": pool_tags},
        }
        if rv:
            spec["aws_node_pool"]["root_volume"] = {"size": int(rv)}
        scaling = pool.get("autoscaling") or {}
        if scaling:
            min_r = int(scaling.get("min_replicas") or scaling.get("min_replica") or 0)
            max_r = int(scaling.get("max_replicas") or scaling.get("max_replica") or 0)
            enabled = scaling.get("enabled")
            if enabled is None:
                enabled = min_r > 0 or max_r > 0
            spec["autoscaling"] = {
                "enabled": bool(enabled),
                "min_replicas": min_r,
                "max_replicas": max_r,
            }
        elif pool.get("replicas") is not None:
            spec["replicas"] = int(pool["replicas"])
        machine_pools[tf_key] = spec
        import_pools.append((tf_key, pool_id))

    notes = [
        "Adopt mode: IAM/OIDC/operator roles are **not** created by Terraform (`create_* = false`).",
        "Run `terraform plan` after import; expect drift on read-only API fields (state, URLs).",
        "OCM reserved property keys `rosa_tf_version` / `rosa_tf_commit` are omitted from tfvars (provider-managed).",
        "Import IDs for node pools use `{cluster_id},{pool_name}` — verify against RHCS provider docs.",
    ]
    notes.extend(autoscaler_notes)
    if private and add_cp_sgs:
        notes.append(
            "Private cluster: additional control-plane SG(s) on ROSA VPCE mapped to "
            "`aws_additional_control_plane_security_group_ids` (additional-cp-sg imports)."
        )
    elif private and cp_vpce_id:
        notes.append(
            "Private cluster: ROSA HCP control-plane VPCE detected; no extra CP SGs beyond "
            "default PrivateLink router SG."
        )
    if not pools:
        notes.append("No node pools in JSON — default workers may be cluster-embedded only; check OCM API.")

    azs = [str(z) for z in (nodes.get("availability_zones") or [])]

    return AdoptMapping(
        cluster_name=name,
        cluster_id=cid,
        region=_region(cluster),
        module_version=module_version,
        openshift_version=ocp,
        channel=ch,
        private=private,
        default_ingress_listening=ingress_method,
        aws_subnet_ids=aws_subnets,
        machine_cidr=net.get("machine_cidr"),
        pod_cidr=net.get("pod_cidr"),
        service_cidr=net.get("service_cidr"),
        host_prefix=net.get("host_prefix"),
        installer_role_arn=installer,
        oidc_config_id=oidc_id,
        operator_role_prefix=op_prefix,
        account_role_prefix=acct_prefix,
        compute_machine_type=compute_type,
        worker_disk_size=disk,
        replicas=nodes.get("compute") if isinstance(nodes.get("compute"), int) else None,
        cluster_autoscaler_enabled=cluster_autoscaler,
        autoscaler_min=None,
        autoscaler_max=autoscaler_max,
        machine_pools=machine_pools,
        import_pool_keys=import_pools,
        availability_zones=azs,
        ec2_metadata_http_tokens=ec2_imds,
        aws_billing_account_id=billing_str,
        properties=props,
        additional_control_plane_security_group_ids=add_cp_sgs,
        control_plane_vpce_id=cp_vpce_id,
        notes=notes,
    )


def _format_machine_pools_hcl(pools: dict[str, dict[str, Any]]) -> str:
    if not pools:
        return "{}"
    lines = ["{"]
    for key, spec in pools.items():
        lines.append(f"  {key} = {{")
        lines.append(f"    name              = {_hcl_string(spec['name'])}")
        lines.append(f"    subnet_id         = {_hcl_string(str(spec.get('subnet_id') or ''))}")
        lines.append(f"    openshift_version = {_hcl_string(str(spec['openshift_version']))}")
        lines.append(f"    auto_repair       = {'true' if spec.get('auto_repair', True) else 'false'}")
        if spec.get("autoscaling"):
            a = spec["autoscaling"]
            lines.append("    autoscaling = {")
            lines.append(f"      enabled      = {'true' if a['enabled'] else 'false'}")
            lines.append(f"      min_replicas = {a['min_replicas']}")
            lines.append(f"      max_replicas = {a['max_replicas']}")
            lines.append("    }")
        elif "replicas" in spec:
            lines.append(f"    replicas = {spec['replicas']}")
        inst = spec["aws_node_pool"]["instance_type"]
        lines.append("    aws_node_pool = {")
        lines.append(f"      instance_type = {_hcl_string(inst)}")
        tags_hcl = _format_string_map_hcl(spec["aws_node_pool"].get("tags") or {})
        if tags_hcl == "{}":
            lines.append("      tags = {}")
        else:
            lines.append(f"      tags = {tags_hcl.replace(chr(10), chr(10) + '      ')}")
        if spec["aws_node_pool"].get("root_volume"):
            rv = spec["aws_node_pool"]["root_volume"]["size"]
            lines.append(f"      root_volume = {{ size = {rv} }}")
        lines.append("    }")
        lines.append("  }")
    lines.append("}")
    return "\n".join(lines)


def generate_imports(result: AdoptMapping, *, include_default_ingress: bool) -> str:
    lines = [
        "# Import existing HCP cluster into terraform-redhat/rosa-hcp/rhcs module graph.",
        "# Apply imports before or during first `terraform apply` (Terraform 1.5+).",
        "",
        "import {",
        "  to = module.rosa_hcp.module.rosa_cluster_hcp.rhcs_cluster_rosa_hcp.rosa_hcp_cluster",
        f"  id = {_hcl_string(result.cluster_id)}",
        "}",
        "",
    ]
    if include_default_ingress:
        lines.extend(
            [
                "import {",
                "  to = module.rosa_hcp.module.rosa_cluster_hcp.rhcs_hcp_default_ingress.default_ingress[0]",
                f"  id = {_hcl_string(result.cluster_id)}",
                "}",
                "",
            ]
        )
    if result.cluster_autoscaler_enabled:
        lines.extend(
            [
                "import {",
                "  to = module.rosa_hcp.module.rosa_cluster_hcp.rhcs_hcp_cluster_autoscaler.cluster_autoscaler[0]",
                f"  id = {_hcl_string(result.cluster_id)}",
                "}",
                "",
            ]
        )
    if (
        result.private
        and result.control_plane_vpce_id
        and result.additional_control_plane_security_group_ids
    ):
        for idx, sg_id in enumerate(result.additional_control_plane_security_group_ids):
            lines.extend(
                [
                    "import {",
                    "  to = module.rosa_hcp.module.rhcs_hcp_additional_controlplane_sg[0]"
                    f'.aws_vpc_endpoint_security_group_association.control_plane_sg[{idx}]',
                    f"  id = {_hcl_string(f'{result.control_plane_vpce_id}/{sg_id}')}",
                    "}",
                    "",
                ]
            )
    for tf_key, pool_name in result.import_pool_keys:
        lines.extend(
            [
                "import {",
                f'  to = module.rosa_hcp.module.rhcs_hcp_machine_pool["{tf_key}"].rhcs_hcp_machine_pool.machine_pool',
                f"  id = {_hcl_string(f'{result.cluster_id},{pool_name}')}",
                "}",
                "",
            ]
        )
    return "\n".join(lines)


def write_stack(result: AdoptMapping, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    ch_line = f"channel = {_hcl_string(result.channel)}" if result.channel else "channel = null"
    hp = result.host_prefix
    hp_line = str(hp) if hp is not None else "null"
    disk = result.worker_disk_size
    disk_line = str(disk) if disk is not None else "null"
    repl = result.replicas
    repl_line = str(repl) if repl is not None else "null"

    (output_dir / "versions.tf").write_text(
        f'''terraform {{
  required_version = ">= 1.5.7"

  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = ">= 6.51.0"
    }}
    rhcs = {{
      source  = "terraform-redhat/rhcs"
      version = ">= 1.7.8"
    }}
  }}
}}

provider "aws" {{
  region = var.aws_region
}}

provider "rhcs" {{
  # Set RHCS_TOKEN in the environment (from console.redhat.com/openshift/token).
}}
''',
        encoding="utf-8",
    )

    (output_dir / "main.tf").write_text(
        f'''module "rosa_hcp" {{
  source  = "terraform-redhat/rosa-hcp/rhcs"
  version = "{result.module_version}"

  cluster_name      = var.cluster_name
  openshift_version = var.openshift_version
  {ch_line}

  aws_subnet_ids         = var.aws_subnet_ids
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

  create_account_roles  = false
  account_role_prefix   = var.account_role_prefix

  create_oidc      = false
  oidc_config_id   = var.oidc_config_id

  create_operator_roles = false
  operator_role_prefix  = var.operator_role_prefix

  cluster_autoscaler_enabled = var.cluster_autoscaler_enabled
  autoscaler_max_nodes_total = var.autoscaler_max_nodes_total

  ec2_metadata_http_tokens = var.ec2_metadata_http_tokens
  aws_billing_account_id   = var.aws_billing_account_id
  properties                 = var.properties

  aws_additional_control_plane_security_group_ids = var.aws_additional_control_plane_security_group_ids

  # true so rhcs_hcp_default_ingress is in the module graph (required for ingress import).
  wait_for_create_complete            = true
  wait_for_std_compute_nodes_complete = false

  machine_pools = var.machine_pools
  identity_providers = {{}}
}}
''',
        encoding="utf-8",
    )

    (output_dir / "variables.tf").write_text(
        '''variable "aws_region" {
  type = string
}

variable "cluster_name" {
  type = string
}

variable "openshift_version" {
  type = string
}

variable "channel" {
  type    = string
  default = null
}

variable "aws_subnet_ids" {
  type = list(string)
}

variable "aws_availability_zones" {
  type    = list(string)
  default = []
}

variable "private" {
  type = bool
}

variable "default_ingress_listening_method" {
  type = string
}

variable "machine_cidr" {
  type    = string
  default = null
}

variable "pod_cidr" {
  type    = string
  default = null
}

variable "service_cidr" {
  type    = string
  default = null
}

variable "host_prefix" {
  type    = number
  default = null
}

variable "replicas" {
  type    = number
  default = null
}

variable "compute_machine_type" {
  type = string
}

variable "worker_disk_size" {
  type    = number
  default = null
}

variable "account_role_prefix" {
  type = string
}

variable "oidc_config_id" {
  type = string
}

variable "operator_role_prefix" {
  type = string
}

variable "cluster_autoscaler_enabled" {
  type    = bool
  default = false
}

variable "autoscaler_max_nodes_total" {
  type    = number
  default = null
}

variable "ec2_metadata_http_tokens" {
  type    = string
  default = "optional"
}

variable "aws_billing_account_id" {
  type    = string
  default = null
}

variable "properties" {
  type    = map(string)
  default = {}
}

variable "aws_additional_control_plane_security_group_ids" {
  type        = list(string)
  default     = null
  description = "Private clusters only: extra SGs on ROSA HCP control-plane VPCE (additional-cp-sg module)."
}

variable "machine_pools" {
  type    = any
  default = {}
}
''',
        encoding="utf-8",
    )

    mp_hcl = _format_machine_pools_hcl(result.machine_pools)
    az_list = result.availability_zones

    tfvars = f'''# Adopt stack for existing HCP cluster {result.cluster_name} ({result.cluster_id})
# Module: terraform-redhat/rosa-hcp/rhcs (same as create path; imports bind live resources)

aws_region = {_hcl_string(result.region)}
cluster_name = {_hcl_string(result.cluster_name)}
openshift_version = {_hcl_string(result.openshift_version)}
{("channel = " + _hcl_string(result.channel)) if result.channel else "# channel omitted — set if plan requires it"}

aws_subnet_ids = {json.dumps(result.aws_subnet_ids)}
aws_availability_zones = {json.dumps(az_list)}

private = {"true" if result.private else "false"}
default_ingress_listening_method = {_hcl_string(result.default_ingress_listening)}

machine_cidr = {_hcl_string(str(result.machine_cidr)) if result.machine_cidr else "null"}
pod_cidr     = {_hcl_string(str(result.pod_cidr)) if result.pod_cidr else "null"}
service_cidr = {_hcl_string(str(result.service_cidr)) if result.service_cidr else "null"}
host_prefix  = {hp_line}

replicas             = {repl_line}
compute_machine_type = {_hcl_string(result.compute_machine_type)}
worker_disk_size     = {disk_line}

account_role_prefix  = {_hcl_string(result.account_role_prefix)}
oidc_config_id       = {_hcl_string(result.oidc_config_id)}
operator_role_prefix = {_hcl_string(result.operator_role_prefix)}

# Live installer ARN (for verification): {result.installer_role_arn}

cluster_autoscaler_enabled = {"true" if result.cluster_autoscaler_enabled else "false"}
autoscaler_max_nodes_total = {result.autoscaler_max if result.autoscaler_max is not None else "null"}

ec2_metadata_http_tokens = {_hcl_string(result.ec2_metadata_http_tokens)}
aws_billing_account_id   = {_hcl_string(result.aws_billing_account_id) if result.aws_billing_account_id else "null"}
properties = {_format_string_map_hcl(result.properties)}

aws_additional_control_plane_security_group_ids = {
    json.dumps(result.additional_control_plane_security_group_ids)
    if result.private and result.additional_control_plane_security_group_ids
    else "null"
}

machine_pools = {mp_hcl}
'''
    (output_dir / "terraform.tfvars").write_text(tfvars, encoding="utf-8")
    (output_dir / "imports.tf").write_text(
        generate_imports(result, include_default_ingress=True),
        encoding="utf-8",
    )

    adopt_md = [
        f"# Adopt `{result.cluster_name}` into Terraform",
        "",
        "Operator runbook: **[README.md](README.md)** (prerequisites, Makefile, apply/destroy order).",
        "",
        f"- OCM cluster ID: `{result.cluster_id}`",
        f"- Module `terraform-redhat/rosa-hcp/rhcs` `{result.module_version}`",
        "",
    ]
    adopt_md.append("")
    (output_dir / "ADOPT.md").write_text("\n".join(adopt_md), encoding="utf-8")

    _write_stack_makefile(output_dir, result.region)

    import sys

    scripts = _network_skill_scripts()
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from stack_readme import StackMeta, write_stack_readme

    write_stack_readme(
        output_dir,
        StackMeta(
            kind="hcp_adopt",
            aws_region=result.region,
            cluster_name=result.cluster_name,
            cluster_id=result.cluster_id,
            module_version=result.module_version,
            notes=list(result.notes),
        ),
    )


def format_dry_run(result: AdoptMapping) -> str:
    lines = [
        f"Cluster: {result.cluster_name} ({result.cluster_id})",
        f"Region: {result.region}",
        f"OpenShift: {result.openshift_version}" + (f" ({result.channel})" if result.channel else ""),
        f"Private: {result.private}, ingress: {result.default_ingress_listening}",
        f"Subnets ({len(result.aws_subnet_ids)}): {', '.join(result.aws_subnet_ids)}",
        f"OIDC config: {result.oidc_config_id}",
        f"Operator prefix: {result.operator_role_prefix}",
        f"Node pools to import: {len(result.import_pool_keys)}",
        f"Cluster autoscaler in TF: {result.cluster_autoscaler_enabled}"
        + (f" (max_nodes_total={result.autoscaler_max})" if result.autoscaler_max else ""),
        f"IMDS tokens: {result.ec2_metadata_http_tokens}",
        "",
        "Notes:",
    ]
    lines.extend(f"  - {n}" for n in result.notes)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cluster-json", type=Path, required=True)
    parser.add_argument("--machinepools-json", type=Path, required=True)
    parser.add_argument("--ingress-json", type=Path, required=True)
    parser.add_argument("--network-inventory", type=Path, default=None)
    parser.add_argument(
        "--autoscaler-json",
        type=Path,
        default=None,
        help="OCM GET .../clusters/{id}/autoscaler (optional; used when no node pool autoscaling)",
    )
    parser.add_argument("--module-version", default="1.7.6")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    args = parser.parse_args()

    if args.dry_run == args.write:
        raise SystemExit("Specify exactly one of --dry-run or --write.")

    cluster = _load_json(args.cluster_json)
    pools = _load_json(args.machinepools_json)
    ingress = _load_json(args.ingress_json)
    net_inv = _load_json(args.network_inventory) if args.network_inventory else None
    autoscaler = _optional_json(args.autoscaler_json)

    result = build_mapping(
        cluster,
        pools,
        ingress,
        module_version=args.module_version,
        network_inventory=net_inv,
        autoscaler_doc=autoscaler,
    )
    if args.dry_run:
        print(format_dry_run(result))
        return
    write_stack(result, args.output_dir)
    print(f"Wrote adopt stack to {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
