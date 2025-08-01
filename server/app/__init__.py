from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    
    # Simple CORS configuration - allow all origins
    CORS(app, origins="*", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], 
         allow_headers=["Content-Type", "Authorization"])
    
    from .routes import bp
    app.register_blueprint(bp)

    return app
