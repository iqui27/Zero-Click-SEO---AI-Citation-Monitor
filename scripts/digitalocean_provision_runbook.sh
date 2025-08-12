#!/usr/bin/env bash
# DigitalOcean provisioning runbook for droplet zero-click (ID 512874238)
# DO NOT EXECUTE directly. Review first.
# To run intentionally after review, set EXECUTE=true in the environment.

set -euo pipefail

if [ "${EXECUTE:-false}" != "true" ]; then
  echo "This is a DO NOT EXECUTE runbook. Review first. To run intentionally: EXECUTE=true $0"
  exit 1
fi

# ========= Config (fill these before running) =========
# Required for API interactions
export DO_API_TOKEN="{{set_in_env}}"   # place your token via environment management, do not inline secrets

# SSH access to the droplet
SSH_KEY="{{PATH_TO_SSH_PRIVATE_KEY}}"  # e.g., /Users/you/.ssh/id_ed25519
DROPLET_USER="{{SSH_USER}}"            # e.g., root

# Detected droplet details (pre-filled)
DROPLET_ID=512874238
DROPLET_NAME="zero-click"
DROPLET_IP="198.211.98.85"
DROPLET_REGION="nyc1"

# Optional firewall config
FIREWALL_NAME="web-ssh-zero-click"
ALLOW_SSH_IPS="{{CIDR_LIST_FOR_SSH}}"  # e.g., 203.0.113.0/24 or 0.0.0.0/0,::/0 (not recommended long-term)

# Volumes to create (space-separated: name:UID:GID)
VOLUMES_SPEC="{{app_data:1000:1000 db_data:999:999}}"

# Optional: DigitalOcean Container Registry (DOCR)
REGISTRY="{{registry_name}}"            # e.g., npp-registry
REGION="{{registry_region}}"           # e.g., nyc3
PROJECT_REPO="{{local_image:tag}}"     # e.g., myapp:latest
REGISTRY_REPO="{{repo_path}}"          # e.g., myapp

# ========= Helper =========
run() {
  echo ">>> $*"
  eval "$@"
}

# ========= 0) Authenticate and verify droplet =========
run "doctl auth init -t \"$DO_API_TOKEN\" >/dev/null 2>&1 || true"
run "doctl compute droplet get $DROPLET_ID --no-header --format ID,Name,PublicIPv4"

# ========= 1) Verify SSH access =========
run "ssh -o BatchMode=yes -i \"$SSH_KEY\" \"$DROPLET_USER@$DROPLET_IP\" true"

# ========= 2) Install Docker Engine and Compose v2 if absent (Ubuntu 25.04) =========
ssh -i "$SSH_KEY" "$DROPLET_USER@$DROPLET_IP" 'bash -s' <<'EOF'
set -euo pipefail
if ! command -v docker >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg
  install -m 0755 -d /etc/apt/keyrings
  if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
    curl -fsSL https://download.docker.com/linux/$(. /etc/os-release && echo "$ID")/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
  fi
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${ID} ${VERSION_CODENAME} stable" > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
else
  echo "Docker already installed"
fi
if ! docker compose version >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y docker-compose-plugin
else
  echo "Docker Compose v2 already installed"
fi
EOF

# ========= 3) Create named volumes with correct ownership =========
ssh -i "$SSH_KEY" "$DROPLET_USER@$DROPLET_IP" 'bash -s' <<'EOF'
set -euo pipefail
VOLUMES="__VOLUMES_SPEC__"
if [ -z "${VOLUMES:-}" ]; then
  echo "No volumes specified (VOLUMES). Skipping."; exit 0
fi
for spec in $VOLUMES; do
  vol="${spec%%:*}"
  rest="${spec#*:}"
  uid="${rest%%:*}"
  gid="${rest#*:}"
  if ! docker volume inspect "$vol" >/dev/null 2>&1; then
    docker volume create "$vol" >/dev/null
    echo "Created volume: $vol"
  else
    echo "Volume exists: $vol"
  fi
  docker run --rm -v "$vol:/data" busybox sh -c "chown -R ${uid}:${gid} /data"
  echo "Set ownership ${uid}:${gid} on volume $vol"
done
EOF
# Replace placeholder inside heredoc
perl -pi -e "s/__VOLUMES_SPEC__/$(printf '%s' \"$VOLUMES_SPEC\" | sed 's:[\\&]:\\\\&:g')/g" "$0" 2>/dev/null || true

# ========= 4) Optional: Cloud Firewall for web + restricted SSH =========
# Create firewall (idempotent-ish: will fail if already exists). Wrap in conditional.
if ! doctl compute firewall list --no-header --format Name | grep -qx "$FIREWALL_NAME"; then
  run "doctl compute firewall create \
  --name \"$FIREWALL_NAME\" \
  --inbound-rules \"protocol:tcp,ports:22,sources:addresses:$ALLOW_SSH_IPS\" \
  --inbound-rules \"protocol:tcp,ports:80,sources:addresses:0.0.0.0/0,::/0\" \
  --inbound-rules \"protocol:tcp,ports:443,sources:addresses:0.0.0.0/0,::/0\" \
  --outbound-rules \"protocol:tcp,ports:0,destinations:addresses:0.0.0.0/0,::/0\" \
  --outbound-rules \"protocol:udp,ports:0,destinations:addresses:0.0.0.0/0,::/0\" \
  --outbound-rules \"protocol:icmp,ports:0,destinations:addresses:0.0.0.0/0,::/0\""
else
  echo "Firewall $FIREWALL_NAME already exists"
fi
# Attach firewall to droplet (safe to re-run)
run "doctl compute firewall add-droplets \"$FIREWALL_NAME\" --droplet-ids $DROPLET_ID"

# ========= 5) Optional: Push built images to DigitalOcean Container Registry for caching =========
if [ "${DOCR:-false}" = "true" ]; then
  run "doctl auth init -t \"$DO_API_TOKEN\" >/dev/null 2>&1 || true"
  run "doctl registry login"
  if ! doctl registry get >/dev/null 2>&1; then
    run "doctl registry create \"$REGISTRY\" --region \"$REGION\""
  fi
  run "docker tag \"$PROJECT_REPO\" \"registry.digitalocean.com/$REGISTRY/$REGISTRY_REPO:latest\""
  run "docker push \"registry.digitalocean.com/$REGISTRY/$REGISTRY_REPO:latest\""
  IMAGE_SHA=$(docker image inspect --format='{{json .Id}}' "$PROJECT_REPO" | sha256sum | cut -c1-12)
  run "docker tag \"$PROJECT_REPO\" \"registry.digitalocean.com/$REGISTRY/$REGISTRY_REPO:${IMAGE_SHA}\""
  run "docker push \"registry.digitalocean.com/$REGISTRY/$REGISTRY_REPO:${IMAGE_SHA}\""
else
  echo "DOCR push skipped (set DOCR=true to enable)"
fi

# ========= 6) Validation checks =========
run "ssh -i \"$SSH_KEY\" \"$DROPLET_USER@$DROPLET_IP\" \"docker --version && docker compose version\""
run "ssh -i \"$SSH_KEY\" \"$DROPLET_USER@$DROPLET_IP\" \"docker volume ls\""
run "doctl compute firewall list --no-header --format ID,Name | grep -E \"($FIREWALL_NAME|allow-wireguard-udp-51820)\" || true"
run "doctl compute firewall get \"$FIREWALL_NAME\" || true"

echo "Runbook completed. Review outputs above."

