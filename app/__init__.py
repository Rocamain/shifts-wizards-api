import os
from flask import Flask, redirect
from flask_cors import CORS
from .api.routes import api as schedule_bp
from flasgger import Swagger


def create_app():
    app = Flask(__name__)

    # Redirect root URL to Swagger UI
    @app.route("/")
    def root():
        return redirect("/apidocs/")

    # CORS setup
    env = os.environ.get("FLASK_ENV", "production")
    origins = "http://localhost:3000" if env == "development" else os.environ.get("FRONTEND_URL")
    CORS(app, resources={r"/api/*": {"origins": origins}})

    # Swagger configuration
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route":   "/apispec.json",
                "rule_filter":   lambda rule: True,  # all endpoints
                "model_filter":  lambda tag: True,   # all models
            }
        ],
        "static_url_path": "/flasgger_static",
        # Use a dropdown instead of raw URL input
        "swagger_ui_config": {
            "urls": [
                { "url": "/apispec.json", "name": "Schedule API" }
            ]
        },
        "swagger_ui":       True,
        "specs_route":      "/apidocs/"
    }
    Swagger(app, config=swagger_config)

    # Register API blueprint
    app.register_blueprint(schedule_bp, url_prefix="/api")
    return app
