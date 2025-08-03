# Production Deployment Guide

## What Was Fixed for Railway

### The Problem
Railway was failing because:
1. `gunicorn run:app` couldn't handle Flask-SocketIO properly
2. Missing eventlet worker class for WebSocket support
3. Incorrect WSGI application reference

### The Solution

#### 1. Created `wsgi.py` Production Entry Point
```python
# server/wsgi.py - Production WSGI application
application = socketio  # Exposes SocketIO app for Gunicorn
```

#### 2. Updated `Procfile` for SocketIO Support
```bash
# server/Procfile
web: gunicorn wsgi:application --worker-class eventlet --workers 1 --bind 0.0.0.0:$PORT
```

#### 3. Added `eventlet` Dependency
```
# server/requirements.txt
eventlet==0.33.3  # Required for SocketIO in production
```

## For Future Deployments

### Railway
1. Push your changes to trigger a new deployment
2. Railway will now use the SocketIO-compatible setup
3. Health check endpoint at `/` should pass

### Other Hosting Platforms
- **Heroku**: Same Procfile will work
- **DigitalOcean**: Use the wsgi.py entry point
- **AWS/GCP**: Configure to use `wsgi:application`

## Local Development vs Production

### Local Development (HTTP - Recommended)
```bash
./start-dev.sh  # Uses original HTTP version
```

### Local Development (WebSocket Testing)
```bash
cd server && python run.py  # Uses SocketIO
cd client && npm run dev
```

### Production (Automatic WebSocket)
```bash
# Railway automatically uses:
gunicorn wsgi:application --worker-class eventlet --workers 1
```

## Verification

After deployment, check:
1. Health check: `https://your-app.railway.app/` returns status OK
2. WebSocket support: Real-time features work in production
3. Logs: No more health check timeout errors

The WebSocket features will now work properly in production while maintaining backward compatibility with HTTP endpoints!
