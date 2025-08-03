
import os
from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))  # Back to 5001 to match start script
    # Use SocketIO's run method instead of Flask's
    print(f"🚀 Starting SocketIO server on http://localhost:{port}")
    socketio.run(app, debug=False, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
