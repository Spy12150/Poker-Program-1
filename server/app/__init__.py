from flask import Flask
from flask_cors import CORS

def create_app():
    print("🔧 Creating Flask app...")
    app = Flask(__name__)
    
    print("🌐 Setting up CORS...")
    # Simple CORS configuration - allow all origins
    CORS(app, origins="*", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], 
         allow_headers=["Content-Type", "Authorization"])
    
    print("📝 Registering routes...")
    from .routes import bp
    app.register_blueprint(bp)
    
    print("✅ Flask app configuration complete")
    return app
