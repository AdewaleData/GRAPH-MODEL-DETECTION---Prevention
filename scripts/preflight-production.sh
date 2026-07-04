#!/usr/bin/env bash
# Halal Graph — production preflight checks
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ERR=0

check() {
  if eval "$2"; then
    echo -e "${GREEN}✓${NC} $1"
  else
    echo -e "${RED}✗${NC} $1"
    ERR=1
  fi
}

echo "=== Halal Graph Production Preflight ==="

check "Docker installed" "command -v docker >/dev/null"
check "Docker Compose installed" "docker compose version >/dev/null"

for f in gcn_best.pt gat_best.pt rf_bundle.joblib feature_cols.joblib; do
  check "Model: $f" "test -f artifacts/models/$f"
done

check ".env file exists" "test -f .env"
if [ -f .env ]; then
  source .env 2>/dev/null || true
  check "JWT_SECRET set (not default)" "[ -n \"\${JWT_SECRET:-}\" ] && [ \"\${JWT_SECRET}\" != 'change-me-to-a-long-random-string' ]"
  check "NEXT_PUBLIC_API_URL set" "[ -n \"\${NEXT_PUBLIC_API_URL:-}\" ] && [ \"\${NEXT_PUBLIC_API_URL}\" != 'https://your-domain.com' ]"
  check "CORS_ORIGINS set" "[ -n \"\${CORS_ORIGINS:-}\" ]"
fi

if [ -f deploy/certs/fullchain.pem ] && [ -f deploy/certs/privkey.pem ]; then
  echo -e "${GREEN}✓${NC} TLS certificates found"
else
  echo -e "${YELLOW}!${NC} No TLS certs — will serve HTTP only on port 80"
fi

if [ "$ERR" -eq 0 ]; then
  echo -e "\n${GREEN}Ready for production deploy.${NC}"
else
  echo -e "\n${RED}Fix the issues above before deploying.${NC}"
  exit 1
fi
