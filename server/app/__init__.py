from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

# Global SocketIO instance
socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    
    # Simple CORS configuration - allow all origins
    CORS(app, origins="*", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], 
         allow_headers=["Content-Type", "Authorization"])
    
    # Initialize SocketIO with CORS support and production-ready async mode
    async_mode = 'eventlet' if 'eventlet' in __import__('sys').modules else 'threading'
    socketio.init_app(app, cors_allowed_origins="*", async_mode=async_mode)
    
    from .routes import bp
    app.register_blueprint(bp)
    
    # Register WebSocket event handlers
    from .websocket_handlers import register_websocket_handlers
    register_websocket_handlers(socketio)

    return app
