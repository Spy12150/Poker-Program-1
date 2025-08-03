"""
Game Service - Handles all game-related business logic
"""
import uuid
from typing import Dict, Tuple, Optional, Any
from app.game.poker import (
    start_new_game, apply_action, betting_round_over, advance_round, 
    next_player, showdown, prepare_next_hand, deal_remaining_cards
)
from app.game.hardcode_ai.ai_bladework_v2 import decide_action_bladeworkv2
from app.game.hardcode_ai.ai_froggie import decide_action as decide_action_froggie


class GameService:
    """Service class for managing poker game logic and state"""
    
    def __init__(self, analytics_service=None):
        self.game_sessions: Dict[str, Dict] = {}
        # Import here to avoid circular imports
        if analytics_service is None:
            from app.game.analytics import analytics
            self.analytics = analytics
        else:
            self.analytics = analytics_service
    
    def _get_ai_function(self, ai_type: str):
        """Get the appropriate AI decision function based on type"""
        ai_functions = {
            'bladework_v2': decide_action_bladeworkv2,
            'froggie': decide_action_froggie
        }
        return ai_functions.get(ai_type, decide_action_bladeworkv2)  # Default to bladework_v2
    
    def create_new_game(self, ai_type: str = 'bladework_v2') -> Tuple[str, Dict]:
        """
        Create a new poker game session
        
        Args:
            ai_type: Type of AI to use ('bladework_v2' or 'froggie')
        
        Returns:
            Tuple of (game_id, game_state_with_metadata)
        """
        game_id = str(uuid.uuid4())
        game_state = start_new_game()
        
        # Store AI type in game state for later use
        game_state['ai_type'] = ai_type
        
        # Update AI player name and logic based on selected AI type
        ai_info = {
            'froggie': {
                'name': 'Froggie',
                'logic': 'Random'
            },
            'bladework_v2': {
                'name': 'Bladework v2',
                'logic': 'Hard Coded'
            }
        }
        
        selected_ai_info = ai_info.get(ai_type, ai_info['bladework_v2'])
        game_state['players'][1]['name'] = selected_ai_info['name']
        game_state['ai_info'] = {
            'name': selected_ai_info['name'],
            'logic': selected_ai_info['logic'],
            'type': ai_type
        }
        
        self.game_sessions[game_id] = game_state
        
        # Create console logs for game start
        console_logs = [
            f"NEW GAME STARTED",
            f"Dealer Position: {game_state.get('dealer_pos')}",
            f"Current Player: {game_state.get('current_player')}",
            f"AI is dealer: {game_state.get('dealer_pos') == 1}",
            f"AI Hand: {game_state['players'][1]['hand']}"
        ]
        
        # Build response with debug info
        response = self._serialize_game_state(game_state)
        response['game_id'] = game_id
        response['debug_info'] = {
            'dealer_pos': game_state.get('dealer_pos'),
            'current_player': game_state.get('current_player'),
            'ai_is_dealer': game_state.get('dealer_pos') == 1,
            'ai_hand': game_state['players'][1]['hand'],
            'blinds_posted': True
        }
        response['console_logs'] = console_logs
        
        return game_id, response
    
    def get_game_state(self, game_id: str) -> Optional[Dict]:
        """
        Get current game state for a session
        
        Args:
            game_id: The game session ID
            
        Returns:
            Serialized game state or None if not found
        """
        if game_id not in self.game_sessions:
            return None
        
        game_state = self.game_sessions[game_id]
        return self._serialize_game_state(game_state)
    
    def execute_player_action(self, game_id: str, action: str, amount: int = 0) -> Dict:
        """
        Execute a player action and process game flow
        
        Args:
            game_id: The game session ID
            action: The action to perform ('fold', 'call', 'check', 'raise')
            amount: The amount for raise actions
            
        Returns:
            Dictionary with result of action and updated game state
            
        Raises:
            ValueError: If game not found, invalid action, or invalid amount
        """
        if game_id not in self.game_sessions:
            raise ValueError('Invalid game session')
        
        if action not in ['fold', 'call', 'check', 'raise']:
            raise ValueError('Invalid action')
        
        game_state = self.game_sessions[game_id]
        
        # Validate it's player's turn (assuming player 0 is human)
        if game_state['current_player'] != 0:
            raise ValueError('Not your turn')
        
        # Additional validation for raise amounts
        if action == 'raise':
            player = game_state['players'][0]
            max_raise = player['stack'] + player['current_bet']  # All-in amount
            
            if amount <= 0:
                raise ValueError('Raise amount must be positive')
            if amount > max_raise:
                raise ValueError(f'Maximum bet is ${max_raise} (all-in)')
        
        # Apply player action
        apply_action(game_state, action, amount)
        self._log_action(game_state, 0, action, amount)
        
        # Process game flow after player action
        return self._process_game_flow(game_state)
    
    def execute_ai_turn(self, game_id: str) -> Dict:
        """
        Process AI turn and continue game flow
        
        Args:
            game_id: The game session ID
            
        Returns:
            Dictionary with AI action result and updated game state
            
        Raises:
            ValueError: If game not found
        """
        if game_id not in self.game_sessions:
            raise ValueError('Invalid game session')
        
        game_state = self.game_sessions[game_id]
        
        print(f"DEBUG: execute_ai_turn called - current_player: {game_state['current_player']}, AI status: {game_state['players'][1]['status']}")
        
        # Only process if it's AI's turn and AI is active
        if game_state['current_player'] != 1 or game_state['players'][1]['status'] != 'active':
            print(f"DEBUG: AI can't act - current_player: {game_state['current_player']}, AI status: {game_state['players'][1]['status']}")
            # Not AI's turn, just return current state
            return {
                'game_state': self._serialize_game_state(game_state),
                'hand_over': False,
            }
        
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
        console_logs.extend([
            f"AI DECISION START",
            f"AI Hand: {debug_info['ai_hand']}",
            f"Dealer Position: {debug_info['dealer_pos']} (AI is player 1)",
            f"Current Player: {debug_info['current_player']}",
            f"To Call: ${debug_info['to_call']}",
            f"Pot: ${debug_info['pot']}",
            f"Action History: {debug_info['action_history']}"
        ])
        
        # Check if AI is dealer (Small Blind)
        ai_is_dealer = debug_info['dealer_pos'] == 1
        ai_position = "Small Blind (Dealer)" if ai_is_dealer else "Big Blind"
        console_logs.append(f"AI Position: {ai_position}")
        
        # Check SB RFI conditions
        is_first_action = len(debug_info['action_history']) == 0
        console_logs.extend([
            f"SB RFI Check:",
            f"  - AI is dealer: {ai_is_dealer}",
            f"  - To call is 0: {debug_info['to_call'] == 0}",
            f"  - First action: {is_first_action}"
        ])
        
        should_use_sb_rfi = ai_is_dealer and debug_info['to_call'] == 0 and is_first_action
        console_logs.append(f"Should use SB RFI: {should_use_sb_rfi}")
        
        # AI makes decision using the selected AI type
        ai_type = game_state.get('ai_type', 'bladework_v2')
        ai_decision_func = self._get_ai_function(ai_type)
        ai_action, ai_amount = ai_decision_func(game_state)
        
        console_logs.append(f"AI Action: {ai_action}")
        if ai_amount > 0:
            console_logs.append(f"AI Amount: ${ai_amount}")
        
        apply_action(game_state, ai_action, ai_amount)
        self._log_action(game_state, 1, ai_action, ai_amount)
        
        # Process game flow after AI action
        result = self._process_game_flow(game_state)
        
        # Add AI action message with proper verb tense
        action_verb = ai_action
        if ai_action == 'call':
            action_verb = 'calls'
        elif ai_action == 'raise':
            action_verb = 'raises'
        elif ai_action == 'fold':
            action_verb = 'folds'
        elif ai_action == 'check':
            action_verb = 'checks'
        
        ai_message = f"AI {action_verb}"
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
        
        # Debug the final result
        print(f"DEBUG: Final result current_player: {result['game_state']['current_player']}")
        print(f"DEBUG: Final result betting_round: {result['game_state']['betting_round']}")
        
        return result
    
    def start_new_hand(self, game_id: str) -> Dict:
        """
        Start a new hand in existing game
        
        Args:
            game_id: The game session ID
            
        Returns:
            Serialized game state for new hand
            
        Raises:
            ValueError: If game not found or insufficient players with chips
        """
        if game_id not in self.game_sessions:
            raise ValueError('Invalid game session')
        
        game_state = self.game_sessions[game_id]
        
        # Check if both players have chips
        active_players = [p for p in game_state['players'] if p['stack'] > 0]
        if len(active_players) < 2:
            raise ValueError('Game over - insufficient players with chips')
        
        # Prepare next hand
        prepare_next_hand(game_state)
        game_state['action_history'] = []
        
        return self._serialize_game_state(game_state)
    
    def start_new_round(self, game_id: str) -> Dict:
        """
        Start a new round in existing game (reset chip stacks to starting amount)
        
        Args:
            game_id: The game session ID
            
        Returns:
            Serialized game state for new round
            
        Raises:
            ValueError: If game not found
        """
        if game_id not in self.game_sessions:
            raise ValueError('Invalid game session')
        
        game_state = self.game_sessions[game_id]
        
        # Reset both players' chip stacks to starting amount
        from app.game.config import STARTING_STACK
        for player in game_state['players']:
            player['stack'] = STARTING_STACK
            player['status'] = 'active'
        
        # Prepare next hand with reset stacks
        prepare_next_hand(game_state)
        game_state['action_history'] = []
        
        return self._serialize_game_state(game_state)
    
    def _process_game_flow(self, game_state: Dict) -> Dict:
        print(f"DEBUG: process_game_flow called, current_player: {game_state.get('current_player')}, betting_round: {game_state.get('betting_round')}")

        # Loop to handle cases where a street ends and immediately leads to another (e.g. pre-flop all-in)
        while True:
            # First, check if the current betting round is over.
            if betting_round_over(game_state):
                print(f"DEBUG: Betting round {game_state['betting_round']} is over.")
                
                # Check for hand-ending conditions
                players_in_hand = [p for p in game_state['players'] if p['status'] in ['active', 'all-in']]
                active_players = [p for p in players_in_hand if p['status'] == 'active']

                # Condition 1: Only one player left (everyone else folded)
                if len(players_in_hand) <= 1:
                    print("DEBUG: Hand ending because only one player remains.")
                    winners = showdown(game_state)
                    self.analytics.record_hand(game_state, winners, game_state.get('action_history', []))
                    return {'game_state': self._serialize_game_state(game_state), 'winners': winners, 'hand_over': True, 'message': f"{winners[0]['name']} wins the pot!"}

                # Condition 2: All remaining players are all-in
                if not active_players:
                    print("DEBUG: All players are all-in. Dealing remaining cards for showdown.")
                    deal_remaining_cards(game_state)
                    winners = showdown(game_state)
                    self.analytics.record_hand(game_state, winners, game_state.get('action_history', []))
                    return {'game_state': self._serialize_game_state(game_state), 'winners': winners, 'hand_over': True, 'showdown': True, 'all_in_showdown': True, 'message': "All-in showdown!"}

                # Condition 3: River betting is done
                if game_state['betting_round'] == 'river':
                    print("DEBUG: River betting is over. Proceeding to showdown.")
                    winners = showdown(game_state)
                    self.analytics.record_hand(game_state, winners, game_state.get('action_history', []))
                    return {'game_state': self._serialize_game_state(game_state), 'winners': winners, 'hand_over': True, 'showdown': True, 'message': "Showdown!"}
                
                # If no hand-ending condition is met, advance to the next street.
                print(f"DEBUG: Advancing to next street from {game_state.get('betting_round')}")
                advance_round(game_state)
                self._set_first_to_act(game_state)
                print(f"DEBUG: Advanced to {game_state.get('betting_round')}. New turn for player {game_state['current_player']}")
                # The loop continues to check the state of the new round.

            else:
                # If the betting round is NOT over, just find the next player.
                next_player(game_state)
                print(f"DEBUG: Betting continues. Next player is {game_state['current_player']}")
                return {'game_state': self._serialize_game_state(game_state), 'hand_over': False}

    
    def _set_first_to_act(self, game_state: Dict) -> None:
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
    
    def _log_action(self, game_state: Dict, player_idx: int, action: str, amount: int) -> None:
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
    
    def _serialize_game_state(self, game_state: Dict) -> Dict:
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
            'dealer_pos': game_state['dealer_pos'],
            'big_blind': game_state.get('big_blind', 10),  # Include big blind for frontend calculations
            'ai_info': game_state.get('ai_info', {'name': 'Bladework v2', 'logic': 'Hard Coded', 'type': 'bladework_v2'})
        }
