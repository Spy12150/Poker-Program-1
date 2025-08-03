"""
WebSocket Service - Handles real-time communication for poker game
"""
from flask_socketio import SocketIO, emit, join_room, leave_room
from typing import Dict, Any, Optional
import uuid


class WebSocketService:
    """Service class for managing WebSocket connections and real-time game events"""
    
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
        self.user_rooms: Dict[str, str] = {}  # user_id -> room_id mapping
        self.room_games: Dict[str, str] = {}  # room_id -> game_id mapping
        
    def handle_connect(self, sid: str) -> None:
        """Handle new WebSocket connection"""
        print(f"WebSocket client connected: {sid}")
        emit('connected', {'status': 'Connected to poker server'})
        
    def handle_disconnect(self, sid: str) -> None:
        """Handle WebSocket disconnection"""
        print(f"WebSocket client disconnected: {sid}")
        # Clean up any room associations for this session
        if sid in self.user_rooms:
            room_id = self.user_rooms[sid]
            leave_room(room_id)
            del self.user_rooms[sid]
    
    def handle_join_game(self, sid: str, data: Dict[str, Any]) -> None:
        """Handle player joining a game room"""
        game_id = data.get('game_id')
        if not game_id:
            emit('error', {'message': 'Game ID required'})
            return
            
        # Create a room for this game
        room_id = f"game_{game_id}"
        join_room(room_id)
        
        # Track user-room and room-game associations
        self.user_rooms[sid] = room_id
        self.room_games[room_id] = game_id
        
        print(f"Player {sid} joined game room {room_id}")
        emit('joined_game', {'game_id': game_id, 'room_id': room_id})
    
    def broadcast_game_update(self, game_id: str, event_type: str, data: Dict[str, Any]) -> None:
        """Broadcast game state update to all players in the game"""
        room_id = f"game_{game_id}"
        print(f"Broadcasting {event_type} to room {room_id}")
        self.socketio.emit(event_type, data, room=room_id)
    
    def broadcast_action_result(self, game_id: str, action_data: Dict[str, Any]) -> None:
        """Broadcast the result of a player action"""
        self.broadcast_game_update(game_id, 'action_result', action_data)
    
    def broadcast_ai_action(self, game_id: str, ai_data: Dict[str, Any]) -> None:
        """Broadcast AI action to all players"""
        self.broadcast_game_update(game_id, 'ai_action', ai_data)
    
    def broadcast_hand_over(self, game_id: str, hand_data: Dict[str, Any]) -> None:
        """Broadcast hand completion to all players"""
        self.broadcast_game_update(game_id, 'hand_over', hand_data)
    
    def broadcast_new_hand(self, game_id: str, hand_data: Dict[str, Any]) -> None:
        """Broadcast new hand start to all players"""
        self.broadcast_game_update(game_id, 'new_hand', hand_data)
    
    def broadcast_game_start(self, game_id: str, game_data: Dict[str, Any]) -> None:
        """Broadcast game start to all players"""
        self.broadcast_game_update(game_id, 'game_start', game_data)
    
    def send_error(self, sid: str, message: str) -> None:
        """Send error message to specific client"""
        self.socketio.emit('error', {'message': message}, room=sid)
    
    def send_message(self, sid: str, message: str) -> None:
        """Send info message to specific client"""
        self.socketio.emit('message', {'message': message}, room=sid)
