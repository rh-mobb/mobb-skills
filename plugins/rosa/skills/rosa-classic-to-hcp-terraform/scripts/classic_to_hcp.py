#!/usr/bin/env python3
# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0
"""Map ROSA Classic cluster JSON to terraform-redhat/rosa-hcp/rhcs stack files."""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
from dataclasses import dataclass, field, field
from pathlib import Path
from typing import Any

from idp_terraform import (
    format_idp_briefing,
    format_identity_providers_classic_tf,
    format_identity_providers_tfvars,
    generate_idp_artifacts,
    load_inventory as load_idp_inventory,
)

LONGEST_OPERATOR_SUFFIX = "openshift-cloud-network-config-controller-cloud-credentials"
MAX_IAM_PREFIX_LEN = 32
INFRA_TAINT = {
    "key": "node-role.kubernetes.io/infra",
    "value": "reserved",
    "schedule_type": "NoSchedule",
}
INFRA_LABEL = {"node-role.kubernetes.io/infra": ""}


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _items(doc: Any) -> list[dict[str, Any]]:
    if isinstance(doc, list):
        return doc
    if isinstance(doc, dict):
        for key in ("items", "body", "machine_pools"):
            if key in doc and isinstance(doc[key], list):
                return doc[key]
    return []


def _cluster_is_hcp(cluster: dict[str, Any]) -> bool:
    hs = cluster.get("hypershift") or {}
    return bool(hs.get("enabled"))


def _region(cluster: dict[str, Any]) -> str:
    region = cluster.get("region") or {}
    if isinstance(region, dict):
        return region.get("id") or region.get("name") or ""
    return str(region)


def _openshift_version(cluster: dict[str, Any]) -> str:
    version = cluster.get("version") or {}
    if isinstance(version, dict):
        return (
            version.get("raw_id")
            or version.get("id")
            or cluster.get("openshift_version")
            or ""
        )
    return str(version) if version else ""


def _channel_group(cluster: dict[str, Any]) -> str:
    version = cluster.get("version") or {}
    if isinstance(version, dict) and version.get("channel_group"):
        return str(version["channel_group"])
    return "stable"


def _network_field(cluster: dict[str, Any], key: str) -> str | None:
    net = cluster.get("network") or {}
    val = net.get(key)
    return str(val) if val not in (None, "") else None


def _host_prefix(cluster: dict[str, Any]) -> int | None:
    net = cluster.get("network") or {}
    hp = net.get("host_prefix")
    if hp is None:
        return None
    return int(hp)


