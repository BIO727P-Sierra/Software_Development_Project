
#Importing relevant packages
import os 
from flask import Flask 

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

#Basic Configuration:
    app.config.from_mapping(
        SECRET_KEY= "dev",
        DATABASE_URL=os.environ.get("DATABASE_URL"),
    )

    if test_config is not None:
        app.config.update(test_config)
    
#Registering the Database:
    from . import db 
    db.init_app(app)

#Registering the Blueprints:
    from . import auth
    app.register_blueprint(auth.bp)

    from . import home
    app.register_blueprint(home.bp)

    return app

#What does this file do?
# create_app() creates the Flask app, loads config, registers the db, registers the blueprints