"""
WebSocket Event Handlers - Define all WebSocket event handlers for the poker game
"""
from flask_socketio import SocketIO, emit, disconnect
from flask import request
from app.services.websocket_service import WebSocketService
from app.services.game_service import GameService
from app.services.validation_service import ValidationService
import json


# Global service instances
game_service = None
websocket_service = None
validation_service = None


def register_websocket_handlers(socketio: SocketIO):
    """Register all WebSocket event handlers"""
    global game_service, websocket_service, validation_service
    
    # Initialize services
    try:
        game_service = GameService()
        websocket_service = WebSocketService(socketio)
        validation_service = ValidationService()
    except Exception as e:
        print(f"Failed to initialize services for WebSocket: {e}")
        return
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        sid = request.sid
        websocket_service.handle_connect(sid)
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        sid = request.sid
        websocket_service.handle_disconnect(sid)
    
    @socketio.on('join_game')
    def handle_join_game(data):
        """Handle player joining a game"""
        sid = request.sid
        websocket_service.handle_join_game(sid, data)
    
    @socketio.on('start_game')
    def handle_start_game(data):
        """Handle starting a new game"""
        try:
            ai_type = data.get('ai_type', 'bladework_v2')
            print(f"Starting game with AI type: {ai_type}")  # Debug log
            
            game_id, response = game_service.create_new_game(ai_type)
            print(f"Game created with ID: {game_id}")  # Debug log
            print(f"Response data structure: {type(response)}")  # Debug log
            
            # Validate response data before sending
            if not response or not isinstance(response, dict):
                print(f"Invalid response data: {response}")
                emit('error', {'message': 'Invalid game data generated'})
                return
            
            # Join the player to the game room
            websocket_service.handle_join_game(request.sid, {'game_id': game_id})
            
            # Broadcast game start
            websocket_service.broadcast_game_start(game_id, response)
            
            # Check if AI needs to act first in the initial game
            if response.get('current_player') == 1:
                print(f"AI goes first in game {game_id}, triggering AI action")  # Debug log
                socketio.start_background_task(_process_ai_action, game_id)
            
        except Exception as e:
            print(f"Error in handle_start_game: {str(e)}")  # Debug log
            emit('error', {'message': f'Failed to start game: {str(e)}'})
    
    @socketio.on('player_action')
    def handle_player_action(data):
        """Handle player action (fold, call, check, raise)"""
        try:
            game_id = data.get('game_id')
            action = data.get('action')
            amount = data.get('amount', 0)
            
            print(f"Player action: {action}, amount: {amount}, game_id: {game_id}")  # Debug log
            
            # Validate input
            is_valid, error_msg = validation_service.validate_game_id(game_id)
            if not is_valid:
                print(f"Invalid game ID: {error_msg}")  # Debug log
                emit('error', {'message': error_msg})
                return
            
            is_valid, error_msg = validation_service.validate_player_action(action, amount)
            if not is_valid:
                print(f"Invalid player action: {error_msg}")  # Debug log
                emit('error', {'message': error_msg})
                return
            
            # Convert amount to int for raise actions
            if action == 'raise':
                amount = int(amount)
            
            # Execute the action
            result = game_service.execute_player_action(game_id, action, amount)
            print(f"Player action result type: {type(result)}")  # Debug log
            
            # Validate result before broadcasting
            if not result or not isinstance(result, dict):
                print(f"Invalid result from player action: {result}")
                emit('error', {'message': 'Invalid game state after action'})
                return
            
            # Broadcast the result to all players in the game
            websocket_service.broadcast_action_result(game_id, result)
            
            # Check if AI needs to act after player action
            if (result.get('game_state', {}).get('current_player') == 1 and 
                not result.get('hand_over', False)):
                # Schedule AI action after a brief delay
                socketio.start_background_task(_process_ai_action, game_id)
                
        except ValueError as e:
            print(f"ValueError in player action: {str(e)}")  # Debug log
            emit('error', {'message': str(e)})
        except Exception as e:
            print(f"Unexpected error in player action: {str(e)}")  # Debug log
            emit('error', {'message': 'Internal server error'})
    
    @socketio.on('new_hand')
    def handle_new_hand(data):
        """Handle starting a new hand"""
        try:
            game_id = data.get('game_id')
            
            is_valid, error_msg = validation_service.validate_game_id(game_id)
            if not is_valid:
                emit('error', {'message': error_msg})
                return
            
            game_state = game_service.start_new_hand(game_id)
            
            # Broadcast new hand to all players
            websocket_service.broadcast_new_hand(game_id, game_state)
            
            # Check if AI needs to act first in the new hand
            if game_state.get('current_player') == 1:
                socketio.start_background_task(_process_ai_action, game_id)
                
        except ValueError as e:
            emit('error', {'message': str(e)})
        except Exception as e:
            emit('error', {'message': 'Internal server error'})
    
    @socketio.on('new_round')
    def handle_new_round(data):
        """Handle starting a new round (reset stacks)"""
        try:
            game_id = data.get('game_id')
            
            is_valid, error_msg = validation_service.validate_game_id(game_id)
            if not is_valid:
                emit('error', {'message': error_msg})
                return
            
            game_state = game_service.start_new_round(game_id)
            
            # Broadcast new round to all players
            websocket_service.broadcast_game_update(game_id, 'new_round', game_state)
            
            # Check if AI needs to act first in the new round
            if game_state.get('current_player') == 1:
                socketio.start_background_task(_process_ai_action, game_id)
            
        except ValueError as e:
            emit('error', {'message': str(e)})
        except Exception as e:
            emit('error', {'message': 'Internal server error'})


def _process_ai_action(game_id: str):
    """Background task to process AI action"""
    try:
        import time
        time.sleep(1)  # Brief delay for UX
        
        result = game_service.execute_ai_turn(game_id)
        
        # Broadcast AI action result
        websocket_service.broadcast_ai_action(game_id, result)
        
        # If hand is over, broadcast that
        if result.get('hand_over'):
            websocket_service.broadcast_hand_over(game_id, result)
        
        # Check if AI needs to act again (in case of multiple AI actions in sequence)
        elif (result.get('game_state', {}).get('current_player') == 1 and 
              not result.get('hand_over', False)):
            # Recursively process next AI action
            _process_ai_action(game_id)
            
    except Exception as e:
        print(f"Error in AI action processing: {e}")
        websocket_service.send_error(game_id, f"AI error: {str(e)}")
