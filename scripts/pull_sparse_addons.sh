#!/usr/bin/env bash
set -euo pipefail

# Regular update script for production sparse checkout.
# Usage example:
#   TARGET_DIR=/opt/odoo-src BRANCH=master ./pull_sparse_addons.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-${SCRIPT_DIR}/sparse.env}"

if [ -f "${ENV_FILE}" ]; then
  echo "[INFO] Loading env file: ${ENV_FILE}"
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

TARGET_DIR="${TARGET_DIR:-/opt/odoo-src}"
BRANCH="${BRANCH:-master}"
REMOTE_NAME="${REMOTE_NAME:-origin}"

if [ ! -d "${TARGET_DIR}/.git" ]; then
  echo "[ERROR] ${TARGET_DIR} is not a git repository."
  echo "[HINT] Run setup_sparse_addons.sh first."
  exit 1
fi

cd "${TARGET_DIR}"

if ! git sparse-checkout list >/dev/null 2>&1; then
  echo "[ERROR] sparse-checkout is not configured in ${TARGET_DIR}."
  echo "[HINT] Run setup_sparse_addons.sh first."
  exit 1
fi

echo "[INFO] Fetching ${REMOTE_NAME}/${BRANCH}"
git fetch "${REMOTE_NAME}" "${BRANCH}"

local_sha="$(git rev-parse HEAD)"
remote_sha="$(git rev-parse "${REMOTE_NAME}/${BRANCH}")"

if [ "${local_sha}" = "${remote_sha}" ]; then
  echo "[INFO] Already up to date (${local_sha})."
  exit 0
fi

echo "[INFO] Updating with fast-forward only"
git merge --ff-only "${REMOTE_NAME}/${BRANCH}"

echo "[INFO] Update completed"
echo "[INFO] Active sparse paths:"
git sparse-checkout list
echo "[INFO] Current revision: $(git rev-parse --short HEAD)"
