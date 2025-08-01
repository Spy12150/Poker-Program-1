
import os
from app import create_app

print("=== STARTING FLASK APP ===")
print(f"PORT environment variable: {os.environ.get('PORT', 'Not set')}")

app = create_app()
print("✅ Flask app created successfully")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"🚀 Starting Flask server on 0.0.0.0:{port}")
    app.run(debug=False, host='0.0.0.0', port=port)
else:
    print("⚠️ run.py not being executed as main module")
