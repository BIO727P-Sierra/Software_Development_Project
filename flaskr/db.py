import psycopg 
from psycopg.rows import dict_row
from flask import current_app, g
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def get_db():
    """Connect to the configured database. The connection is unique for each request."""
    if "db" not in g:
        dsn = current_app.config.get("DATABASE_URL")
        if not dsn:
            raise RuntimeError(
                "DATABASE_URL is not set. Example: "
                "postgres://user:password@localhost:5432/dbname"
            )
        g.db = psycopg.connect(dsn, row_factory=dict_row)

    return g.db


def close_db(e=None):
    """Close the database at the end of the request."""
    db = g.pop("db", None)

    if db is not None:
        db.close()
    


def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)
    db.init_app(app)