def _parse_cidrs(cluster: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    return (
        _network_field(cluster, "machine_cidr"),
        _network_field(cluster, "pod_cidr"),
        _network_field(cluster, "service_cidr"),
    )


def validate_cluster_cidrs(
    machine: str | None, pod: str | None, service: str | None
) -> None:
    missing = [
        name
        for name, val in (
            ("machine_cidr", machine),
            ("pod_cidr", pod),
            ("service_cidr", service),
        )
        if not val
    ]
    if missing:
        raise SystemExit(f"Classic cluster missing network CIDR(s): {', '.join(missing)}")
    nets = {
        "machine_cidr": ipaddress.ip_network(machine, strict=False),
        "pod_cidr": ipaddress.ip_network(pod, strict=False),
        "service_cidr": ipaddress.ip_network(service, strict=False),
    }
    pairs = [
        ("machine_cidr", "pod_cidr"),
        ("machine_cidr", "service_cidr"),
        ("pod_cidr", "service_cidr"),
    ]
    for a, b in pairs:
        if nets[a].overlaps(nets[b]):
            raise SystemExit(f"Classic cluster CIDR overlap: {a} and {b}")


def validate_vpc_contains_machine(vpc_cidr: str, machine_cidr: str) -> None:
    vpc = ipaddress.ip_network(vpc_cidr, strict=False)
    machine = ipaddress.ip_network(machine_cidr, strict=False)
    if not (machine.subnet_of(vpc) or machine == vpc):
        raise SystemExit(
            f"machine_cidr {machine_cidr} must equal or be a subset of vpc_cidr {vpc_cidr}"
        )


def _is_infra_pool(pool: dict[str, Any]) -> bool:
    pool_id = (pool.get("id") or pool.get("name") or "").lower()
    if pool_id == "infra" or pool_id.startswith("infra-"):
        return True
    labels = pool.get("labels") or {}
    return "node-role.kubernetes.io/infra" in labels


def _pool_azs(pool: dict[str, Any], cluster: dict[str, Any]) -> list[str]:
    azs = pool.get("availability_zones") or pool.get("availabilityZones") or []
    if azs:
        return list(azs)
    if cluster.get("multi_az"):
        return []
    region = _region(cluster)
    if region:
        return [f"{region}a"]
    return []


def _cluster_azs(worker_pool: dict[str, Any], cluster: dict[str, Any]) -> list[str]:
    azs = _pool_azs(worker_pool, cluster)
    if azs:
        return sorted(azs)
    if cluster.get("multi_az"):
        region = _region(cluster)
        return [f"{region}a", f"{region}b", f"{region}c"]
    region = _region(cluster)
    return [f"{region}a"] if region else []


def _worker_disk_gib(pool: dict[str, Any]) -> int | None:
    rv = pool.get("root_volume") or pool.get("rootVolume") or {}
    size = rv.get("size")
    if size is None:
        return None
    if isinstance(size, str):
        m = re.match(r"^(\d+)", size)
        return int(m.group(1)) if m else None
    return int(size)


def _sanitize_cluster_name(name: str) -> str:
    cleaned = re.sub(r"[^a-z0-9-]", "-", name.lower())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned[:54] or "rosa-hcp"


def _iam_prefix(cluster_name: str) -> tuple[str, str | None]:
    """Return (prefix, note_if_shortened)."""
    base = _sanitize_cluster_name(cluster_name)
    test_name = f"{base}-{LONGEST_OPERATOR_SUFFIX}"
    if len(test_name) <= 64:
        prefix = base[:MAX_IAM_PREFIX_LEN]
        note = None
        if prefix != base:
            note = f"IAM prefix shortened from {base!r} to {prefix!r} for 64-char role name limit."
        return prefix, note
    # shorten until operator role fits
    for length in range(min(len(base), MAX_IAM_PREFIX_LEN), 0, -1):
        candidate = base[:length]
        if len(f"{candidate}-{LONGEST_OPERATOR_SUFFIX}") <= 64:
            return candidate, (
                f"IAM prefix shortened from {base!r} to {candidate!r} for 64-char role name limit."
            )
    return base[:8], f"IAM prefix aggressively shortened to fit operator role names."


def _version_tuple(version: str) -> tuple[int, int, int]:
    nums = [int(x) for x in re.findall(r"\d+", version)]
    if len(nums) < 2:
        raise SystemExit(f"Invalid OpenShift version: {version!r}")
    patch = nums[2] if len(nums) > 2 else 0
    return nums[0], nums[1], patch


def _minor_line(version: str) -> str:
    major, minor, _ = _version_tuple(version)
    return f"{major}.{minor}"


def _collect_hosted_cp_versions(versions_doc: Any) -> list[str]:
    hosted: list[str] = []
    for item in _items(versions_doc):
        if isinstance(item, dict):
            vid = item.get("raw_id") or item.get("id") or item.get("version")
            if vid:
                hosted.append(str(vid))
        elif isinstance(item, str):
            hosted.append(item)
    if not hosted and isinstance(versions_doc, dict):
        for key in ("items", "versions"):
            for item in versions_doc.get(key) or []:
                if isinstance(item, dict):
                    vid = item.get("raw_id") or item.get("id")
                    if vid:
                        hosted.append(str(vid))
    return sorted(set(hosted), key=_version_tuple)


def _latest_patch_by_minor(hosted: list[str]) -> dict[str, str]:
    by_minor: dict[str, list[str]] = {}
    for version in hosted:
        by_minor.setdefault(_minor_line(version), []).append(version)
    return {minor: max(versions, key=_version_tuple) for minor, versions in by_minor.items()}


@dataclass
class VersionChoice:
    minor_line: str
    version: str
    description: str


@dataclass
class VersionPlan:
    classic_version: str
    chosen: str
    channel: str
    note: str | None
    needs_user_choice: bool
    recommended: str
    choices: list[VersionChoice] = field(default_factory=list)


def _pick_same_minor_patch(classic_version: str, hosted: list[str]) -> str:
    classic_mk = _minor_line(classic_version)
    ct = _version_tuple(classic_version)
    if classic_version in hosted:
        return classic_version
    same_minor = [v for v in hosted if _minor_line(v) == classic_mk]
    if not same_minor:
        raise SystemExit(f"No hosted-cp versions on Classic minor line {classic_mk}.")
    at_or_above = [v for v in same_minor if _version_tuple(v) >= ct]
    if at_or_above:
        return max(at_or_above, key=_version_tuple)
    return max(same_minor, key=_version_tuple)


def plan_hcp_version(
    classic_version: str,
    channel_group: str,
    versions_doc: Any,
    *,
    user_version: str | None = None,
) -> VersionPlan:
    """Pick HCP OpenShift version from hosted-cp catalog vs Classic cluster version."""
    hosted = _collect_hosted_cp_versions(versions_doc)
    if not hosted:
        raise SystemExit("hosted-cp versions JSON is empty; run `rosa list versions --hosted-cp`.")

    if user_version:
        if user_version not in hosted:
            raise SystemExit(
                f"--openshift-version {user_version!r} is not in the hosted-cp catalog "
                f"({len(hosted)} versions loaded)."
            )
        mk = _minor_line(user_version)
        return VersionPlan(
            classic_version=classic_version,
            chosen=user_version,
            channel=f"{channel_group}-{mk}",
            note=None,
            needs_user_choice=False,
            recommended=user_version,
        )

    latest_by_minor = _latest_patch_by_minor(hosted)
    classic_mk = _minor_line(classic_version)
    ct_minor = _version_tuple(classic_mk + ".0")
    newer_minor_lines = sorted(
        [
            mk
            for mk in latest_by_minor
            if _version_tuple(mk + ".0") > ct_minor
        ],
        key=lambda mk: _version_tuple(mk + ".0"),
    )

    if not newer_minor_lines:
        chosen = _pick_same_minor_patch(classic_version, hosted)
        note = None
        if chosen != classic_version:
            note = (
                f"Hosted-cp version: Classic {classic_version} -> HCP {chosen} "
                f"(nearest patch on {classic_mk}; exact match not on hosted-cp)."
            )
        return VersionPlan(
            classic_version=classic_version,
            chosen=chosen,
            channel=f"{channel_group}-{classic_mk}",
            note=note,
            needs_user_choice=False,
            recommended=chosen,
        )

    choices: list[VersionChoice] = []
    if classic_mk in latest_by_minor:
        recommended = _pick_same_minor_patch(classic_version, hosted)
        choices.append(
            VersionChoice(
                classic_mk,
                recommended,
                f"Stay on Classic minor {classic_mk} (latest hosted-cp patch)",
            )
        )
    else:
        recommended = latest_by_minor[newer_minor_lines[0]]
        choices.append(
            VersionChoice(
                newer_minor_lines[0],
                recommended,
                f"No {classic_mk} on hosted-cp; closest newer line",
            )
        )

    for mk in newer_minor_lines:
        if any(c.minor_line == mk for c in choices):
            continue
        choices.append(
            VersionChoice(
                mk,
                latest_by_minor[mk],
                f"Upgrade to OpenShift {mk} (latest hosted-cp patch)",
            )
        )

    return VersionPlan(
        classic_version=classic_version,
        chosen=recommended,
        channel=f"{channel_group}-{_minor_line(recommended)}",
        note=(
            f"Classic runs {classic_version}; hosted-cp also offers newer minor lines. "
            "Confirm target OpenShift version before --write."
        ),
        needs_user_choice=True,
        recommended=recommended,
        choices=choices,
    )


def format_version_plan(plan: VersionPlan) -> str:
    lines = [
        "## OpenShift version (hosted-cp)",
        "",
        f"- Classic cluster version: `{plan.classic_version}`",
        f"- Proposed for Terraform (preview): `{plan.chosen}` ({plan.channel})",
    ]
    if plan.note:
        lines.append(f"- Note: {plan.note}")
    if plan.needs_user_choice:
        lines.append("")
        lines.append(
            "**Operator must choose** a hosted-cp version before `--write` "
            "(pass `--openshift-version`). Newest patch per minor line:"
        )
        for choice in plan.choices:
            rec = " (recommended default)" if choice.version == plan.recommended else ""
            lines.append(
                f"  - **{choice.minor_line}** -> `{choice.version}` — {choice.description}{rec}"
            )
    return "\n".join(lines)


def _resolve_hcp_version(
    classic_version: str, channel_group: str, versions_doc: Any, *, user_version: str | None = None
) -> tuple[str, str, str | None]:
    """Return (openshift_version, channel, substitution_note). Prefer plan_hcp_version()."""
    plan = plan_hcp_version(classic_version, channel_group, versions_doc, user_version=user_version)
    return plan.chosen, plan.channel, plan.note


def _round_replicas(total: int, az_count: int, minimum: int) -> tuple[int, str | None]:
    if az_count < 1:
        az_count = 1
    adjusted = max(total, minimum)
    remainder = adjusted % az_count
    if remainder:
        adjusted += az_count - remainder
        return adjusted, (
            f"Replica count rounded up from {total} to {adjusted} "
            f"to divide evenly across {az_count} AZ(s)."
        )
    if adjusted != total:
        return adjusted, f"Replica count raised from {total} to {adjusted} (minimum {minimum})."
    return adjusted, None


def _divide_per_az(total: int, az_count: int, round_up: bool = True) -> tuple[int, str | None]:
    if az_count < 1:
        return total, None
    if total % az_count == 0:
        return total // az_count, None
    per = total // az_count
    if round_up:
        per += 1
    note = (
        f"Per-AZ replica count for {total} nodes / {az_count} AZs "
        f"set to {per} ({'rounded up' if round_up else 'truncated'})."
    )
    return per, note


def _private_cluster(cluster: dict[str, Any], ingresses: list[dict[str, Any]]) -> bool:
    aws = cluster.get("aws") or {}
    if aws.get("private_link") or aws.get("private"):
        return True
    for ing in ingresses:
        if ing.get("default") or ing.get("default_route"):
            if ing.get("listening") == "internal" or ing.get("private"):
                return True
            listening = (ing.get("listening_method") or ing.get("listeningMethod") or "").lower()
            if listening == "internal":
                return True
    return False


def _default_ingress_method(ingresses: list[dict[str, Any]], private: bool) -> str:
    for ing in ingresses:
        if ing.get("default") or ing.get("default_route"):
            listening = (ing.get("listening_method") or ing.get("listeningMethod") or "").lower()
            if listening in ("internal", "external"):
                return listening
            if ing.get("private") or ing.get("listening") == "internal":
                return "internal"
    return "internal" if private else "external"


def _taints_hcp(pool: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for t in pool.get("taints") or []:
        effect = t.get("effect") or t.get("schedule_type") or "NoSchedule"
        out.append(
            {
                "key": t.get("key", ""),
                "value": t.get("value") or "",
                "schedule_type": effect.replace("NoSchedule", "NoSchedule")
                if effect.startswith("No")
                else effect,
            }
        )
        if effect in ("NoSchedule", "PreferNoSchedule", "NoExecute"):
            out[-1]["schedule_type"] = effect
    return out


@dataclass
class PoolPlan:
    name: str
    az_index: int | None
    az: str
    replicas: int
    instance_type: str
    labels: dict[str, str] = field(default_factory=dict)
    taints: list[dict[str, str]] = field(default_factory=list)
    autoscaling: dict[str, Any] | None = None
    subnet_comment: str = ""
    is_infra: bool = False


@dataclass
class MappingResult:
    source_cluster_id: str
    source_cluster_name: str
    target_cluster_name: str
    region: str
    openshift_version: str
    channel: str
    multi_az: bool
    azs: list[str]
    private: bool
    default_ingress_listening_method: str
    service_cidr: str
    machine_cidr: str | None
    pod_cidr: str | None
    host_prefix: int | None
    replicas: int
    compute_machine_type: str
    worker_disk_size: int | None
    account_role_prefix: str
    operator_role_prefix: str
    machine_pools: dict[str, dict[str, Any]]
    version_plan: VersionPlan
    notes: list[str] = field(default_factory=list)
    unmapped: list[str] = field(default_factory=list)
    module_version: str = "1.7.6"


def build_mapping(
    cluster: dict[str, Any],
    pools_doc: Any,
    ingress_doc: Any,
    versions_doc: Any,
    *,
    target_cluster_name: str,
    include_infra: bool,
    reuse_cidrs: bool,
    module_version: str,
    openshift_version: str | None = None,
) -> MappingResult:
    if _cluster_is_hcp(cluster):
        raise SystemExit("Cluster is already ROSA HCP (hypershift.enabled=true).")

    machine_c, pod_c, service_c = _parse_cidrs(cluster)
    validate_cluster_cidrs(machine_c, pod_c, service_c)

    pools = _items(pools_doc)
    ingresses = _items(ingress_doc)
    classic_version = _openshift_version(cluster)
    ch_group = _channel_group(cluster)
    version_plan = plan_hcp_version(
        classic_version,
        ch_group,
        versions_doc,
        user_version=openshift_version,
    )
    hcp_version = version_plan.chosen
    channel = version_plan.channel
    ver_note = version_plan.note

    compute_pools = [p for p in pools if not _is_infra_pool(p)]
    infra_pools = [p for p in pools if _is_infra_pool(p)]

    azs = _cluster_azs(
        next(
            (
                p
                for p in compute_pools
                if (p.get("id") or "").lower() == "worker"
            ),
            compute_pools[0] if compute_pools else {},
        ),
        cluster,
    )

    if include_infra and not infra_pools:
        cp = cluster.get("nodes") or {}
        infra_count = int(cp.get("infra") or 0)
        if infra_count:
            imt = cp.get("infra_machine_type") or {}
            instance = imt.get("id") if isinstance(imt, dict) else str(imt or "r5.xlarge")
            infra_pools = [
                {
                    "id": "infra",
                    "replicas": infra_count,
                    "instance_type": instance,
                    "availability_zones": azs,
                }
            ]

    worker = next((p for p in compute_pools if (p.get("id") or "").lower() == "worker"), None)
    if worker is None and compute_pools:
        worker = compute_pools[0]
    if worker is None:
        raise SystemExit("No worker/compute machine pool found on Classic cluster.")

    if not azs:
        azs = _cluster_azs(worker, cluster)
    multi_az = len(azs) > 1
    az_count = len(azs) or 1

    notes: list[str] = []
    if ver_note:
        notes.append(ver_note)

    synthesized_infra = bool(
        include_infra
        and infra_pools
        and str(infra_pools[0].get("id") or "") == "infra"
    )

    prefix, prefix_note = _iam_prefix(target_cluster_name)
    if prefix_note:
        notes.append(prefix_note)

    private = _private_cluster(cluster, ingresses)
    ingress_method = _default_ingress_method(ingresses, private)

    raw_replicas = int(worker.get("replicas") or worker.get("replica") or 0)
    min_replicas = 2 if not multi_az else az_count
    replicas, rep_note = _round_replicas(raw_replicas, az_count, min_replicas)
    if rep_note:
        notes.append(rep_note)

    per_worker_az = replicas // az_count if az_count else replicas
    if multi_az:
        notes.append(
            f"Default pool will materialize as worker-1 .. worker-{az_count} "
            f"with {per_worker_az} replica(s) each (total {replicas})."
        )
    else:
        notes.append(f"Default pool: single AZ {azs[0]}, {replicas} replica(s).")

    extra_pools = [p for p in compute_pools if p is not worker]
    machine_pools: dict[str, dict[str, Any]] = {}
    mp_index = 0

    def add_machine_pool(key: str, spec: dict[str, Any]) -> None:
        nonlocal mp_index
        machine_pools[key] = spec
        mp_index += 1

    for pool in extra_pools:
        pool_id = pool.get("id") or pool.get("name") or "pool"
        instance = pool.get("instance_type") or pool.get("instanceType") or "m5.xlarge"
        total_rep = int(pool.get("replicas") or 0)
        labels = dict(pool.get("labels") or {})
        taints = _taints_hcp(pool)
        autoscaling = pool.get("autoscaling") or {}
        autoscale_enabled = bool(autoscaling.get("enabled"))

        if multi_az:
            per_az, div_note = _divide_per_az(total_rep, az_count, round_up=True)
            if div_note:
                notes.append(f"Pool {pool_id}: {div_note}")
            for idx, az in enumerate(azs, start=1):
                key = f"{pool_id.replace('-', '_')}_{idx}"
                name = f"{pool_id}-{idx}"
                spec: dict[str, Any] = {
                    "name": name,
                    "subnet_id": "",
                    "openshift_version": hcp_version,
                    "aws_node_pool": {
                        "instance_type": instance,
                        "tags": {},
                    },
                }
                if labels:
                    spec["labels"] = labels
                if taints:
                    spec["taints"] = taints
                if autoscale_enabled:
                    min_r = int(autoscaling.get("min_replicas") or autoscaling.get("min_replica") or 0)
                    max_r = int(autoscaling.get("max_replicas") or autoscaling.get("max_replica") or 0)
                    min_per, _ = _divide_per_az(min_r, az_count, round_up=True)
                    max_per, _ = _divide_per_az(max_r, az_count, round_up=True)
                    spec["autoscaling"] = {
                        "enabled": True,
                        "min_replicas": min_per,
                        "max_replicas": max_per,
                    }
                else:
                    spec["replicas"] = per_az
                add_machine_pool(key, spec)
                notes.append(
                    f"Additional pool {name} -> AZ {az} (private subnet for worker-{idx})."
                )
        else:
            az = azs[0]
            key = pool_id.replace("-", "_")
            spec = {
                "name": pool_id,
                "subnet_id": "",
                "openshift_version": hcp_version,
                "aws_node_pool": {"instance_type": instance, "tags": {}},
            }
            if labels:
                spec["labels"] = labels
            if taints:
                spec["taints"] = taints
            if autoscale_enabled:
                spec["autoscaling"] = {
                    "enabled": True,
                    "min_replicas": int(
                        autoscaling.get("min_replicas") or autoscaling.get("min_replica") or 0
                    ),
                    "max_replicas": int(
                        autoscaling.get("max_replicas") or autoscaling.get("max_replica") or 0
                    ),
                }
            else:
                spec["replicas"] = total_rep
            add_machine_pool(key, spec)
            notes.append(f"Additional pool {pool_id} -> AZ {az} (single private subnet).")

        disk = _worker_disk_gib(pool)
        default_disk = _worker_disk_gib(worker)
        if disk and disk != default_disk:
            notes.append(
                f"Pool {pool_id} root disk {disk} GiB — not configurable on additional HCP pools; adjust manually."
            )

        if autoscale_enabled:
            notes.append(
                f"Pool {pool_id} autoscaling on Classic — verify HCP pool autoscaling limits after apply."
            )

    if include_infra and infra_pools:
        infra = infra_pools[0]
        instance = infra.get("instance_type") or infra.get("instanceType") or "r5.xlarge"
        if multi_az:
            per_az = int(infra.get("replicas") or 1)
            if per_az * az_count != int(infra.get("replicas") or 0):
                per_az, _ = _divide_per_az(int(infra.get("replicas") or az_count), az_count, round_up=False)
                if per_az < 1:
                    per_az = 1
            for idx, az in enumerate(azs, start=1):
                key = f"infra_{idx}"
                spec = {
                    "name": f"infra-{idx}",
                    "subnet_id": "",
                    "openshift_version": hcp_version,
                    "replicas": per_az,
                    "labels": dict(INFRA_LABEL),
                    "taints": [dict(INFRA_TAINT)],
                    "aws_node_pool": {"instance_type": instance, "tags": {}},
                }
                add_machine_pool(key, spec)
        else:
            spec = {
                "name": "infra-1",
                "subnet_id": "",
                "openshift_version": hcp_version,
                "replicas": 2,
                "labels": dict(INFRA_LABEL),
                "taints": [dict(INFRA_TAINT)],
                "aws_node_pool": {"instance_type": instance, "tags": {}},
            }
            add_machine_pool("infra_1", spec)
        if synthesized_infra:
            notes.append(
                "Synthesized infra machine pools from Classic nodes.infra "
                "(no infra MachinePool in ROSA API)."
            )

    unmapped: list[str] = []
    if cluster.get("fips") or (cluster.get("fips_enabled")):
        unmapped.append("FIPS mode — configure separately on HCP if required.")
    aws = cluster.get("aws") or {}
    if aws.get("subnet_ids"):
        unmapped.append(f"Classic subnet IDs (do not reuse): {', '.join(aws['subnet_ids'])}")
    if worker.get("autoscaling", {}).get("enabled"):
        unmapped.append(
            "Default worker pool autoscaling on Classic — not mapped (module cluster_autoscaler unavailable)."
        )
    for label_k, label_v in (worker.get("labels") or {}).items():
        unmapped.append(f"Default pool label {label_k}={label_v} — not on module default pool.")
    for t in worker.get("taints") or []:
        unmapped.append(f"Default pool taint {t} — not on module default pool.")

    cp = cluster.get("nodes") or {}
    if cp.get("master") or cp.get("compute") is not None:
        unmapped.append(
            f"Classic control plane / infra node counts: {json.dumps(cp)} — HCP has no customer control plane."
        )

    if not reuse_cidrs:
        unmapped.append(
            f"Do not reuse Classic machine CIDR {machine_c} or pod CIDR {pod_c} when routing overlaps."
        )

    return MappingResult(
        source_cluster_id=str(cluster.get("id") or ""),
        source_cluster_name=str(cluster.get("name") or ""),
        target_cluster_name=target_cluster_name,
        region=_region(cluster),
        openshift_version=hcp_version,
        channel=channel,
        multi_az=multi_az,
        azs=azs,
        private=private,
        default_ingress_listening_method=ingress_method,
        service_cidr=service_c or "",
        machine_cidr=machine_c if reuse_cidrs else None,
        pod_cidr=pod_c if reuse_cidrs else None,
        host_prefix=_host_prefix(cluster) if reuse_cidrs else None,
        replicas=replicas,
        compute_machine_type=worker.get("instance_type")
        or worker.get("instanceType")
        or "m5.xlarge",
        worker_disk_size=_worker_disk_gib(worker),
        account_role_prefix=prefix,
        operator_role_prefix=prefix,
        machine_pools=machine_pools,
        version_plan=version_plan,
        notes=notes,
        unmapped=unmapped,
        module_version=module_version,
    )


def format_dry_run(result: MappingResult, classic_machine: str, classic_pod: str) -> str:
    lines = [
        format_version_plan(result.version_plan),
        "",
        f"Source: {result.source_cluster_name} ({result.source_cluster_id})",
        f"Target cluster name: {result.target_cluster_name}",
        f"Topology: {'multi-AZ' if result.multi_az else 'single-AZ'} ({', '.join(result.azs)})",
        f"Private: {result.private}",
        f"OpenShift: {result.openshift_version} ({result.channel})",
        f"Default pool: {result.compute_machine_type}, {result.replicas} replicas total",
        f"CIDRs — machine: {classic_machine}, pod: {classic_pod}, service: {result.service_cidr}",
        f"IAM prefix: {result.account_role_prefix}",
        f"Additional machine_pools keys: {', '.join(result.machine_pools.keys()) or '(none)'}",
        "",
        "Notes:",
    ]
    lines.extend(f"  - {n}" for n in result.notes)
    if result.unmapped:
        lines.append("")
        lines.append("Unmapped / operator actions:")
        lines.extend(f"  - {u}" for u in result.unmapped)
    return "\n".join(lines)


def _hcl_string(val: str) -> str:
    escaped = val.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _hcl_bool(val: bool) -> str:
    return "true" if val else "false"


def write_stack(
    result: MappingResult,
    output_dir: Path,
    reuse_cidrs: bool,
    *,
    idps_json: Path | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    idp_inv: dict[str, Any] | None = None
    idp_active: dict[str, Any] = {}
    idp_htpasswd_tf = ""
    idp_optional_tf = ""
    idp_migration_md = ""
    needs_random = False
    if idps_json and idps_json.is_file():
        idp_inv = load_idp_inventory(idps_json)
        idp_active, idp_htpasswd_tf, idp_optional_tf, idp_migration_md, needs_random = (
            generate_idp_artifacts(idp_inv, target_cluster_name=result.target_cluster_name)
        )

    random_block = ""
    if needs_random:
        random_block = """
    random = {
      source  = "hashicorp/random"
      version = ">= 3.6.0"
    }"""

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
    }}{random_block}
  }}
}}

