from flask import Blueprint, jsonify, request
from app.game.poker import (
    start_new_game, apply_action, betting_round_over, advance_round, 
    award_pot, next_player, showdown, prepare_next_hand, deal_remaining_cards
)
from app.game.ai_gto_enhanced import decide_action_gto
from app.game.analytics import analytics
import uuid

bp = Blueprint('api', __name__)

# Game sessions (in-memory for now)
game_sessions = {}

@bp.route('/start-game', methods=['POST'])
def start_game():
    """Start a new game session"""
    game_id = str(uuid.uuid4())
    game_state = start_new_game()
    
    game_sessions[game_id] = game_state
    
    response = serialize_game_state(game_state)
    response['game_id'] = game_id
    
    # Create console logs for game start
    console_logs = []
    console_logs.append(f"🎮 NEW GAME STARTED")
    console_logs.append(f"🎲 Dealer Position: {game_state.get('dealer_pos')}")
    console_logs.append(f"👤 Current Player: {game_state.get('current_player')}")
    console_logs.append(f"🤖 AI is dealer: {game_state.get('dealer_pos') == 1}")
    console_logs.append(f"🃏 AI Hand: {game_state['players'][1]['hand']}")
    
    # Add debug info for initial game state
    response['debug_info'] = {
        'dealer_pos': game_state.get('dealer_pos'),
        'current_player': game_state.get('current_player'),
        'ai_is_dealer': game_state.get('dealer_pos') == 1,
        'ai_hand': game_state['players'][1]['hand'],
        'blinds_posted': True
    }
    response['console_logs'] = console_logs
    
    return jsonify(response)

@bp.route('/player-action', methods=['POST'])
def player_action():
    """Handle player action and process game flow"""
    data = request.json
    game_id = data.get('game_id')
    action = data.get('action')
    amount = data.get('amount', 0)
    
    # Validation
    if not game_id or game_id not in game_sessions:
        return jsonify({'error': 'Invalid game session'}), 400
    if not action or action not in ['fold', 'call', 'check', 'raise']:
        return jsonify({'error': 'Invalid action'}), 400
    
    game_state = game_sessions[game_id]
    
    # Validate it's player's turn (assuming player 0 is human)
    if game_state['current_player'] != 0:
        return jsonify({'error': 'Not your turn'}), 400
    
    # Additional validation for raise amounts
    if action == 'raise':
        player = game_state['players'][0]
        # Let the poker.py logic handle minimum raise calculation
        # Just do basic validation that amount is positive and not more than stack
        max_raise = player['stack'] + player['current_bet']  # All-in amount
        
        if amount <= 0:
            return jsonify({'error': 'Raise amount must be positive'}), 400
        if amount > max_raise:
            return jsonify({'error': f'Maximum bet is ${max_raise} (all-in)'}), 400
    
    try:
        # Apply player action
        apply_action(game_state, action, amount)
        log_action(game_state, 0, action, amount)
        
        # Process game flow after player action
        result = process_game_flow(game_state)
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/game-state/<game_id>', methods=['GET'])
def get_game_state(game_id):
    """Get current game state"""
    if game_id not in game_sessions:
        return jsonify({'error': 'Game not found'}), 404
    
    game_state = game_sessions[game_id]
    return jsonify(serialize_game_state(game_state))

