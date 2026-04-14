#!/usr/bin/env bash
set -euo pipefail

# One-time setup for sparse checkout on production.
# Usage example:
#   REPO_URL=git@github.com:org/repo.git TARGET_DIR=/opt/odoo-src BRANCH=master ./setup_sparse_addons.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-${SCRIPT_DIR}/sparse.env}"

if [ -f "${ENV_FILE}" ]; then
  echo "[INFO] Loading env file: ${ENV_FILE}"
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

REPO_URL="${REPO_URL:-}"
BRANCH="${BRANCH:-master}"
TARGET_DIR="${TARGET_DIR:-/opt/odoo-src}"
SPARSE_PATHS="${SPARSE_PATHS:-addons}"
REMOTE_NAME="${REMOTE_NAME:-origin}"

if [ -z "${REPO_URL}" ]; then
  echo "[ERROR] REPO_URL is required."
  echo "[HINT] Example: REPO_URL=git@github.com:org/repo.git ./setup_sparse_addons.sh"
  exit 1
fi

echo "[INFO] Starting sparse checkout setup"
echo "[INFO] repo=${REPO_URL}"
echo "[INFO] branch=${BRANCH}"
echo "[INFO] target_dir=${TARGET_DIR}"
echo "[INFO] sparse_paths=${SPARSE_PATHS}"

mkdir -p "${TARGET_DIR}"
cd "${TARGET_DIR}"

if [ ! -d ".git" ]; then
  echo "[INFO] Initializing git repository in ${TARGET_DIR}"
  git init
fi

if git remote get-url "${REMOTE_NAME}" >/dev/null 2>&1; then
  existing_url="$(git remote get-url "${REMOTE_NAME}")"
  if [ "${existing_url}" != "${REPO_URL}" ]; then
    echo "[ERROR] Remote ${REMOTE_NAME} already points to ${existing_url}"
    echo "[HINT] Use another TARGET_DIR or update the remote manually."
    exit 1
  fi
else
  echo "[INFO] Adding remote ${REMOTE_NAME}"
  git remote add "${REMOTE_NAME}" "${REPO_URL}"
fi

echo "[INFO] Enabling sparse-checkout (cone mode)"
git sparse-checkout init --cone

echo "[INFO] Applying sparse paths"
# shellcheck disable=SC2086
git sparse-checkout set ${SPARSE_PATHS}

echo "[INFO] Fetching branch ${BRANCH}"
git fetch "${REMOTE_NAME}" "${BRANCH}"

echo "[INFO] Checking out local branch ${BRANCH}"
git checkout -B "${BRANCH}" "${REMOTE_NAME}/${BRANCH}"

echo "[INFO] Sparse checkout configured successfully"
echo "[INFO] Active sparse paths:"
git sparse-checkout list
echo "[INFO] Current revision: $(git rev-parse --short HEAD)"
