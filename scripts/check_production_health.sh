#!/usr/bin/env bash
set -euo pipefail

ROOT="${PARTY_ARCHIVE_ROOT:-/srv/party-archive}"
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT}/app/compose.production.yml}"
COMPOSE_ENV="${COMPOSE_ENV:-${ROOT}/app/deploy/compose.env}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1/health/ready/}"
SERVER_NAME="${NGINX_SERVER_NAME:?NGINX_SERVER_NAME is required}"
BACKUP_SUCCESS_FILE="${BACKUP_SUCCESS_FILE:-${ROOT}/data/backups/.last-offsite-success}"
DISK_WARNING_PERCENT="${DISK_WARNING_PERCENT:-80}"
DISK_CRITICAL_PERCENT="${DISK_CRITICAL_PERCENT:-90}"
BACKUP_MAX_AGE_SECONDS="${BACKUP_MAX_AGE_SECONDS:-90000}"

failures=()
warnings=()
transient_failures=()
FAILURE_THRESHOLD="${FAILURE_THRESHOLD:-3}"
STATE_FILE="${HEALTH_STATE_FILE:-${ROOT}/data/logs/health-failure-count}"

compose() {
    docker compose --env-file "${COMPOSE_ENV}" -f "${COMPOSE_FILE}" "$@"
}

for service in web nginx; do
    container_id="$(compose ps -q "${service}")"
    if [[ -z "${container_id}" ]]; then
        transient_failures+=("${service}:missing")
        continue
    fi
    status="$(docker inspect --format '{{.State.Status}}/{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "${container_id}")"
    if [[ "${status}" != "running/healthy" ]]; then
        transient_failures+=("${service}:${status}")
    fi
done

if ! curl --fail --silent --show-error --max-time 10 \
    --header "Host: ${SERVER_NAME}" "${HEALTH_URL}" >/dev/null; then
    transient_failures+=("http-readiness")
fi

disk_percent="$(df -P "${ROOT}" | awk 'NR==2 {gsub(/%/, "", $5); print $5}')"
if (( disk_percent >= DISK_CRITICAL_PERCENT )); then
    failures+=("disk:${disk_percent}%")
elif (( disk_percent >= DISK_WARNING_PERCENT )); then
    warnings+=("disk:${disk_percent}%")
fi

if [[ ! -f "${BACKUP_SUCCESS_FILE}" ]]; then
    failures+=("offsite-backup-marker-missing")
else
    marker_age=$(( $(date +%s) - $(stat -c %Y "${BACKUP_SUCCESS_FILE}") ))
    if (( marker_age > BACKUP_MAX_AGE_SECONDS )); then
        failures+=("offsite-backup-stale:${marker_age}s")
    fi
fi

if ! timedatectl show -p NTPSynchronized --value 2>/dev/null | grep -qx yes; then
    warnings+=("clock-not-synchronized")
fi

if ((${#transient_failures[@]} > 0)); then
    previous_count=0
    [[ ! -f "${STATE_FILE}" ]] || read -r previous_count < "${STATE_FILE}"
    failure_count=$((previous_count + 1))
    printf '%s\n' "${failure_count}" > "${STATE_FILE}.tmp"
    mv "${STATE_FILE}.tmp" "${STATE_FILE}"
    if (( failure_count >= FAILURE_THRESHOLD )); then
        failures+=("${transient_failures[@]}")
    else
        warnings+=("transient-${failure_count}/${FAILURE_THRESHOLD}:${transient_failures[*]}")
    fi
else
    rm -f "${STATE_FILE}"
fi

printf 'party-archive health failures=%s warnings=%s\n' "${#failures[@]}" "${#warnings[@]}"
((${#warnings[@]} == 0)) || printf 'warnings: %s\n' "${warnings[*]}"
if ((${#failures[@]} > 0)); then
    printf 'failures: %s\n' "${failures[*]}" >&2
    exit 2
fi
