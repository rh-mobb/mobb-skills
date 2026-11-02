#!/usr/bin/env python3
# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0
"""Print a Classic (+ optional AWS network) inventory briefing for operator confirmation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tgw_terraform import format_tgw_briefing


def _format_vpc_endpoints_briefing(inventory: dict[str, Any]) -> list[str]:
    eps = inventory.get("vpc_endpoints") or []
    if not eps:
        return []
    adoptable = [e for e in eps if e.get("adoptable")]
    cp = [e for e in eps if e.get("rosa_hcp_control_plane")]
    lines: list[str] = ["", "### VPC endpoints (discovered)", ""]
    if adoptable:
        lines.append(
            f"- **Customer (adoptable):** {len(adoptable)} — confirm before "
            "`network_to_tf.py --write` or pass `--skip-endpoints`."
        )
        for ep in adoptable[:8]:
            lines.append(
                f"  - `{ep.get('id', '?')}` — {ep.get('service_name', '?')} ({ep.get('type', '?')})"
            )
        if len(adoptable) > 8:
            lines.append(f"  - … and {len(adoptable) - 8} more")
    if cp:
        lines.append(
            "- **ROSA HCP control-plane VPCE:** present — **never** adopt in `network/` (ROSA-managed)."
        )
        cp_inv = inventory.get("rosa_hcp_control_plane_vpc_endpoint") or {}
        add_sgs = cp_inv.get("additional_control_plane_security_group_ids") or []
        if add_sgs:
            lines.append(
                f"- **Additional control-plane SGs:** {len(add_sgs)} — on **HCP cluster** stack "
                "(`additional-cp-sg`), not as network VPCE adopt."
            )
    return lines


def _items(doc: Any) -> list[dict[str, Any]]:
    if isinstance(doc, list):
        return doc
    if isinstance(doc, dict):
        for key in ("items", "Items", "body", "machine_pools"):
            if key in doc and isinstance(doc[key], list):
                return doc[key]
    return []


def _region(cluster: dict[str, Any]) -> str:
    reg = cluster.get("region") or {}
    return str(reg.get("id") or reg.get("name") or "?")


def _network_cidrs(cluster: dict[str, Any]) -> tuple[str, str, str]:
    net = cluster.get("network") or {}
    machine = str(net.get("machine_cidr") or net.get("machineCIDR") or "?")
    pod = str(net.get("pod_cidr") or net.get("podCIDR") or "?")
    service = str(net.get("service_cidr") or net.get("serviceCIDR") or "?")
    return machine, pod, service


def _ingress_listening(cluster: dict[str, Any], ingress_doc: Any) -> str:
    api = cluster.get("api") or {}
    if api.get("listening"):
        return str(api["listening"])
    for ing in _items(ingress_doc):
        if ing.get("default"):
            return str(ing.get("listening") or "?")
    return "?"


def _private_cluster(cluster: dict[str, Any], ingress_doc: Any) -> bool:
    api = cluster.get("api") or {}
    if api.get("listening") == "internal":
        return True
    for ing in _items(ingress_doc):
        if ing.get("default") and ing.get("listening") == "internal":
            return True
    return False


def _worker_pool(pools_doc: Any) -> dict[str, Any] | None:
    for pool in _items(pools_doc):
        pid = str(pool.get("id") or pool.get("name") or "")
        if pid == "worker" or pool.get("replicas") is not None:
            return pool
    return _items(pools_doc)[0] if _items(pools_doc) else None


def _azs_from_pools(pools_doc: Any) -> list[str]:
    worker = _worker_pool(pools_doc)
    if not worker:
        return []
    azs = worker.get("availability_zones") or worker.get("availabilityZones") or []
    return [str(a) for a in azs]


def format_briefing(
    cluster: dict[str, Any],
    pools_doc: Any,
    ingress_doc: Any,
    inventory: dict[str, Any] | None,
    idps_inventory: dict[str, Any] | None = None,
) -> str:
    name = str(cluster.get("name") or "?")
    cid = str(cluster.get("id") or "?")
    state = str(cluster.get("state") or "?")
    region = _region(cluster)
    machine_c, pod_c, service_c = _network_cidrs(cluster)
    private = _private_cluster(cluster, ingress_doc)
    ingress = _ingress_listening(cluster, ingress_doc)
    azs = _azs_from_pools(pools_doc)
    multi_az = len(azs) > 1
    worker = _worker_pool(pools_doc) or {}
    replicas = worker.get("replicas", "?")
    instance = worker.get("instance_type") or worker.get("instanceType") or "?"
    nodes = cluster.get("nodes") or {}

    lines = [
        "# Classic inventory briefing",
        "",
        f"**Cluster:** `{name}` (`{cid}`) — **{state}** — **{region}**",
        "",
        "## Topology (from Classic today)",
        "",
        f"- **API / ingress:** {'private (internal)' if private else 'public (external)'} "
        f"(API listening: `{ingress}`)",
        f"- **Availability:** {'multi-AZ' if multi_az else 'single-AZ'}"
        + (f" — {', '.join(azs)}" if azs else ""),
        f"- **Default workers:** `{instance}` × **{replicas}** total replicas",
    ]
    if nodes.get("infra"):
        infra_type = (nodes.get("infra_machine_type") or {}).get("id") or nodes.get(
            "infra_machine_type"
        )
        lines.append(
            f"- **Classic infra nodes (not separate machine pools in API):** "
            f"**{nodes.get('infra')}** × `{infra_type or '?'}`"
        )
    lines.extend(
        [
            "",
            "## CIDRs (Classic cluster network object)",
            "",
            "| Role | CIDR |",
            "|------|------|",
            f"| Machine | `{machine_c}` |",
            f"| Pod | `{pod_c}` |",
            f"| Service | `{service_c}` |",
        ]
    )

    if inventory:
        vpc = inventory.get("vpc") or {}
        subnets = inventory.get("subnets") or []
        priv = [s for s in subnets if not s.get("public")]
        pub = [s for s in subnets if s.get("public")]
        lines.extend(
            [
                "",
                "## AWS VPC (discovered)",
                "",
                f"- **VPC:** `{vpc.get('id', '?')}` — **`{vpc.get('cidr_block', '?')}`**",
                f"- **Subnets:** {len(priv)} private, {len(pub)} public",
            ]
        )
        nats = inventory.get("nat_gateways") or []
        if nats:
            lines.append(f"- **NAT gateways:** {len(nats)}")
        if inventory.get("internet_gateway"):
            lines.append("- **Internet gateway:** attached")
        rts = inventory.get("route_tables") or []
        if rts:
            lines.append(f"- **Route tables (named/worker):** {len(rts)}")
        tgw_section = format_tgw_briefing(inventory)
        if tgw_section:
            lines.append(tgw_section)
        lines.extend(_format_vpc_endpoints_briefing(inventory))

    else:
        aws = cluster.get("aws") or {}
        sids = aws.get("subnet_ids") or []
        lines.extend(
            [
                "",
                "## AWS VPC (cluster JSON only — run discovery for full inventory)",
                "",
                f"- **Subnet IDs on cluster:** {len(sids)}",
            ]
        )

    if idps_inventory:
        lines.extend(["", _format_idp_section(idps_inventory)])

    lines.extend(
        [
            "",
            "## Decisions (confirm or change before generating Terraform)",
            "",
            "The agent **must** wait for your answers. Do **not** auto-pick copy CIDRs or "
            "`--unique-cidrs` without confirmation.",
            "",
            "1. **HCP target cluster name** (default `<classic>-hcp`)",
            "2. **Network mode:** `adopt` (import existing VPC) vs `copy` (new VPC for parallel HCP)",
            "3. **VPC CIDR** — keep Classic VPC CIDR vs **new** CIDR for copy (required when Classic stays up)",
            "4. **Cluster CIDRs** — reuse Classic machine/pod/host_prefix vs **new** ranges",
            "5. **OpenShift version** — same minor / nearest patch on hosted-cp; if newer minor lines exist, pick from latest patch per line (`--openshift-version`)",
            "6. **Visibility** — keep **private** vs **public** (edit tfvars after generate if you change)",
            "7. **AZ layout** — keep **multi-AZ** vs **single-AZ** (fewer AZs may need manual edits)",
            "8. **Infra machine pools** on HCP — mirror Classic infra nodes?",
            "9. **Customer VPC endpoints** — include in `network/` vs `network_to_tf.py --skip-endpoints` "
            "(agent asks; **never** adopt ROSA HCP control-plane VPCE in `network/`)",
            "10. **Optional scope:** skip TGW, cluster SGs, or flow logs in network Terraform",
            "11. **Shared VPC** — out of scope (BYO VPC adopt/copy only)",
            "",
            "After you confirm, run `network_to_tf.py --write` and `classic_to_hcp.py --write` with your choices.",
        ]
    )
    return "\n".join(lines)


def _format_idp_section(idps_inventory: dict[str, Any]) -> str:
    idps = idps_inventory.get("identity_providers") or []
    lines = ["## Identity providers (Classic)", ""]
    if not idps:
        lines.append("_No IdPs configured on Classic._")
        return "\n".join(lines)
    lines.extend(["| Name | Type | Notes |", "|------|------|-------|"])
    for idp in idps:
        name = idp.get("name", "?")
        typ = idp.get("type", "?")
        note = ""
        if typ == "htpasswd":
            n = len(idp.get("htpasswd_users") or [])
            note = f"{n} htpasswd user(s)" if n else "empty htpasswd IdP"
        elif typ in ("openid", "github", "gitlab", "google", "ldap"):
            note = "needs new OAuth client + callback on HCP"
        lines.append(f"| `{name}` | {typ} | {note} |")
    lines.append("")
    lines.append(
        "Collect with `fetch_classic_idps.py`; HCP Terraform replicates **htpasswd** "
        "and emits commented stubs for OAuth/OIDC types."
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cluster-json", type=Path, required=True)
    parser.add_argument("--machinepools-json", type=Path, required=True)
    parser.add_argument("--ingress-json", type=Path, required=True)
    parser.add_argument("--network-inventory", type=Path, default=None)
    parser.add_argument(
        "--idps-inventory",
        type=Path,
        default=None,
        help="From fetch_classic_idps.py (Classic IdP list + describe).",
    )
    args = parser.parse_args()

    cluster = json.loads(args.cluster_json.read_text(encoding="utf-8"))
    pools = json.loads(args.machinepools_json.read_text(encoding="utf-8"))
    ingress = json.loads(args.ingress_json.read_text(encoding="utf-8"))
    inv = None
    if args.network_inventory:
        inv = json.loads(args.network_inventory.read_text(encoding="utf-8"))
    idps_inv = None
    if args.idps_inventory:
        idps_inv = json.loads(args.idps_inventory.read_text(encoding="utf-8"))

    print(format_briefing(cluster, pools, ingress, inv, idps_inv))


if __name__ == "__main__":
    main()
