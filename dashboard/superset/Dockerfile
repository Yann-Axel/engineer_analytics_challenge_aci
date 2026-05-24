FROM apache/superset:4.1.2

# Run as root only to install extra Python deps + copy entrypoint, then drop
# back to the superset user.
USER root

# duckdb-engine is the SQLAlchemy driver Superset uses to talk to DuckDB.
# We pin duckdb to a version compatible with the file produced by dbt-duckdb (1.10.x).
RUN pip install --no-cache-dir \
        duckdb==1.5.3 \
        duckdb-engine==0.17.0

# Bootstrap entrypoint: runs `superset db upgrade`, creates the admin user,
# and runs `superset init` on every container start (idempotent), so a fresh
# clone + `docker compose up` yields a usable Superset without manual steps.
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh \
 && chmod +x /app/docker-entrypoint.sh

USER superset

ENTRYPOINT ["/app/docker-entrypoint.sh"]
