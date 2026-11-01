#!/usr/bin/env bash
# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${ROOT}/scripts/hcp_adopt_to_tf.py"
FIX="${ROOT}/fixtures/demo-hcp-public"
GOLD="${ROOT}/fixtures/golden/demo-hcp-adopt"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

python3 "${PY}" --write \
  --cluster-json "${FIX}/cluster.json" \
  --machinepools-json "${FIX}/machinepools.json" \
  --ingress-json "${FIX}/ingress.json" \
  --network-inventory "${FIX}/network-inventory.json" \
  --module-version 1.7.6 \
  --output-dir "${TMP}/out"

if command -v terraform >/dev/null 2>&1; then
  terraform fmt "${TMP}/out" >/dev/null
  terraform fmt "${GOLD}" >/dev/null
fi

diff -ru "${GOLD}" "${TMP}/out"

echo "All hcp-adopt fixture tests passed."
