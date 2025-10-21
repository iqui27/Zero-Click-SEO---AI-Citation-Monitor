#!/usr/bin/env bash
set -euo pipefail

# Default command if none provided.
if [[ $# -eq 0 ]]; then
  set -- uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --timeout-keep-alive 300 \
    --workers 1 \
    --log-level info \
    --access-log
fi

log() {
  echo "[backend-tunnel] $*" >&2
}

start_tunnel() {
  local local_port remote_host remote_port ssh_host ssh_user ssh_opts

  if [[ -z "${BASTION_SSH_HOST:-}" || -z "${BASTION_SSH_USER:-}" ]]; then
    log "Tunnel requested but BASTION_SSH_HOST or BASTION_SSH_USER not set."
    exit 1
  fi

  ssh_host="${BASTION_SSH_HOST}"
  ssh_user="${BASTION_SSH_USER}"
  local_port="${DB_TUNNEL_LOCAL_PORT:-14331}"
  remote_host="${DB_TUNNEL_REMOTE_HOST:-db-aigeo.database.windows.net}"
  remote_port="${DB_TUNNEL_REMOTE_PORT:-1433}"
  ssh_opts="-o StrictHostKeyChecking=no -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=5"

  if [[ -n "${DB_TUNNEL_SSH_OPTIONS:-}" ]]; then
    ssh_opts+=" ${DB_TUNNEL_SSH_OPTIONS}"
  fi

  mkdir -p /home/appuser/.ssh || log "warning: unable to create /home/appuser/.ssh"
  chmod 700 /home/appuser/.ssh 2>/dev/null || log "warning: unable to chmod /home/appuser/.ssh"

  # Private key handling.
  key_file=""
  if [[ -n "${BASTION_SSH_PRIVATE_KEY_BASE64:-}" ]]; then
    key_file="/home/appuser/.ssh/id_rsa"
    echo "${BASTION_SSH_PRIVATE_KEY_BASE64}" | base64 -d > "${key_file}"
    chmod 600 "${key_file}" 2>/dev/null || log "warning: unable to chmod decoded SSH key"
  elif [[ -n "${BASTION_SSH_PRIVATE_KEY:-}" ]]; then
    key_file="/home/appuser/.ssh/id_rsa"
    printf '%s\n' "${BASTION_SSH_PRIVATE_KEY}" > "${key_file}"
    chmod 600 "${key_file}" 2>/dev/null || log "warning: unable to chmod inline SSH key"
  elif [[ -n "${BASTION_SSH_KEY_PATH:-}" && -f "${BASTION_SSH_KEY_PATH}" ]]; then
    key_file="${BASTION_SSH_KEY_PATH}"
  fi

  if [[ -n "${key_file}" ]]; then
    ssh_opts+=" -i ${key_file}"
  fi

  log "Opening SSH tunnel ${local_port} -> ${remote_host}:${remote_port} via ${ssh_user}@${ssh_host}"
  ssh ${ssh_opts} -f -N -L "${local_port}:${remote_host}:${remote_port}" "${ssh_user}@${ssh_host}"

  if [[ -n "${DATABASE_URL:-}" ]]; then
    DATABASE_URL="$(python3 - <<'PY'
import os, urllib.parse, sys

url = os.environ.get("DATABASE_URL", "")
local_port = os.environ.get("DB_TUNNEL_LOCAL_PORT", "14331")
remote_host = os.environ.get("DB_TUNNEL_REMOTE_HOST", "db-aigeo.database.windows.net")

if not url:
    sys.exit(0)

parsed = urllib.parse.urlparse(url)
query = urllib.parse.parse_qs(parsed.query)
odbc = query.get("odbc_connect")
if not odbc:
    # Replace occurrences directly in netloc if present.
    new_netloc = parsed.netloc.replace(remote_host, "127.0.0.1")
    new_netloc = new_netloc.replace(f":1433", f":{local_port}")
    rebuilt = parsed._replace(netloc=new_netloc)
    print(urllib.parse.urlunparse(rebuilt))
    sys.exit(0)

decoded = urllib.parse.unquote(odbc[0])
decoded = decoded.replace(f"SERVER={remote_host},1433", f"SERVER=127.0.0.1,{local_port}")
decoded = decoded.replace(f"SERVER={remote_host}\\,1433", f"SERVER=127.0.0.1,{local_port}")
decoded = decoded.replace(f"SERVER={remote_host}%2C1433", f"SERVER=127.0.0.1,{local_port}")
encoded = urllib.parse.quote(decoded, safe="")
new_url = f"{parsed.scheme}:///?odbc_connect={encoded}"
print(new_url)
PY
)"
    export DATABASE_URL
    log "DATABASE_URL rewritten for local tunnel."
  fi
}

if [[ "${DB_TUNNEL_ENABLED:-0}" != "0" ]]; then
  start_tunnel
else
  log "DB tunnel disabled (DB_TUNNEL_ENABLED=${DB_TUNNEL_ENABLED:-0})."
fi

exec "$@"
