"""
WSGI entry point for production deployment with SocketIO support
"""
from app import create_app, socketio

# Create the Flask app with SocketIO
app = create_app()

# This is what Gunicorn will use - must be the SocketIO app for WebSocket support
application = socketio

if __name__ == "__main__":
    # For Railway deployment - use SocketIO's built-in server
    import os
    port = int(os.environ.get('PORT', 5001))
    print(f"🚀 Starting WebSocket server on port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False, log_output=True)
