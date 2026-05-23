"""
Superset configuration for the Air Côte d'Ivoire challenge.
Lightweight setup: SQLite metastore, no Celery, no Redis.
Suitable for a local single-user analytics demo.
"""
import os

# ─── Secret key (read from env so it's not committed) ────────────────────────
SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]

# ─── Metastore: SQLite (no Postgres needed for a demo) ───────────────────────
# The metastore stores Superset's own metadata (users, dashboards, charts).
# A volume keeps it across container restarts.
SQLALCHEMY_DATABASE_URI = "sqlite:////app/superset_home/superset.db"

# ─── Feature flags ────────────────────────────────────────────────────────────
FEATURE_FLAGS = {
    "DASHBOARD_RBAC": False,           # single-user demo
    "EMBEDDED_SUPERSET": False,
    "ENABLE_TEMPLATE_PROCESSING": True, # jinja in chart SQL
    "DASHBOARD_CROSS_FILTERS": True,    # cross-filtering UX on dashboards
    "ALERT_REPORTS": False,             # no Celery in this setup
    "GLOBAL_ASYNC_QUERIES": False,
}

# ─── Web server / UX ──────────────────────────────────────────────────────────
ROW_LIMIT = 50_000             # max rows per chart query
SUPERSET_WEBSERVER_TIMEOUT = 120
DEFAULT_FEATURE_FLAGS = FEATURE_FLAGS

# ─── Caching: in-process simple cache (zero-deps for local demo) ─────────────
CACHE_CONFIG = {
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 60 * 5,
}
DATA_CACHE_CONFIG = CACHE_CONFIG
EXPLORE_FORM_DATA_CACHE_CONFIG = CACHE_CONFIG

# ─── Disable Celery (alerts/reports won't be used in this demo) ──────────────
class CeleryConfig:
    broker_url = "sqla+sqlite:////app/superset_home/celery.db"
    result_backend = "db+sqlite:////app/superset_home/celery_results.db"

CELERY_CONFIG = CeleryConfig

# ─── Auth: keep Superset's built-in DB auth (admin user created at bootstrap) ─
AUTH_TYPE = 1  # AUTH_DB
PUBLIC_ROLE_LIKE = "Gamma"

# ─── Locale ───────────────────────────────────────────────────────────────────
BABEL_DEFAULT_LOCALE = "en"
LANGUAGES = {
    "en": {"flag": "us", "name": "English"},
    "fr": {"flag": "fr", "name": "French"},
}

# ─── Security headers (basic local dev settings) ──────────────────────────────
TALISMAN_ENABLED = False
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = None
