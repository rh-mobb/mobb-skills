#!/usr/bin/env bash
# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${ROOT}/scripts/classic_to_hcp.py"
MODULE_VERSION="${MODULE_VERSION:-1.7.6}"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

run_write() {
  local fixture="$1"
  local mode="$2"
  local out="${TMP}/${fixture}-${mode}"
  local extra=()
  case "${mode}" in
    with-infra) extra=(--write --include-infra --reuse-cidrs) ;;
    no-infra) extra=(--write --no-infra --reuse-cidrs) ;;
    *) echo "unknown mode ${mode}" >&2; exit 1 ;;
  esac
  python3 "${PY}" "${extra[@]}" \
    --cluster-json "${ROOT}/fixtures/${fixture}/cluster.json" \
    --machinepools-json "${ROOT}/fixtures/${fixture}/machinepools.json" \
    --ingress-json "${ROOT}/fixtures/${fixture}/ingress.json" \
    --versions-json "${ROOT}/fixtures/${fixture}/versions-hosted-cp.json" \
    --module-version "${MODULE_VERSION}" \
    --cluster-name "$3" \
    --output-dir "${out}"
  if command -v terraform >/dev/null 2>&1; then
    terraform fmt "${out}" >/dev/null
  fi
  diff -ru "${ROOT}/fixtures/golden/$4" "${out}"
}

run_write multi-az-private with-infra demo-multi-hcp multi-az-private-with-infra
run_write multi-az-private no-infra demo-multi-hcp multi-az-private-no-infra
run_write single-az-public no-infra demo-single-hcp single-az-public-no-infra

run_write_idps() {
  local out="${TMP}/single-az-public-with-idps"
  python3 "${PY}" --write --no-infra --reuse-cidrs \
    --cluster-json "${ROOT}/fixtures/single-az-public/cluster.json" \
    --machinepools-json "${ROOT}/fixtures/single-az-public/machinepools.json" \
    --ingress-json "${ROOT}/fixtures/single-az-public/ingress.json" \
    --versions-json "${ROOT}/fixtures/single-az-public/versions-hosted-cp.json" \
    --idps-json "${ROOT}/fixtures/idp-mix/classic-idps-inventory.json" \
    --module-version "${MODULE_VERSION}" \
    --cluster-name demo-idp-hcp \
    --output-dir "${out}"
  if command -v terraform >/dev/null 2>&1; then
    terraform fmt "${out}" >/dev/null
  fi
  diff -ru "${ROOT}/fixtures/golden/single-az-public-with-idps" "${out}"
}
run_write_idps

if python3 "${PY}" --dry-run \
  --cluster-json "${ROOT}/fixtures/cidr-overlap/cluster.json" \
  --machinepools-json "${ROOT}/fixtures/cidr-overlap/machinepools.json" \
  --ingress-json "${ROOT}/fixtures/cidr-overlap/ingress.json" \
  --versions-json "${ROOT}/fixtures/cidr-overlap/versions-hosted-cp.json" \
  --module-version "${MODULE_VERSION}" 2>/dev/null; then
  echo "expected cidr-overlap fixture to fail" >&2
  exit 1
fi

python3 "${PY}" --dry-run \
  --cluster-json "${ROOT}/fixtures/multi-az-private/cluster.json" \
  --machinepools-json "${ROOT}/fixtures/multi-az-private/machinepools.json" \
  --ingress-json "${ROOT}/fixtures/multi-az-private/ingress.json" \
  --versions-json "${ROOT}/fixtures/multi-az-private/versions-hosted-cp.json" \
  --module-version "${MODULE_VERSION}" \
  --vpc-cidr 192.168.0.0/16 2>/dev/null && {
  echo "expected vpc/machine mismatch to fail" >&2
  exit 1
}

if python3 "${PY}" --write --no-infra --reuse-cidrs \
  --cluster-json "${ROOT}/fixtures/version-choice/cluster.json" \
  --machinepools-json "${ROOT}/fixtures/version-choice/machinepools.json" \
  --ingress-json "${ROOT}/fixtures/version-choice/ingress.json" \
  --versions-json "${ROOT}/fixtures/version-choice/versions-hosted-cp.json" \
  --module-version "${MODULE_VERSION}" \
  --output-dir "${TMP}/version-choice-fail" 2>/dev/null; then
  echo "expected version-choice write without --openshift-version to fail" >&2
  exit 1
fi

python3 "${PY}" --dry-run \
  --cluster-json "${ROOT}/fixtures/version-choice/cluster.json" \
  --machinepools-json "${ROOT}/fixtures/version-choice/machinepools.json" \
  --ingress-json "${ROOT}/fixtures/version-choice/ingress.json" \
  --versions-json "${ROOT}/fixtures/version-choice/versions-hosted-cp.json" \
  --module-version "${MODULE_VERSION}" | grep -q "Operator must choose" || {
  echo "expected version-choice dry-run to list operator version choices" >&2
  exit 1
}

echo "All fixture tests passed."
