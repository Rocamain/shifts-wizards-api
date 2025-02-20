from flask import Flask
from flask_cors import CORS
from app.api.routes import api  # adjust import as needed

def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})

    # Register your blueprint with prefix "/api"
    app.register_blueprint(api, url_prefix="/api")

    return app
