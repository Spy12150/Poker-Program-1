from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    
    # Configure CORS more explicitly
    CORS(app, resources={
        r"/*": {
            "origins": [
                "http://localhost:3000", "http://127.0.0.1:3000",
                "http://localhost:3001", "http://127.0.0.1:3001", 
                "http://localhost:3002", "http://127.0.0.1:3002",
                "http://localhost:3003", "http://127.0.0.1:3003",
                "http://localhost:3004", "http://127.0.0.1:3004"
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    from .routes import bp
    app.register_blueprint(bp)

    return app
