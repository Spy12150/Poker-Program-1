"""
WSGI entry point for production deployment with SocketIO support
"""
from app import create_app, socketio

# Create the Flask app with SocketIO
app = create_app()

# For Gunicorn: Flask-SocketIO in threading mode should expose the Flask app
# The socketio events are handled through the initialized socketio instance
application = app

if __name__ == "__main__":
    # For production deployment - Flask-SocketIO's built-in server
    import os
    port = int(os.environ.get('PORT', 5001))
    print(f"🚀 Starting Flask-SocketIO production server on port {port}")
    print("📡 Using Flask-SocketIO's built-in server (recommended for WebSockets)")
    socketio.run(app, 
                host='0.0.0.0', 
                port=port, 
                debug=False, 
                log_output=False,
                allow_unsafe_werkzeug=True)
