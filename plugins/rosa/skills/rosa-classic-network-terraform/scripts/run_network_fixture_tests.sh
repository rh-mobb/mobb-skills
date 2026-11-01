#!/usr/bin/env bash
# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INV="${ROOT}/fixtures/multi-az-public/network-inventory.json"
NET="${ROOT}/scripts/network_to_tf.py"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

run_write() {
  local mode="$1"
  local golden="$2"
  local extra=()
  if [ "${mode}" = "copy" ]; then
    extra=(--vpc-cidr 10.1.0.0/16)
  fi
  python3 "${NET}" --write --mode "${mode}" \
    --inventory "${INV}" \
    --output-dir "${TMP}/${mode}" \
    "${extra[@]}"
  if command -v terraform >/dev/null 2>&1; then
    terraform fmt "${TMP}/${mode}" >/dev/null
    (cd "${TMP}/${mode}" && terraform init -backend=false >/dev/null && terraform validate)
  fi
  diff -ru "${ROOT}/fixtures/golden/${golden}" "${TMP}/${mode}" \
    -x .terraform -x .terraform.lock.hcl
}

run_write adopt multi-az-public-adopt
run_write copy multi-az-public-copy

python3 "${ROOT}/scripts/network_to_tf.py" --dry-run --mode adopt --inventory "${INV}" >/dev/null
HCP_TFVARS="${ROOT}/../rosa-classic-to-hcp-terraform/fixtures/golden/multi-az-private-no-infra/terraform.tfvars"
if python3 "${ROOT}/scripts/merge_hcp_stack.py" --dry-run \
  --network-outputs "${ROOT}/fixtures/golden/multi-az-public-adopt/network-outputs.json" \
  --hcp-tfvars "${HCP_TFVARS}" 2>/dev/null; then
  echo "merge should have failed without --allow-subnet-reuse" >&2
  exit 1
fi
python3 "${ROOT}/scripts/merge_hcp_stack.py" --dry-run \
  --network-outputs "${ROOT}/fixtures/golden/multi-az-public-adopt/network-outputs.json" \
  --hcp-tfvars "${HCP_TFVARS}" \
  --allow-subnet-reuse >/dev/null

echo "All network fixture tests passed."
