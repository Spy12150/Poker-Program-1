from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

# Global SocketIO instance
socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    
    # Configure static file caching for better performance
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 year cache for static files
    
    # Simple CORS configuration - allow all origins
    CORS(app, origins="*", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], 
         allow_headers=["Content-Type", "Authorization"])
    
    # Initialize SocketIO with Railway-optimized settings
    # Use threading mode for Python 3.13 compatibility
    async_mode = 'threading'
    print("🔌 Using threading mode for WebSocket support (Python 3.13 compatible)")
    
    socketio.init_app(app, 
                     cors_allowed_origins="*", 
                     async_mode=async_mode,
                     # Railway-specific optimizations
                     ping_timeout=60,
                     ping_interval=25,
                     # Allow larger message sizes
                     max_http_buffer_size=1e6,
                     # Connection settings for stability  
                     logger=False,
                     engineio_logger=False,
                     # Reduce WebSocket errors in logs
                     always_connect=False)
    
    print(f"🔌 SocketIO initialized with async_mode: {async_mode}")
    
    from .routes import bp
    app.register_blueprint(bp)
    
    # Register WebSocket event handlers
    from .websocket_handlers import register_websocket_handlers
    register_websocket_handlers(socketio)

    return app
