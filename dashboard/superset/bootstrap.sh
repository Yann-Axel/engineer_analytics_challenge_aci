#!/bin/bash
# One-shot bootstrap to bring a fresh Superset container to a usable state.
# Idempotent: re-running won't break anything.

set -euo pipefail

CONTAINER="airline-superset"

echo ">>> Waiting for Superset container to be ready..."
for i in {1..30}; do
  if docker exec "$CONTAINER" sh -c 'true' >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo ">>> Initialising Superset metastore (db upgrade)..."
docker exec "$CONTAINER" superset db upgrade

echo ">>> Creating admin user (idempotent — already-exists is OK)..."
docker exec "$CONTAINER" superset fab create-admin \
  --username admin \
  --firstname Admin \
  --lastname User \
  --email admin@air-cote-divoire.local \
  --password admin || true

echo ">>> Initialising Superset roles & permissions..."
docker exec "$CONTAINER" superset init

echo ""
echo "=============================================================="
echo "  Superset is ready at: http://localhost:8088"
echo "  Login: admin / admin"
echo "=============================================================="
