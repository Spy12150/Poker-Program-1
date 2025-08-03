"""
WSGI entry point for production deployment
"""
from app import create_app

# Create the Flask app
app = create_app()

# This is what Gunicorn will use
application = app

if __name__ == "__main__":
    # For local testing
    app.run(host='0.0.0.0', port=5001)