provider "aws" {{
  region = {_hcl_string(result.region)}
}}

provider "rhcs" {{
  # Set RHCS_TOKEN in the environment (from console.redhat.com/openshift/token).
}}
''',
        encoding="utf-8",
    )

    idp_module_line = "  identity_providers  = var.identity_providers"
    if idp_active:
        idp_module_line = (
            "  identity_providers  = merge(var.identity_providers, local.identity_providers_classic)"
        )

    (output_dir / "main.tf").write_text(
        f'''module "rosa_hcp" {{
  source  = "terraform-redhat/rosa-hcp/rhcs"
  version = "{result.module_version}"

  cluster_name      = var.cluster_name
  openshift_version = var.openshift_version
  channel           = var.channel

  aws_subnet_ids         = var.aws_subnet_ids
  aws_availability_zones = var.aws_availability_zones

  private                          = var.private
  default_ingress_listening_method = var.default_ingress_listening_method

  machine_cidr  = var.machine_cidr
  pod_cidr      = var.pod_cidr
  service_cidr  = var.service_cidr
  host_prefix   = var.host_prefix

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

  machine_pools       = var.machine_pools
{idp_module_line}
}}
''',
        encoding="utf-8",
    )

    (output_dir / "variables.tf").write_text(
        '''variable "cluster_name" {
  type = string
}

