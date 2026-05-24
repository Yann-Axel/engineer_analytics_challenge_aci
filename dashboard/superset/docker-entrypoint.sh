#!/bin/bash
# =============================================================================
# Superset entrypoint — initialises the metastore on first boot, then hands off
# to the default gunicorn launcher. Idempotent: subsequent restarts skip work
# already done by Alembic / Flask-AppBuilder.
# =============================================================================
set -euo pipefail

echo ">>> [superset-init] db upgrade"
superset db upgrade

echo ">>> [superset-init] create admin (idempotent)"
superset fab create-admin \
    --username admin \
    --firstname Admin \
    --lastname User \
    --email admin@air-cote-divoire.local \
    --password admin || true

echo ">>> [superset-init] init roles & permissions"
superset init

echo ">>> [superset-init] launching web server"
exec /usr/bin/run-server.sh
