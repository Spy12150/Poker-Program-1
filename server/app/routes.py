from flask import Blueprint, jsonify, request
from app.services.game_service import GameService
from app.services.analytics_service import AnalyticsService
from app.services.validation_service import ValidationService

bp = Blueprint('api', __name__)

# Initialize services
game_service = GameService()
analytics_service = AnalyticsService()
validation_service = ValidationService()

@bp.route('/', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({'status': 'OK', 'message': 'Flask app is running!'})

@bp.route('/start-game', methods=['POST'])
def start_game():
    """Start a new game session"""
    try:
        game_id, response = game_service.create_new_game()
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': f'Failed to start game: {str(e)}'}), 500

@bp.route('/player-action', methods=['POST'])
def player_action():
    """Handle player action and process game flow"""
    data = request.json
    game_id = data.get('game_id')
    action = data.get('action')
    amount = data.get('amount', 0)
    
    # Basic validation
    is_valid, error_msg = validation_service.validate_game_id(game_id)
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    is_valid, error_msg = validation_service.validate_player_action(action, amount)
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    try:
        # Convert amount to int for raise actions
        if action == 'raise':
            amount = int(amount)
        
        # Execute the action through service
        result = game_service.execute_player_action(game_id, action, amount)
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/game-state/<game_id>', methods=['GET'])
def get_game_state(game_id):
    """Get current game state"""
    is_valid, error_msg = validation_service.validate_game_id(game_id)
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    game_state = game_service.get_game_state(game_id)
    if game_state is None:
        return jsonify({'error': 'Game not found'}), 404
    
    return jsonify(game_state)

@bp.route('/process-ai-turn', methods=['POST'])
def process_ai_turn():
    """Process AI turn and continue game flow"""
    print(f"DEBUG: process-ai-turn route called")
    data = request.json
    game_id = data.get('game_id')
    print(f"DEBUG: game_id from request: {game_id}")
    
    is_valid, error_msg = validation_service.validate_game_id(game_id)
    if not is_valid:
        print(f"DEBUG: validation failed: {error_msg}")
        return jsonify({'error': error_msg}), 400
    
    print(f"DEBUG: validation passed, calling game_service.execute_ai_turn")
    try:
        result = game_service.execute_ai_turn(game_id)
        print(f"DEBUG: execute_ai_turn returned: {type(result)}")
        return jsonify(result)
    except ValueError as e:
        print(f"DEBUG: ValueError in execute_ai_turn: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f"DEBUG: Exception in execute_ai_turn: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/new-hand', methods=['POST'])
def new_hand():
    """Start a new hand in existing game"""
    data = request.json
    game_id = data.get('game_id')
    
    is_valid, error_msg = validation_service.validate_game_id(game_id)
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    try:
        game_state = game_service.start_new_hand(game_id)
        return jsonify(game_state)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/new-round', methods=['POST'])
def new_round():
    """Start a new round in existing game (reset chip stacks)"""
    data = request.json
    game_id = data.get('game_id')
    
    is_valid, error_msg = validation_service.validate_game_id(game_id)
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    try:
        game_state = game_service.start_new_round(game_id)
        return jsonify(game_state)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/analytics', methods=['GET'])
def get_analytics():
    """Get game analytics and statistics"""
    try:
        analytics_data = analytics_service.get_analytics_report()
        return jsonify(analytics_data)
    except Exception as e:
        return jsonify({'error': 'Failed to retrieve analytics'}), 500



