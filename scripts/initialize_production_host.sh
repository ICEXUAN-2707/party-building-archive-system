#!/usr/bin/env bash
set -euo pipefail

readonly ROOT="/srv/party-archive"
readonly APP_UID="10001"
readonly APP_GID="10001"

if [[ "${EUID}" -ne 0 ]]; then
    echo "Run this script with sudo; it only initializes ${ROOT}." >&2
    exit 1
fi

install -d -m 0750 "${ROOT}/app"
install -d -m 0750 -o "${APP_UID}" -g "${APP_GID}" \
    "${ROOT}/data/database" \
    "${ROOT}/data/media" \
    "${ROOT}/data/static" \
    "${ROOT}/data/backups"
install -d -m 0750 "${ROOT}/data/logs"
install -d -m 0700 "${ROOT}/secrets" "${ROOT}/secrets/tls"

echo "Initialized ${ROOT}; existing files were not removed or overwritten."
