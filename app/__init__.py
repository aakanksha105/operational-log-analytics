import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

from app.extensions import db


def create_app(test_config=None):
    load_dotenv()
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///log_anomaly.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if test_config:
        app.config.update(test_config)

    CORS(app)
    db.init_app(app)

    from app.routes import api_bp
    from app.dashboard import dashboard_bp
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(dashboard_bp)

    with app.app_context():
        db.create_all()

    return app
