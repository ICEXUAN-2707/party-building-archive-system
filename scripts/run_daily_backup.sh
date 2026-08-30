#!/usr/bin/env bash
set -euo pipefail

ROOT="${PARTY_ARCHIVE_ROOT:-/srv/party-archive}"
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT}/app/compose.production.yml}"
COMPOSE_ENV="${COMPOSE_ENV:-${ROOT}/app/deploy/compose.env}"
BACKUP_ENV="${BACKUP_ENV:-${ROOT}/secrets/backup.env}"

compose() {
    docker compose --env-file "${COMPOSE_ENV}" -f "${COMPOSE_FILE}" "$@"
}

container_id="$(compose ps -q web)"
if [[ -z "${container_id}" || ! -f "${BACKUP_ENV}" ]]; then
    printf 'Web容器未运行或backup.env不存在。\n' >&2
    exit 2
fi
output="$(docker exec "${container_id}" python manage.py create_production_backup --reason daily)"
archive="$(printf '%s\n' "${output}" | sed -n 's/^备份完成：//p' | tail -n 1)"
if [[ -z "${archive}" ]]; then
    printf '无法从备份命令输出确定归档路径。\n' >&2
    exit 2
fi
docker exec --env-file "${BACKUP_ENV}" "${container_id}" python manage.py upload_backup_to_cos "${archive}"
printf '%s\n' "${output}"