variable "openshift_version" {
  type = string
}

variable "channel" {
  type = string
}

variable "vpc_cidr" {
  type        = string
  description = "Target VPC CIDR. machine_cidr must equal or be a subset of this CIDR."
  default     = ""
}

variable "aws_subnet_ids" {
  type        = list(string)
  description = "Private subnet per AZ (and public per AZ when private=false). Every subnet CIDR must fall inside machine_cidr."
  default     = []
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
  default = ""

  validation {
    condition = (
      var.vpc_cidr == "" || var.machine_cidr == "" ||
      var.machine_cidr == var.vpc_cidr ||
      can(cidrcontains(var.vpc_cidr, var.machine_cidr))
    )
    error_message = "machine_cidr must equal or be a subset of vpc_cidr when both are set."
  }
}

variable "pod_cidr" {
  type    = string
  default = ""
}

variable "service_cidr" {
  type = string
}

variable "host_prefix" {
  type    = number
  default = null
}

variable "replicas" {
  type = number
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

variable "operator_role_prefix" {
  type = string
}

variable "admin_credentials_username" {
  type    = string
  default = ""
}

variable "admin_credentials_password" {
  type      = string
  sensitive = true
  default   = ""
}

variable "machine_pools" {
  type    = any
  default = {}
}

variable "identity_providers" {
  type        = any
  default     = {}
  description = "HCP identity providers (htpasswd replicated from Classic when --idps-json is used)."
}
''',
        encoding="utf-8",
    )

    az_hcl = ", ".join(_hcl_string(a) for a in result.azs)
    mp_hcl = _format_machine_pools_hcl(result.machine_pools, result.multi_az, result.azs)

    machine_line = _hcl_string(result.machine_cidr) if result.machine_cidr else '""'
    pod_line = _hcl_string(result.pod_cidr) if result.pod_cidr else '""'
    hp_line = str(result.host_prefix) if result.host_prefix is not None else "null"
    disk_line = str(result.worker_disk_size) if result.worker_disk_size else "null"

    tfvars = f'''# Generated from Classic cluster {result.source_cluster_name} ({result.source_cluster_id})
# Fill empty values before terraform apply.

vpc_cidr = "" # Target VPC CIDR; machine_cidr must equal or be a subset.

aws_subnet_ids = [] # {"One private subnet per AZ in order worker-1..N" if result.multi_az else f"Private subnet for {result.azs[0]}"}{"; add public subnet per AZ when private=false" if not result.private else ""}

aws_availability_zones = [{az_hcl}]

cluster_name      = {_hcl_string(result.target_cluster_name)}
openshift_version = {_hcl_string(result.openshift_version)}
channel           = {_hcl_string(result.channel)}

private                          = {_hcl_bool(result.private)}
default_ingress_listening_method = {_hcl_string(result.default_ingress_listening_method)}

machine_cidr = {machine_line}
pod_cidr     = {pod_line}
service_cidr = {_hcl_string(result.service_cidr)}
host_prefix  = {hp_line}

replicas             = {result.replicas}
compute_machine_type = {_hcl_string(result.compute_machine_type)}
worker_disk_size     = {disk_line}

account_role_prefix  = {_hcl_string(result.account_role_prefix)}
operator_role_prefix = {_hcl_string(result.operator_role_prefix)}

admin_credentials_username = "admin"
admin_credentials_password = "REPLACE-ME-14chars-min" # set before production apply (RHCS min 14 chars)

machine_pools = {mp_hcl}
'''
    idp_tfvars = format_identity_providers_tfvars(idp_active)
    tfvars = tfvars.rstrip() + "\n\n" + idp_tfvars
    (output_dir / "terraform.tfvars").write_text(tfvars, encoding="utf-8")

    classic_tf = output_dir / "identity_providers_classic.tf"
    if idp_active:
        classic_tf.write_text(format_identity_providers_classic_tf(idp_active), encoding="utf-8")
    elif idp_inv is not None:
        classic_tf.write_text(
            "locals {\n  identity_providers_classic = {}\n}\n",
            encoding="utf-8",
        )
    elif classic_tf.is_file():
        classic_tf.unlink()

    if idp_htpasswd_tf:
        (output_dir / "idp_htpasswd.tf").write_text(idp_htpasswd_tf + "\n", encoding="utf-8")
    if idp_optional_tf.strip() and idp_inv:
        (output_dir / "identity_providers_optional.tf").write_text(
            idp_optional_tf, encoding="utf-8"
        )

    migration = [
        f"# Migration notes: Classic `{result.source_cluster_name}` → HCP `{result.target_cluster_name}`",
        "",
        "Operator runbook: **[README.md](README.md)**.",
        "",
        f"- Source cluster ID: `{result.source_cluster_id}`",
        f"- IAM: new HCP account roles, OIDC, and operator roles with prefix `{result.account_role_prefix}`",
        "",
        "## Translations",
        "",
    ]
    migration.extend(f"- {n}" for n in result.notes)
    if idp_migration_md:
        migration.extend(["", idp_migration_md.rstrip()])
    if result.unmapped:
        migration.extend(["", "## Unmapped / manual", ""])
        migration.extend(f"- {u}" for u in result.unmapped)
    migration.append("")
    migration.append(
        "Workloads targeting infra nodes need tolerations for "
        "`node-role.kubernetes.io/infra=reserved:NoSchedule` when infra pools were created."
    )
    migration_md = "\n".join(migration)
    (output_dir / "MIGRATION.md").write_text(migration_md + "\n", encoding="utf-8")

    import sys

    scripts = Path(__file__).resolve().parents[2] / "rosa-classic-network-terraform" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from stack_makefile import write_split_stack_makefile
    from stack_readme import StackMeta, write_stack_readme

    write_split_stack_makefile(output_dir, aws_region=result.region)
    extra: list[str] = []
    if idp_migration_md.strip():
        extra.append(idp_migration_md.rstrip())
    write_stack_readme(
        output_dir,
        StackMeta(
            kind="classic_hcp",
            aws_region=result.region,
            cluster_name=result.target_cluster_name,
            cluster_id=result.source_cluster_id,
            source_cluster_name=result.source_cluster_name,
            target_cluster_name=result.target_cluster_name,
            module_version=result.module_version,
            account_role_prefix=result.account_role_prefix,
            notes=list(result.notes),
            unmapped=list(result.unmapped),
            extra_sections=extra,
        ),
    )


def _format_machine_pools_hcl(
    pools: dict[str, dict[str, Any]], multi_az: bool, azs: list[str]
) -> str:
    if not pools:
        return "{}"
    lines = ["{"]
    for key, spec in pools.items():
        lines.append(f'  {key} = {{')
        lines.append(f'    name               = {_hcl_string(spec["name"])}')
        subnet_comment = ""
        if multi_az and spec["name"].startswith(("infra-",)) or "-" in spec["name"]:
            m = re.search(r"-(\d+)$", spec["name"])
            if m:
                idx = int(m.group(1))
                if idx <= len(azs):
                    subnet_comment = f" # private subnet AZ {azs[idx-1]} (worker-{idx})"
        elif not multi_az:
            subnet_comment = f" # private subnet AZ {azs[0] if azs else '?'}"
        lines.append(f'    subnet_id          = ""{subnet_comment}')
        lines.append(f'    openshift_version  = {_hcl_string(spec["openshift_version"])}')
        lines.append("    auto_repair        = true")
        if "replicas" in spec:
            lines.append(f'    replicas           = {spec["replicas"]}')
        if spec.get("labels"):
            labels = ", ".join(f'{_hcl_string(k)} = {_hcl_string(v)}' for k, v in spec["labels"].items())
            lines.append(f"    labels             = {{ {labels} }}")
        if spec.get("taints"):
            lines.append("    taints = [")
            for t in spec["taints"]:
                lines.append(
                    "      { "
                    f"key = {_hcl_string(t['key'])}, "
                    f"value = {_hcl_string(t.get('value', ''))}, "
                    f"schedule_type = {_hcl_string(t.get('schedule_type', 'NoSchedule'))} "
                    "},"
                )
            lines.append("    ]")
        if spec.get("autoscaling"):
            a = spec["autoscaling"]
            lines.append("    autoscaling = {")
            lines.append(f"      enabled      = true")
            lines.append(f"      min_replicas = {a['min_replicas']}")
            lines.append(f"      max_replicas = {a['max_replicas']}")
            lines.append("    }")
        inst = spec["aws_node_pool"]["instance_type"]
        lines.append("    aws_node_pool = {")
        lines.append(f"      instance_type = {_hcl_string(inst)}")
        lines.append("      tags          = {}")
        lines.append("    }")
        lines.append("  }")
    lines.append("}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cluster-json", type=Path, required=True)
    parser.add_argument("--machinepools-json", type=Path, required=True)
    parser.add_argument("--ingress-json", type=Path, required=True)
    parser.add_argument("--versions-json", type=Path, required=True)
    parser.add_argument("--module-version", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--cluster-name", default="")
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    parser.add_argument("--include-infra", action="store_true")
    parser.add_argument("--no-infra", action="store_true")
    parser.add_argument("--reuse-cidrs", action="store_true")
    parser.add_argument("--unique-cidrs", action="store_true")
    parser.add_argument("--vpc-cidr", default="")
    parser.add_argument(
        "--openshift-version",
        default="",
        help="Hosted-cp OpenShift version from `rosa list versions --hosted-cp` "
        "(required when multiple minor lines are available).",
    )
    parser.add_argument(
        "--idps-json",
        type=Path,
        default=None,
        help="Classic IdP inventory from fetch_classic_idps.py (htpasswd replicated; others commented).",
    )
    args = parser.parse_args()

    if args.reuse_cidrs and args.unique_cidrs:
        raise SystemExit("Use only one of --reuse-cidrs or --unique-cidrs.")
    if args.write and not (args.include_infra or args.no_infra):
        raise SystemExit("--write requires --include-infra or --no-infra.")
    if args.write and not (args.reuse_cidrs or args.unique_cidrs):
        raise SystemExit("--write requires --reuse-cidrs or --unique-cidrs.")
    if not args.dry_run and not args.write:
        raise SystemExit("Specify --dry-run or --write.")

    cluster = _load_json(args.cluster_json)
    pools_doc = _load_json(args.machinepools_json)
    ingress_doc = _load_json(args.ingress_json)
    versions_doc = _load_json(args.versions_json)

    machine_c, pod_c, _ = _parse_cidrs(cluster)
    if args.vpc_cidr and machine_c:
        validate_vpc_contains_machine(args.vpc_cidr, machine_c)

    source_name = str(cluster.get("name") or "cluster")
    target_name = args.cluster_name or f"{_sanitize_cluster_name(source_name)}-hcp"
    include_infra = args.include_infra
    reuse = args.reuse_cidrs or (args.dry_run and not args.unique_cidrs)
    user_ocp_version = args.openshift_version.strip() or None

    if args.dry_run:
        reuse_for_preview = True
        result = build_mapping(
            cluster,
            pools_doc,
            ingress_doc,
            versions_doc,
            target_cluster_name=target_name,
            include_infra=False,
            reuse_cidrs=reuse_for_preview,
            module_version=args.module_version,
            openshift_version=user_ocp_version,
        )
        print(format_dry_run(result, machine_c or "", pod_c or ""))
        if args.idps_json and args.idps_json.is_file():
            print("")
            print(format_idp_briefing(load_idp_inventory(args.idps_json)))
        if result.version_plan.needs_user_choice and not user_ocp_version:
            print("")
            print(
                "Cannot --write until you pass --openshift-version with one of the versions above."
            )
        return

    preview_plan = plan_hcp_version(
        _openshift_version(cluster),
        _channel_group(cluster),
        versions_doc,
        user_version=None,
    )
    if preview_plan.needs_user_choice and not user_ocp_version:
        raise SystemExit(
            format_version_plan(preview_plan)
            + "\n\nPass --openshift-version before --write."
        )

    result = build_mapping(
        cluster,
        pools_doc,
        ingress_doc,
        versions_doc,
        target_cluster_name=target_name,
        include_infra=include_infra,
        reuse_cidrs=args.reuse_cidrs,
        module_version=args.module_version,
        openshift_version=user_ocp_version,
    )
    write_stack(result, args.output_dir, args.reuse_cidrs, idps_json=args.idps_json)
    print(f"Wrote Terraform stack to {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
