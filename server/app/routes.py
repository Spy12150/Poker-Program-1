from flask import Blueprint, jsonify, request
from app.game.poker import start_new_game
from app.game.ai import decide_action

bp = Blueprint('api', __name__)

# Game state (in-memory for now)
game_state = {}

@bp.route('/start-game', methods=['POST'])
def start_game():
    global game_state
    game_state = start_new_game()
    # Only expose player and AI hands plus community cards to the client
    response = {
        "player_hand": game_state["players"][0]["hand"],
        "ai_hand": game_state["players"][1]["hand"],
        "community": game_state["community"],
    }
    return jsonify(response)

@bp.route('/action', methods=['POST'])
def player_action():
    global game_state
    data = request.json
    action = data.get('action')

    # Simulate AI response (you'll later improve this)
    ai_decision = decide_action(game_state)

    # Update game state (basic logic for now)
    game_state['last_player_action'] = action
    game_state['ai_decision'] = ai_decision

    return jsonify(game_state)

