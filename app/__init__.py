from flask import Flask
from flask_cors import CORS

# Import your blueprint from the routes.py module
from .api.routes import api as schedule_bp

def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})
    app.register_blueprint(schedule_bp, url_prefix="/api")
    return app
