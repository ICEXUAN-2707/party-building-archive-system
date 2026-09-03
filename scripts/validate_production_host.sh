#!/usr/bin/env bash
set -u

# DEP-09 preflight is deliberately read-only. It never installs packages or
# changes users, permissions, firewall rules, Docker, or systemd services.
ROOT="${PARTY_ARCHIVE_ROOT:-/srv/party-archive}"
MIN_MEMORY_KIB=3800000
MIN_DISK_KIB=30000000
failures=0
warnings=0

pass() { printf '[PASS] %s\n' "$1"; }
warn() { printf '[WARN] %s\n' "$1"; warnings=$((warnings + 1)); }
fail() { printf '[FAIL] %s\n' "$1" >&2; failures=$((failures + 1)); }

if [[ "$(uname -s)" == "Linux" ]]; then pass "Linux host"; else fail "Linux is required"; fi
if [[ "$(uname -m)" == "x86_64" ]]; then pass "x86_64 architecture"; else fail "x86_64 architecture is required"; fi

if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    [[ "${ID:-}" == "ubuntu" ]] || warn "Ubuntu 24.04 LTS is the reviewed platform (found ${ID:-unknown})"
    [[ "${VERSION_ID:-}" == "24.04" ]] || warn "Ubuntu 24.04 LTS is the reviewed version (found ${VERSION_ID:-unknown})"
else
    warn "cannot read /etc/os-release"
fi

memory_kib="$(awk '/MemTotal/ {print $2}' /proc/meminfo 2>/dev/null || true)"
if [[ "${memory_kib:-0}" -ge "$MIN_MEMORY_KIB" ]]; then pass "memory is at least 4 GiB class"; else fail "at least 4 GiB memory is required"; fi

disk_kib="$(df -Pk "${ROOT}" 2>/dev/null | awk 'NR==2 {print $4}' || true)"
if [[ -z "$disk_kib" ]]; then
    disk_kib="$(df -Pk / | awk 'NR==2 {print $4}')"
    warn "${ROOT} does not exist; checking root filesystem capacity"
fi
if [[ "${disk_kib:-0}" -ge "$MIN_DISK_KIB" ]]; then pass "at least 30 GiB disk space is available"; else fail "at least 30 GiB free disk space is required"; fi

for command_name in docker curl openssl systemctl timedatectl; do
    if command -v "$command_name" >/dev/null 2>&1; then pass "command available: ${command_name}"; else fail "missing command: ${command_name}"; fi
done

if command -v docker >/dev/null 2>&1; then
    docker version >/dev/null 2>&1 && pass "Docker daemon reachable" || fail "Docker daemon is not reachable"
    docker compose version >/dev/null 2>&1 && pass "Docker Compose plugin available" || fail "Docker Compose plugin is unavailable"
fi

if command -v timedatectl >/dev/null 2>&1; then
    timedatectl show -p NTPSynchronized --value 2>/dev/null | grep -qx yes \
        && pass "system clock synchronized" || warn "system clock is not confirmed synchronized"
fi

for relative_path in app data/database data/media data/static data/backups data/logs secrets secrets/tls; do
    [[ -d "${ROOT}/${relative_path}" ]] && pass "directory exists: ${ROOT}/${relative_path}" || warn "directory missing: ${ROOT}/${relative_path}"
done

if [[ -e "${ROOT}/secrets/.env.production" ]]; then
    mode="$(stat -c '%a' "${ROOT}/secrets/.env.production" 2>/dev/null || true)"
    [[ "$mode" == "600" ]] && pass "production environment file mode is 600" || fail "production environment file must have mode 600"
else
    warn "production environment file is not provisioned"
fi

printf 'Summary: failures=%s warnings=%s\n' "$failures" "$warnings"
[[ "$failures" -eq 0 ]]
