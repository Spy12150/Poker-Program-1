"""
WSGI entry point for production deployment with SocketIO support
"""
from app import create_app, socketio

# Create the Flask app with SocketIO
app = create_app()

# This is what Gunicorn will use - must be the SocketIO app for WebSocket support
application = socketio

if __name__ == "__main__":
    # For LOCAL development only - use SocketIO's built-in server
    import os
    port = int(os.environ.get('PORT', 5001))
    print(f"🚀 Starting LOCAL WebSocket server on port {port}")
    print("⚠️  This is for development only - production uses Gunicorn via Procfile")
    socketio.run(app, host='0.0.0.0', port=port, debug=True, log_output=True)
