import os
from flask import Flask, redirect,request, jsonify
from flask_cors import CORS
from .api.routes import api as schedule_bp
from flasgger import Swagger
from dotenv import load_dotenv
load_dotenv()

def create_app():
    app = Flask(__name__)

    @app.before_request
    def verify_api_key():
        if request.path.startswith("/api/"):
            expected_key = os.environ.get("SECRET_KEY")
            provided_key = request.headers.get("X-API-KEY")
            if not expected_key or provided_key != expected_key:
                return jsonify({"error": "Unauthorized"}), 401
    # Redirect root URL to Swagger UI
    @app.route("/health")
    def health():
     return "", 200

    @app.route("/")
    def root():
        return redirect("/apidocs/")

    # Determine allowed origins, default to allow all if FRONTEND_URL is not set
    env = os.environ.get("FLASK_ENV", "production")

    if env == "development":
        api_origins = "http://localhost:3000/*"
    else:
        api_origins = os.environ.get("FRONTEND_URL", "*") or "*"

        # CORS: allow all origins (API and Swagger UI)
    CORS(app)

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
        "swagger_ui":       True,
        "specs_route":      "/apidocs/",
        "swagger_ui_config": {
            "urls": [
                { "url": "/apispec.json", "name": "Schedule API" }
            ]
        },
    }
    Swagger(app, config=swagger_config)

    # Register API blueprint
    app.register_blueprint(schedule_bp, url_prefix="/api")
    return app
