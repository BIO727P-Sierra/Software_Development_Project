import psycopg
from psycopg.rows import dict_row
from flask import current_app, g


def get_db():
    """Return a per-request database connection."""
    if "db" not in g:
        dsn = current_app.config.get("DATABASE_URL")
        if not dsn:
            raise RuntimeError(
                "DATABASE_URL is not set. "
                "Example: postgres://user:password@localhost:5432/dbname"
            )
        g.db = psycopg.connect(dsn, row_factory=dict_row)
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)
