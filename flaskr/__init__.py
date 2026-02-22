
#Importing relevant packages
import os 
from flask import Flask 
from flask_login import LoginManager
from flask_login import UserMixin
from .db import get_db


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

#Basic Configuration:
    app.config.from_mapping(
        SECRET_KEY= "dev",
        DATABASE_URL=os.environ.get("DATABASE_URL"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("SQLALCHEMY_DATABASE_URI"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config is not None:
        app.config.update(test_config)
    
#Registering the Database:
    from . import db 
    db.init_app(app)

#Flask Login:

    login_manager = LoginManager()
    login_manager.login_view = "auth.login" #Where it sends user if not logged in
    login_manager.init_app(app)

#Imports User class from auth (after the app exists):
    from .auth import User

    @login_manager.user_loader
    def load_user(user_id: str):
        db_conn = get_db()
        with db_conn.cursor() as cur:
            cur.execute("SELECT id, email FROM users WHERE id =%s", (user_id,))
            row = cur.fetchone()
        return User(row["id"], row["email"]) if row else None

#Registering the Blueprints:
    from . import auth
    app.register_blueprint(auth.bp)

    from . import home
    app.register_blueprint(home.bp)

    

### Creating Blueprint - Registering Uniprot ###
    
    from . import uniprot
    app.register_blueprint(uniprot.bp)

    return app

################################################################



# create_app() creates the Flask app, loads config, registers the db, registers the blueprints
