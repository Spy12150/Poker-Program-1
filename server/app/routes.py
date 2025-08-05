from flask import Blueprint, jsonify
from app.services.analytics_service import AnalyticsService

bp = Blueprint('api', __name__)

# Initialize minimal services for WebSocket-only app
try:
    analytics_service = AnalyticsService()
except Exception as e:
    print(f"Failed to initialize AnalyticsService: {e}")
    analytics_service = None

@bp.after_request
def after_request(response):
    """Add CORS headers to all responses"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@bp.route('/', methods=['GET'])
def health_check():
    """Health check endpoint for Railway deployment"""
    status = {
        'status': 'OK', 
        'message': 'WebSocket Poker Server Running!',
        'websocket_enabled': True,
        'services': {
            'analytics_service': analytics_service is not None
        }
    }
    return jsonify(status)

# All game functionality now handled via WebSocket
# HTTP endpoints removed - WebSocket only!

@bp.route('/analytics', methods=['GET'])
def get_analytics():
    """Get game analytics and statistics"""
    try:
        analytics_data = analytics_service.get_analytics_report()
        return jsonify(analytics_data)
    except Exception as e:
        return jsonify({'error': 'Failed to retrieve analytics'}), 500



