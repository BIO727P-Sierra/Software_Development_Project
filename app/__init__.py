import os
from flask import Flask
from flask_login import LoginManager
from .db import get_db, init_app as db_init_app
from flask_session import Session


def create_app(test_config=None):
    app = Flask(__name__, template_folder="templates")

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-change-me"),
        DATABASE_URL=os.environ.get("DATABASE_URL"),
        SESSION_TYPE="filesystem"
    )

    if test_config is not None:
        app.config.update(test_config)

    # ── Database ──────────────────────────────────────────────
    db_init_app(app)

    # ── Initialise session ────────────────────────────────────
    Session(app)
    
    # ── Flask-Login ───────────────────────────────────────────
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    from .auth import User

    @login_manager.user_loader
    def load_user(user_id: str):
        db_conn = get_db()
        with db_conn.cursor() as cur:
            cur.execute("SELECT id, email FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
        return User(row["id"], row["email"]) if row else None

    # ── Blueprints ────────────────────────────────────────────
    from . import auth, home, uniprot, FASTA_upload, experiment_upload, analysis

    app.register_blueprint(auth.bp)
    app.register_blueprint(home.bp)
    app.register_blueprint(uniprot.bp)
    app.register_blueprint(FASTA_upload.bp)
    app.register_blueprint(experiment_upload.bp)
    app.register_blueprint(analysis.bp)
    

    return app
