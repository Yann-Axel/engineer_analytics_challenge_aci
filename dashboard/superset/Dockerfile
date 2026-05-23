FROM apache/superset:4.1.2

# Run as root only to install extra Python deps, then drop back to superset user.
USER root

# duckdb-engine is the SQLAlchemy driver Superset uses to talk to DuckDB.
# We pin duckdb to a version compatible with the file produced by dbt-duckdb (1.10.x).
RUN pip install --no-cache-dir \
        duckdb==1.5.3 \
        duckdb-engine==0.17.0

USER superset
