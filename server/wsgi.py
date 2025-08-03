"""
WSGI entry point for production deployment
This file ensures compatibility with both Gunicorn and Railway hosting
"""
import os
import logging
from app import create_app, socketio

# Configure logging for production
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the Flask app with SocketIO support
app = create_app()

# For production deployments, we need to expose the SocketIO app
# This allows Gunicorn with eventlet workers to handle WebSocket connections
application = socketio

if __name__ == "__main__":
    # This is for local development only
    port = int(os.environ.get('PORT', 5001))
    logger.info(f"🚀 Starting SocketIO server on http://localhost:{port}")
    socketio.run(app, debug=False, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
else:
    # Production mode - Gunicorn will use the 'application' object
    logger.info("🌐 Starting in production mode with Gunicorn + eventlet")
