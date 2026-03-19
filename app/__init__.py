from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from config import Config

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(Config)

    db.init_app(app)
    CORS(app)

    # Load ML models ONCE at startup — stored on app object
    from app.ml_engine import MLEngine
    app.ml_engine = MLEngine(app.config)

    with app.app_context():
        db.create_all()

    from app.routes import main
    app.register_blueprint(main)

    return app
