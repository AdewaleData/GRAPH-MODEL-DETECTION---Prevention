#!/usr/bin/env bash
# Halal Graph — one-command production deployment (Linux server)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Halal Graph Production Deploy ==="

# Create .env from template if missing
if [ ! -f .env ]; then
  echo "Creating .env from .env.production.example ..."
  cp .env.production.example .env
  JWT=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
  sed -i "s/^JWT_SECRET=.*/JWT_SECRET=${JWT}/" .env
  echo ""
  echo ">>> Edit .env and set NEXT_PUBLIC_API_URL + CORS_ORIGINS to your domain <<<"
  echo "    nano .env"
  echo ""
  read -rp "Press Enter after editing .env, or Ctrl+C to abort..."
fi

bash scripts/preflight-production.sh

echo ""
echo "Building and starting production stack..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

echo ""
echo "Waiting for API health..."
for i in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:${HTTP_PORT:-80}/health" >/dev/null 2>&1; then
    echo "API is healthy."
    curl -s "http://127.0.0.1:${HTTP_PORT:-80}/health" | python3 -m json.tool 2>/dev/null || true
    break
  fi
  sleep 5
  if [ "$i" -eq 30 ]; then
    echo "Health check timed out. Check logs: docker compose logs api"
    exit 1
  fi
done

echo ""
echo "=== Deploy complete ==="
source .env 2>/dev/null || true
echo "Dashboard : http://127.0.0.1:${HTTP_PORT:-80}/"
echo "API docs  : http://127.0.0.1:${HTTP_PORT:-80}/docs"
echo "Prevention: http://127.0.0.1:${HTTP_PORT:-80}/prevention"
echo ""
echo "Login: admin@gmail.com / Admin@12345  — change password immediately!"
echo "Logs : docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f"