@bp.route('/process-ai-turn', methods=['POST'])
def process_ai_turn():
    """Process AI turn and continue game flow"""
    data = request.json
    game_id = data.get('game_id')
    
    if not game_id or game_id not in game_sessions:
        return jsonify({'error': 'Invalid game session'}), 400
    
    game_state = game_sessions[game_id]
    
    # Only process if it's AI's turn and AI is active
    if game_state['current_player'] == 1 and game_state['players'][1]['status'] == 'active':
        # Create debug messages for browser console
        console_logs = []
        
        # Debug info for browser console
        debug_info = {
            'dealer_pos': game_state.get('dealer_pos'),
            'current_player': game_state.get('current_player'),
            'ai_hand': game_state['players'][1]['hand'],
            'action_history': game_state.get('action_history', []),
            'to_call': game_state.get('current_bet', 0) - game_state['players'][1]['current_bet'],
            'pot': game_state['pot']
        }
        
        # Add debug messages
        console_logs.append(f"🤖 AI DECISION START")
        console_logs.append(f"🎯 AI Hand: {debug_info['ai_hand']}")
        console_logs.append(f"🎲 Dealer Position: {debug_info['dealer_pos']} (AI is player 1)")
        console_logs.append(f"👤 Current Player: {debug_info['current_player']}")
        console_logs.append(f"💰 To Call: ${debug_info['to_call']}")
        console_logs.append(f"🏆 Pot: ${debug_info['pot']}")
        console_logs.append(f"📝 Action History: {debug_info['action_history']}")
        
        # Check if AI is dealer (Small Blind)
        ai_is_dealer = debug_info['dealer_pos'] == 1
        ai_position = "Small Blind (Dealer)" if ai_is_dealer else "Big Blind"
        console_logs.append(f"📍 AI Position: {ai_position}")
        
        # Check SB RFI conditions
        is_first_action = len(debug_info['action_history']) == 0
        console_logs.append(f"🔍 SB RFI Check:")
        console_logs.append(f"  - AI is dealer: {ai_is_dealer}")
        console_logs.append(f"  - To call is 0: {debug_info['to_call'] == 0}")
        console_logs.append(f"  - First action: {is_first_action}")
        
        should_use_sb_rfi = ai_is_dealer and debug_info['to_call'] == 0 and is_first_action
        console_logs.append(f"✅ Should use SB RFI: {should_use_sb_rfi}")
        
        # AI makes decision
        ai_action, ai_amount = decide_action_gto(game_state)
        
        console_logs.append(f"🎬 AI Action: {ai_action}")
        if ai_amount > 0:
            console_logs.append(f"💵 AI Amount: ${ai_amount}")
        
        apply_action(game_state, ai_action, ai_amount)
        log_action(game_state, 1, ai_action, ai_amount)
        
        # Process game flow after AI action
        result = process_game_flow(game_state)
        
        # Add AI action message
        ai_message = f"AI {ai_action}"
        if ai_amount > 0:
            ai_message += f" ${ai_amount}"
        
        # Combine messages if there's already a message from game flow
        if result.get('message'):
            result['message'] = f"{ai_message}. {result['message']}"
        else:
            result['message'] = ai_message
        
        # Add debug info to response
        result['debug_info'] = debug_info
        result['console_logs'] = console_logs
        result['ai_action_debug'] = {
            'action': ai_action,
            'amount': ai_amount,
            'hand': game_state['players'][1]['hand'],
            'should_use_sb_rfi': should_use_sb_rfi
        }
        
        return jsonify(result)
    else:
        # Not AI's turn, just return current state
        return jsonify({
            'game_state': serialize_game_state(game_state),
            'hand_over': False,
        })

@bp.route('/new-hand', methods=['POST'])
def new_hand():
    """Start a new hand in existing game"""
    data = request.json
    game_id = data.get('game_id')
    
    if not game_id or game_id not in game_sessions:
        return jsonify({'error': 'Invalid game session'}), 400
    
    game_state = game_sessions[game_id]
    
    # Check if both players have chips
    active_players = [p for p in game_state['players'] if p['stack'] > 0]
    if len(active_players) < 2:
        return jsonify({'error': 'Game over - insufficient players with chips'}), 400
    
    # Prepare next hand
    prepare_next_hand(game_state)
    game_state['action_history'] = []
    
    return jsonify(serialize_game_state(game_state))

@bp.route('/analytics', methods=['GET'])
def get_analytics():
    """Get game analytics and statistics"""
    summary = analytics.get_session_summary()
    recent_hands = analytics.get_recent_hands(5)
    
    return jsonify({
        'summary': summary,
        'recent_hands': recent_hands
    })

