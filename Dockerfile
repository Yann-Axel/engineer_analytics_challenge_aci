# =============================================================================
# Air Côte d'Ivoire — pipeline + MCP image
# Single Python image reused by both the one-shot pipeline service (Part 1+2)
# and the MCP server (Part 4). Superset has its own image — see
# dashboard/superset/Dockerfile.
# =============================================================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# git is needed by `dbt deps`; curl/ca-certs for general network ops.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Install Python deps first to maximise layer caching.
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt \
    && pip install duckdb==1.5.3

# 2. Copy project code. Bind-mounts in docker-compose can override these at
#    runtime when artefacts need to persist on the host.
COPY scripts/ /app/scripts/
COPY dbt/ /app/dbt/
COPY mcp_server/ /app/mcp_server/
COPY data/ /app/data/
COPY docker/ /app/docker/
# Superset provisioning scripts — used by the `superset-provisioner`
# compose service to create datasets/charts/dashboards after Superset boots.
COPY dashboard/superset/ /app/dashboard/superset/

RUN sed -i 's/\r$//' /app/docker/entrypoint-pipeline.sh \
                     /app/docker/entrypoint-provisioner.sh \
 && chmod +x /app/docker/entrypoint-pipeline.sh \
             /app/docker/entrypoint-provisioner.sh

# Default to an interactive Python; compose services override `command`.
CMD ["python"]
