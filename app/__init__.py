import os
from flask import Flask
from flask_cors import CORS
from .api.routes import api as schedule_bp

def create_app():
    app = Flask(__name__)

    env = os.environ.get("FLASK_ENV", "production")
    if env == "development":
        origins = "http://localhost:3000"
    else:
        origins = os.environ.get("FRONTEND_URL")

    CORS(app, resources={r"/api/*": {"origins": origins}})
    app.register_blueprint(schedule_bp, url_prefix="/api")
    return app