def process_game_flow(game_state):
    """Process the game flow after an action"""
    print(f"DEBUG: process_game_flow called, current_player: {game_state.get('current_player')}, betting_round: {game_state.get('betting_round')}")
    
    # Flag to track if we advanced to a new round
    advanced_to_new_round = False
    
    # Check if betting round is over and advance rounds as needed
    while betting_round_over(game_state):
        print(f"DEBUG: Betting round over, advancing from {game_state.get('betting_round')}")
        
        # Check if game is over (only one player left in hand)
        players_in_hand = [p for p in game_state['players'] if p['status'] in ['active', 'all-in']]
        active_players = [p for p in game_state['players'] if p['status'] == 'active']
        
        if len(players_in_hand) <= 1:
            # Someone folded or everyone else is eliminated, award pot
            winners = award_pot(game_state)
            # Record hand for analytics
            analytics.record_hand(game_state, [{'name': winners[0]}], game_state.get('action_history', []))
            return {
                'game_state': serialize_game_state(game_state),
                'winners': winners,
                'hand_over': True,
                'message': f"{winners[0]} wins the pot!"
            }
        
        # Check if all remaining players are all-in
        if len(active_players) == 0 and len(players_in_hand) > 1:
            # All players are all-in, deal remaining cards and go to showdown
            deal_remaining_cards(game_state)
            winners = showdown(game_state)
            # Record hand for analytics
            analytics.record_hand(game_state, winners, game_state.get('action_history', []))
            return {
                'game_state': serialize_game_state(game_state),
                'winners': winners,
                'hand_over': True,
                'showdown': True,
                'all_in_showdown': True,
                'message': f"All-in showdown! Winner(s): {', '.join([w['name'] for w in winners])}"
            }
        
        # If we're at river, go to showdown
        if game_state['betting_round'] == 'river':
            winners = showdown(game_state)
            # Record hand for analytics
            analytics.record_hand(game_state, winners, game_state.get('action_history', []))
            return {
                'game_state': serialize_game_state(game_state),
                'winners': winners,
                'hand_over': True,
                'showdown': True,
                'message': f"Showdown! Winner(s): {', '.join([w['name'] for w in winners])}"
            }
        else:
            # Advance to next street
            print(f"DEBUG: Advancing to next street from {game_state.get('betting_round')}")
            advance_round(game_state)
            print(f"DEBUG: Advanced to {game_state.get('betting_round')}")
            # Set current player to first active player after dealer
            set_first_to_act(game_state)
            print(f"DEBUG: Set first to act: current_player = {game_state.get('current_player')}")
            advanced_to_new_round = True
            # Continue the loop to check if this new round is immediately over too
    
    # Only move to next player if we're in the middle of a betting round
    # Don't move to next player if we just advanced to a new round and set first to act
    if not betting_round_over(game_state) and not advanced_to_new_round:
        print(f"DEBUG: Betting round not over, moving to next player from {game_state.get('current_player')}")
        next_player(game_state)
        print(f"DEBUG: Next player is now: {game_state.get('current_player')}")
    elif advanced_to_new_round:
        print(f"DEBUG: Just advanced to new round, staying with first to act player: {game_state.get('current_player')}")
    
    print(f"DEBUG: process_game_flow finished, current_player: {game_state.get('current_player')}, betting_round: {game_state.get('betting_round')}")
    
    return {
        'game_state': serialize_game_state(game_state),
        'hand_over': False
    }

def set_first_to_act(game_state):
    """Set the first active player to act for a new betting round"""
    num_players = len(game_state['players'])
    
    # In heads-up poker, postflop the button/dealer acts first
    if num_players == 2:
        # Heads-up: dealer acts first postflop
        first_pos = game_state['dealer_pos']
    else:
        # Multi-way: player after dealer acts first
        first_pos = (game_state['dealer_pos'] + 1) % num_players
    
    for i in range(num_players):
        pos = (first_pos + i) % num_players
        if game_state['players'][pos]['status'] == 'active' and game_state['players'][pos]['stack'] > 0:
            game_state['current_player'] = pos
            return
    
    # If no active players found, something is wrong
    game_state['current_player'] = 0

def log_action(game_state, player_idx, action, amount):
    """Log player action for UI feedback"""
    player = game_state['players'][player_idx]
    entry = {
        'player': player['name'],
        'action': action,
        'round': game_state['betting_round'],
        'pot_after': game_state['pot']
    }
    
    if action == 'raise':
        entry['amount'] = amount
    elif action == 'call':
        to_call = game_state.get('current_bet', 0) - player['current_bet']
        entry['amount'] = min(to_call, player['stack'] + player['current_bet'])
    
    game_state['action_history'].append(entry)

def serialize_game_state(game_state):
    """Convert game state to JSON-safe format for frontend"""
    return {
        'game_id': game_state.get('game_id'),
        'player_hand': game_state['players'][0]['hand'],
        'community': game_state['community'],
        'pot': game_state['pot'],
        'players': [
            {
                'name': p['name'],
                'stack': p['stack'],
                'current_bet': p['current_bet'], 
                'status': p['status'],
                'hand': p['hand']  # Include hand for showdown display
            } for p in game_state['players']
        ],
        'current_player': game_state['current_player'],
        'betting_round': game_state['betting_round'],
        'current_bet': game_state['current_bet'],
        'last_bet_amount': game_state.get('last_bet_amount', 0),
        'action_history': game_state.get('action_history', []),
        'dealer_pos': game_state['dealer_pos']
    }

