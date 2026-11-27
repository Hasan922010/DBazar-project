#!/usr/bin/env bash
# DBazar Monorepo — Yagona Ishga Tushirish va Avto-Test Skripti (`run.sh`)
# Rejimlar:
#   ./run.sh          -> Migratsiyalar + Kontrakt + Testlarni o'tkazib, so'ngra Backend va Frontend serverlarini yoqadi
#   ./run.sh test     -> Faqat Backend (pytest) va Frontend (node --test) avto-testlarini tekshiradi va yakunlaydi
#   ./run.sh serve    -> Testlarsiz to'g'ridan-to'g'ri Backend va Frontend serverlarini yoqadi
#   ./run.sh docker   -> Docker Compose (PostgreSQL 16, Redis 7, Redpanda, ClickHouse, MinIO) ni ko'taradi

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/apps/backend"
PYTHON_BIN="$BACKEND_DIR/.venv/bin/python"

MODE="${1:-all}"

pick_free_port() {
  "$PYTHON_BIN" - "$1" <<'PY'
import socket, sys
preferred = int(sys.argv[1])
for port in (preferred, 8001, 8080, 8888, 3001):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("127.0.0.1", port))
        print(port)
        sys.exit(0)
    except OSError:
        pass
    finally:
        s.close()
print(preferred)
PY
}

ensure_backend_ready() {
  echo "==> [1/4] Django 5 Ma'lumotlar bazasi migratsiyalari va OpenAPI 3.1.0 kontrakt eksporti..."
  cd "$BACKEND_DIR"
  "$PYTHON_BIN" manage.py migrate --noinput
  "$PYTHON_BIN" manage.py export_openapi

  echo "==> [2/4] TypeScript kontrakt tiplarini generatsiya qilish (@dbazar/contracts)..."
  cd "$ROOT_DIR"
  node packages/contracts/generate.js
}

run_all_tests() {
  echo "==> [3/4] Backend pytest va B2B Xavfsizlik Auditi (/b2b-security-audit)..."
  cd "$BACKEND_DIR"
  "$PYTHON_BIN" -m pytest

  echo "==> [4/4] Frontend ilovalar testlari (Web-Portal, Offline-First POS SQLite, Mobile App)..."
  cd "$ROOT_DIR"
  node --test \
    apps/web-portal/tests/web-portal.test.js \
    apps/pos-client/tests/pos-client.test.js \
    apps/mobile-app/tests/mobile-app.test.js

  echo ""
  echo "=================================================================="
  echo " BARCHA BACKEND VA FRONTEND TESTLAR 100% MUVAFFAQIYATLI O'TDI!"
  echo "=================================================================="
}

start_servers() {
  BACKEND_PORT="$(pick_free_port "${BACKEND_PORT:-8000}")"
  FRONTEND_PORT="$(pick_free_port "${FRONTEND_PORT:-3000}")"

  echo ""
  echo "==> Serverlar ishga tushirilmoqda (to'xtatish uchun Ctrl+C bosing):"
  echo "    - Frontend UI Preview: http://127.0.0.1:${FRONTEND_PORT}"
  echo "    - Backend OpenAPI 3.1: http://127.0.0.1:${BACKEND_PORT}/api/v1/openapi.json"
  echo "    - Backend Healthcheck: http://127.0.0.1:${BACKEND_PORT}/healthz/"
  echo "    - Django Admin Panel:  http://127.0.0.1:${BACKEND_PORT}/admin/  (Login: admin / Parol: dbazar2026)"
  echo ""

  cd "$BACKEND_DIR"
  "$PYTHON_BIN" manage.py seed_demo_data >/dev/null

  cleanup() {
    kill "${BACKEND_PID:-}" "${FRONTEND_PID:-}" 2>/dev/null || true
  }
  trap cleanup EXIT INT TERM

  cd "$BACKEND_DIR"
  "$PYTHON_BIN" manage.py runserver "127.0.0.1:${BACKEND_PORT}" --noreload --skip-checks &
  BACKEND_PID=$!

  cd "$ROOT_DIR"
  PORT="$FRONTEND_PORT" BACKEND_PORT="$BACKEND_PORT" node apps/web-portal/src/preview-server.js &
  FRONTEND_PID=$!

  wait "$BACKEND_PID" "$FRONTEND_PID"
}

case "$MODE" in
  all)
    ensure_backend_ready
    run_all_tests
    start_servers
    ;;
  test)
    ensure_backend_ready
    run_all_tests
    ;;
  serve)
    ensure_backend_ready
    start_servers
    ;;
  docker)
    cd "$ROOT_DIR"
    docker compose up -d
    docker compose ps
    ;;
  *)
    echo "Foydalanish: ./run.sh [all|test|serve|docker]"
    exit 1
    ;;
esac
