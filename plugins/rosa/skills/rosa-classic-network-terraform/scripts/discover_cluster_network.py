#!/usr/bin/env python3
# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0
"""Build network-inventory.json from ROSA cluster JSON (Classic or HCP) and AWS read-only APIs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError as exc:  # pragma: no cover
    raise SystemExit("discover_cluster_network.py requires boto3") from exc

SCHEMA_VERSION = 1


def _items(doc: Any) -> list[dict[str, Any]]:
    if isinstance(doc, list):
        return doc
    if isinstance(doc, dict):
        for key in ("items", "Items"):
            if key in doc and isinstance(doc[key], list):
                return doc[key]
    return []


def _tag_map(tags: list[dict[str, str]] | None) -> dict[str, str]:
    if not tags:
        return {}
    return {t["Key"]: t["Value"] for t in tags if "Key" in t and "Value" in t}


def _region(cluster: dict[str, Any]) -> str:
    reg = cluster.get("region") or {}
    rid = reg.get("id") or reg.get("name")
    if not rid:
        raise SystemExit("Cluster JSON missing region.id")
    return str(rid)


def _cluster_subnet_seeds(cluster: dict[str, Any], pools_doc: Any) -> list[str]:
    ids: list[str] = []
    aws = cluster.get("aws") or {}
    for sid in aws.get("subnet_ids") or []:
        if sid and sid not in ids:
            ids.append(str(sid))
    for pool in _items(pools_doc):
        for sid in pool.get("subnets") or []:
            if sid and sid not in ids:
                ids.append(str(sid))
    if not ids:
        raise SystemExit("No subnet IDs on cluster.aws.subnet_ids or machine pool subnets")
    return ids


def _is_public_subnet(subnet: dict[str, Any], tags: dict[str, str]) -> bool:
    if subnet.get("MapPublicIpOnLaunch"):
        return True
    if tags.get("kubernetes.io/role/elb") == "1":
        return True
    name = tags.get("Name", "").lower()
    if "public" in name and "private" not in name:
        return True
    return False


def _private_cluster(cluster: dict[str, Any], ingress_doc: Any) -> bool:
    api = cluster.get("api") or {}
    if api.get("listening") == "internal":
        return True
    for ing in _items(ingress_doc):
        if ing.get("default") and ing.get("listening") == "internal":
            return True
    return False


def _sort_az(subnets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(subnets, key=lambda s: (s["availability_zone"], s["id"]))


def _rosa_hcp_subnet_order(
    private_subnets: list[dict[str, Any]],
    public_subnets: list[dict[str, Any]],
    private_cluster: bool,
) -> dict[str, Any]:
    priv = _sort_az(private_subnets)
    pub = _sort_az(public_subnets)
    ordered = [s["id"] for s in priv]
    if not private_cluster:
        ordered.extend(s["id"] for s in pub)
    by_az = {s["availability_zone"]: s["id"] for s in priv}
    return {
        "aws_subnet_ids": ordered,
        "private_subnet_ids_by_az": by_az,
        "private_subnet_ids": [s["id"] for s in priv],
        "public_subnet_ids": [s["id"] for s in pub] if not private_cluster else [],
    }


def _is_rosa_hcp_control_plane_vpc_endpoint(
    tags: dict[str, str], cluster_id: str, cluster_name: str
) -> bool:
    """ROSA HCP creates a control-plane PrivateLink VPCE tagged with the cluster OCM id/name."""
    if cluster_id and tags.get("api.openshift.com/id") == cluster_id:
        return True
    if cluster_name and tags.get("api.openshift.com/name") == cluster_name:
        return True
    return False


def _additional_control_plane_security_group_ids(groups: list[dict[str, Any]]) -> list[str]:
    """Extra SGs on the control-plane VPCE (module additional-cp-sg), excluding default PrivateLink router SG."""
    extra: list[str] = []
    for g in groups:
        gid = g.get("GroupId")
        if not gid:
            continue
        name = (g.get("GroupName") or "").lower()
        if "vpce-private-router" in name or name.endswith("-private-router"):
            continue
        extra.append(str(gid))
    return extra


def discover(
    cluster: dict[str, Any],
    pools_doc: Any,
    ingress_doc: Any,
    *,
    include_endpoints: bool = True,
    include_security_groups: bool = True,
    include_flow_logs: bool = True,
    include_tgw: bool = True,
) -> dict[str, Any]:
    region = _region(cluster)
    name = str(cluster.get("name") or "")
    infra_id = str(cluster.get("infra_id") or "")
    cluster_id = str(cluster.get("id") or "")
    private_cluster = _private_cluster(cluster, ingress_doc)

    session = boto3.Session(region_name=region)
    ec2 = session.client("ec2")

    seed_ids = _cluster_subnet_seeds(cluster, pools_doc)
    try:
        sub_resp = ec2.describe_subnets(SubnetIds=seed_ids)
    except ClientError as exc:
        raise SystemExit(f"describe_subnets failed: {exc}") from exc

    subnets_raw = sub_resp.get("Subnets") or []
    if len(subnets_raw) != len(seed_ids):
        found = {s["SubnetId"] for s in subnets_raw}
        missing = [s for s in seed_ids if s not in found]
        raise SystemExit(f"Could not describe subnets: {missing}")

    vpc_ids = {s["VpcId"] for s in subnets_raw}
    if len(vpc_ids) != 1:
        raise SystemExit(f"Expected one VPC, found {vpc_ids}")
    vpc_id = next(iter(vpc_ids))

    subnets: list[dict[str, Any]] = []
    for s in subnets_raw:
        tags = _tag_map(s.get("Tags"))
        public = _is_public_subnet(s, tags)
        subnets.append(
            {
                "id": s["SubnetId"],
                "availability_zone": s["AvailabilityZone"],
                "cidr_block": s["CidrBlock"],
                "public": public,
                "map_public_ip_on_launch": bool(s.get("MapPublicIpOnLaunch")),
                "tags": tags,
            }
        )

    private_subnets = [s for s in subnets if not s["public"]]
    public_subnets = [s for s in subnets if s["public"]]

    vpc_resp = ec2.describe_vpcs(VpcIds=[vpc_id])
    vpc = vpc_resp["Vpcs"][0]
    vpc_tags = _tag_map(vpc.get("Tags"))

    igw_resp = ec2.describe_internet_gateways(
        Filters=[{"Name": "attachment.vpc-id", "Values": [vpc_id]}]
    )
    igws = [
        {"id": g["InternetGatewayId"], "tags": _tag_map(g.get("Tags"))}
        for g in igw_resp.get("InternetGateways") or []
    ]

    nat_resp = ec2.describe_nat_gateways(
        Filter=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )
    nat_gateways = []
    for ng in nat_resp.get("NatGateways") or []:
        if ng.get("State") == "deleted":
            continue
        addrs = ng.get("NatGatewayAddresses") or []
        eip_alloc = addrs[0].get("AllocationId") if addrs else None
        nat_gateways.append(
            {
                "id": ng["NatGatewayId"],
                "subnet_id": ng["SubnetId"],
                "eip_allocation_id": eip_alloc,
                "state": ng.get("State"),
                "tags": _tag_map(ng.get("Tags")),
            }
        )

    rt_resp = ec2.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )
    route_tables = []
    for rt in rt_resp.get("RouteTables") or []:
        routes = []
        for route in rt.get("Routes") or []:
            routes.append(
                {
                    "destination_cidr": route.get("DestinationCidrBlock"),
                    "gateway_id": route.get("GatewayId"),
                    "nat_gateway_id": route.get("NatGatewayId"),
                    "transit_gateway_id": route.get("TransitGatewayId"),
                }
            )
        associations = []
        for assoc in rt.get("Associations") or []:
            associations.append(
                {
                    "subnet_id": assoc.get("SubnetId"),
                    "main": bool(assoc.get("Main")),
                    "association_id": assoc.get("RouteTableAssociationId"),
                }
            )
        route_tables.append(
            {
                "id": rt["RouteTableId"],
                "tags": _tag_map(rt.get("Tags")),
                "routes": routes,
                "associations": associations,
            }
        )

    vpc_endpoints: list[dict[str, Any]] = []
    if include_endpoints:
        ep_resp = ec2.describe_vpc_endpoints(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
        )
        for ep in ep_resp.get("VpcEndpoints") or []:
            tags = _tag_map(ep.get("Tags"))
            groups = ep.get("Groups") or []
            is_cp = _is_rosa_hcp_control_plane_vpc_endpoint(tags, cluster_id, name)
            vpc_endpoints.append(
                {
                    "id": ep["VpcEndpointId"],
                    "service_name": ep.get("ServiceName"),
                    "type": ep.get("VpcEndpointType"),
                    "subnet_ids": ep.get("SubnetIds") or [],
                    "tags": tags,
                    "rosa_hcp_control_plane": is_cp,
                    "adoptable": not is_cp,
                    "security_group_ids": [
                        str(g["GroupId"]) for g in groups if g.get("GroupId")
                    ],
                    "endpoint_groups": [
                        {"GroupId": g.get("GroupId"), "GroupName": g.get("GroupName")}
                        for g in groups
                    ],
                }
            )

    rosa_hcp_control_plane_vpc_endpoint: dict[str, Any] | None = None
    for ep in vpc_endpoints:
        if ep.get("rosa_hcp_control_plane"):
            rosa_hcp_control_plane_vpc_endpoint = {
                "id": ep["id"],
                "service_name": ep.get("service_name"),
                "additional_control_plane_security_group_ids": _additional_control_plane_security_group_ids(
                    ep.get("endpoint_groups") or []
                ),
            }
            break

    security_groups: list[dict[str, Any]] = []
    if include_security_groups:
        sg_resp = ec2.describe_security_groups(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
        )
        cluster_pat = re.compile(re.escape(name), re.I) if name else None
        infra_pat = re.compile(re.escape(infra_id), re.I) if infra_id else None
        for sg in sg_resp.get("SecurityGroups") or []:
            if sg.get("GroupName") == "default":
                continue
            tags = _tag_map(sg.get("Tags"))
            text = json.dumps(tags) + sg.get("GroupName", "") + sg.get("Description", "")
            if cluster_pat and not cluster_pat.search(text) and infra_pat and not infra_pat.search(text):
                if not tags.get("kubernetes.io/cluster/" + infra_id):
                    continue
            security_groups.append(
                {
                    "id": sg["GroupId"],
                    "name": sg.get("GroupName"),
                    "description": sg.get("Description"),
                    "tags": tags,
                }
            )

    flow_logs: list[dict[str, Any]] = []
    if include_flow_logs:
        fl_resp = ec2.describe_flow_logs(
            Filters=[{"Name": "resource-id", "Values": [vpc_id]}]
        )
        for fl in fl_resp.get("FlowLogs") or []:
            flow_logs.append(
                {
                    "id": fl["FlowLogId"],
                    "traffic_type": fl.get("TrafficType"),
                    "log_destination": fl.get("LogDestination"),
                    "tags": _tag_map(fl.get("Tags")),
                }
            )

    tgw_attachments: list[dict[str, Any]] = []
    if include_tgw:
        tgw_resp = ec2.describe_transit_gateway_vpc_attachments(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
        )
        for att in tgw_resp.get("TransitGatewayVpcAttachments") or []:
            if att.get("State") in ("deleted", "deleting"):
                continue
            tgw_attachments.append(
                {
                    "id": att["TransitGatewayAttachmentId"],
                    "transit_gateway_id": att.get("TransitGatewayId"),
                    "subnet_ids": att.get("SubnetIds") or [],
                    "state": att.get("State"),
                    "tags": _tag_map(att.get("Tags")),
                }
            )

    warnings: list[str] = []
    if not private_cluster and not public_subnets:
        warnings.append("Cluster is public but no public subnets were identified.")
    if private_cluster and public_subnets:
        warnings.append("Cluster marked private but public subnets exist in inventory.")

    hcp_order = _rosa_hcp_subnet_order(private_subnets, public_subnets, private_cluster)

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "cluster_name": name,
            "cluster_id": cluster_id,
            "infra_id": infra_id,
            "region": region,
            "private_cluster": private_cluster,
            "cluster_state": cluster.get("state"),
        },
        "vpc": {
            "id": vpc_id,
            "cidr_block": vpc.get("CidrBlock"),
            "tags": vpc_tags,
        },
        "subnets": subnets,
        "internet_gateways": igws,
        "nat_gateways": nat_gateways,
        "route_tables": route_tables,
        "vpc_endpoints": vpc_endpoints,
        "security_groups": security_groups,
        "transit_gateway_attachments": tgw_attachments,
        "flow_logs": flow_logs,
        "warnings": warnings,
        "rosa_hcp_wiring": hcp_order,
        "rosa_hcp_control_plane_vpc_endpoint": rosa_hcp_control_plane_vpc_endpoint,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cluster-json", type=Path, required=True)
    parser.add_argument("--machinepools-json", type=Path, default=None)
    parser.add_argument("--ingress-json", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skip-endpoints", action="store_true")
    parser.add_argument("--skip-security-groups", action="store_true")
    parser.add_argument("--skip-flow-logs", action="store_true")
    parser.add_argument("--skip-tgw", action="store_true")
    args = parser.parse_args()

    cluster = json.loads(args.cluster_json.read_text(encoding="utf-8"))
    pools: Any = []
    ingress: Any = []
    if args.machinepools_json and args.machinepools_json.is_file():
        pools = json.loads(args.machinepools_json.read_text(encoding="utf-8"))
    if args.ingress_json and args.ingress_json.is_file():
        ingress = json.loads(args.ingress_json.read_text(encoding="utf-8"))

    try:
        inv = discover(
            cluster,
            pools,
            ingress,
            include_endpoints=not args.skip_endpoints,
            include_security_groups=not args.skip_security_groups,
            include_flow_logs=not args.skip_flow_logs,
            include_tgw=not args.skip_tgw,
        )
    except (ClientError, BotoCoreError) as exc:
        raise SystemExit(f"AWS API error: {exc}") from exc

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(inv, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output.resolve()}")


if __name__ == "__main__":
    main()
