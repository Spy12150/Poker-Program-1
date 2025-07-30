"""
Game Service - Handles all game-related business logic
"""
import uuid
from typing import Dict, Tuple, Optional, Any
from app.game.poker import (
    start_new_game, apply_action, betting_round_over, advance_round, 
    next_player, showdown, prepare_next_hand, deal_remaining_cards
)
from app.game.hardcode_ai.ai_gto_enhanced import decide_action_gto


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
    
    def create_new_game(self) -> Tuple[str, Dict]:
        """
        Create a new poker game session
        
        Returns:
            Tuple of (game_id, game_state_with_metadata)
        """
        game_id = str(uuid.uuid4())
        game_state = start_new_game()
        
        self.game_sessions[game_id] = game_state
        
        # Create console logs for game start
        console_logs = [
            f"🎮 NEW GAME STARTED",
            f"🎲 Dealer Position: {game_state.get('dealer_pos')}",
            f"👤 Current Player: {game_state.get('current_player')}",
            f"🤖 AI is dealer: {game_state.get('dealer_pos') == 1}",
            f"🃏 AI Hand: {game_state['players'][1]['hand']}"
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
            f"🤖 AI DECISION START",
            f"🎯 AI Hand: {debug_info['ai_hand']}",
            f"🎲 Dealer Position: {debug_info['dealer_pos']} (AI is player 1)",
            f"👤 Current Player: {debug_info['current_player']}",
            f"💰 To Call: ${debug_info['to_call']}",
            f"🏆 Pot: ${debug_info['pot']}",
            f"📝 Action History: {debug_info['action_history']}"
        ])
        
        # Check if AI is dealer (Small Blind)
        ai_is_dealer = debug_info['dealer_pos'] == 1
        ai_position = "Small Blind (Dealer)" if ai_is_dealer else "Big Blind"
        console_logs.append(f"📍 AI Position: {ai_position}")
        
        # Check SB RFI conditions
        is_first_action = len(debug_info['action_history']) == 0
        console_logs.extend([
            f"🔍 SB RFI Check:",
            f"  - AI is dealer: {ai_is_dealer}",
            f"  - To call is 0: {debug_info['to_call'] == 0}",
            f"  - First action: {is_first_action}"
        ])
        
        should_use_sb_rfi = ai_is_dealer and debug_info['to_call'] == 0 and is_first_action
        console_logs.append(f"✅ Should use SB RFI: {should_use_sb_rfi}")
        
        # AI makes decision
        ai_action, ai_amount = decide_action_gto(game_state)
        
        console_logs.append(f"🎬 AI Action: {ai_action}")
        if ai_amount > 0:
            console_logs.append(f"💵 AI Amount: ${ai_amount}")
        
        apply_action(game_state, ai_action, ai_amount)
        self._log_action(game_state, 1, ai_action, ai_amount)
        
        # Process game flow after AI action
        result = self._process_game_flow(game_state)
        
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
    
    def _process_game_flow(self, game_state: Dict) -> Dict:
        """
        Process the game flow after an action
        
        Args:
            game_state: Current game state
            
        Returns:
            Dictionary with flow result and updated state
        """
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
                winners = showdown(game_state)
                # Clear current player since hand is over
                game_state['current_player'] = None
                # Record hand for analytics
                self.analytics.record_hand(game_state, winners, game_state.get('action_history', []))
                return {
                    'game_state': self._serialize_game_state(game_state),
                    'winners': winners,
                    'hand_over': True,
                    'message': f"{winners[0]['name']} wins the pot!"
                }
            
            # Check if no more betting actions are possible (e.g., one player all-in, others called)
            # Only check this if we have active current_bet values (i.e., before reset_bets is called)
            current_bet = game_state.get('current_bet', 0)
            all_in_players = [p for p in game_state['players'] if p['status'] == 'all-in']
            if len(all_in_players) > 0 and len(players_in_hand) > 1 and current_bet > 0:
                # Someone is all-in and there's an active bet, check if all others have matched it
                all_matched = True
                for player in players_in_hand:
                    if player['status'] == 'active' and player['current_bet'] != current_bet:
                        all_matched = False
                        break
                if all_matched:
                    # No more betting possible, go to showdown immediately
                    print(f"DEBUG: All-in situation detected - going to showdown")
                    deal_remaining_cards(game_state)
                    winners = showdown(game_state)
                    # Clear current player since hand is over
                    game_state['current_player'] = None
                    # Record hand for analytics
                    self.analytics.record_hand(game_state, winners, game_state.get('action_history', []))
                    return {
                        'game_state': self._serialize_game_state(game_state),
                        'winners': winners,
                        'hand_over': True,
                        'showdown': True,
                        'all_in_showdown': True,
                        'message': f"All-in showdown! Winner(s): {', '.join([w['name'] for w in winners])}"
                    }
            
            # Check if all remaining players are all-in (original logic)
            if len(active_players) == 0 and len(players_in_hand) > 1:
                # All players are all-in, deal remaining cards and go to showdown
                deal_remaining_cards(game_state)
                winners = showdown(game_state)
                # Clear current player since hand is over
                game_state['current_player'] = None
                # Record hand for analytics
                self.analytics.record_hand(game_state, winners, game_state.get('action_history', []))
                return {
                    'game_state': self._serialize_game_state(game_state),
                    'winners': winners,
                    'hand_over': True,
                    'showdown': True,
                    'all_in_showdown': True,
                    'message': f"All-in showdown! Winner(s): {', '.join([w['name'] for w in winners])}"
                }
            
            # If we're at river, go to showdown
            if game_state['betting_round'] == 'river':
                winners = showdown(game_state)
                # Clear current player since hand is over
                game_state['current_player'] = None
                # Record hand for analytics
                self.analytics.record_hand(game_state, winners, game_state.get('action_history', []))
                return {
                    'game_state': self._serialize_game_state(game_state),
                    'winners': winners,
                    'hand_over': True,
                    'showdown': True,
                    'message': f"Showdown! Winner(s): {', '.join([w['name'] for w in winners])}"
                }
            elif game_state['betting_round'] == 'showdown':
                # We've already advanced to showdown, trigger it
                winners = showdown(game_state)
                # Clear current player since hand is over
                game_state['current_player'] = None
                # Record hand for analytics
                self.analytics.record_hand(game_state, winners, game_state.get('action_history', []))
                return {
                    'game_state': self._serialize_game_state(game_state),
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
                
                # Check if we just advanced to showdown
                if game_state['betting_round'] == 'showdown':
                    # We advanced from river to showdown, trigger it immediately
                    winners = showdown(game_state)
                    # Clear current player since hand is over
                    game_state['current_player'] = None
                    # Record hand for analytics
                    self.analytics.record_hand(game_state, winners, game_state.get('action_history', []))
                    return {
                        'game_state': self._serialize_game_state(game_state),
                        'winners': winners,
                        'hand_over': True,
                        'showdown': True,
                        'message': f"Showdown! Winner(s): {', '.join([w['name'] for w in winners])}"
                    }
                
                # Set current player to first active player after dealer
                self._set_first_to_act(game_state)
                print(f"DEBUG: Set first to act: current_player = {game_state.get('current_player')}")
                advanced_to_new_round = True
                # Continue the loop to check if this new round is immediately over too
        
        # Only move to next player if we're in the middle of a betting round
        # Don't move to next player if we just advanced to a new round and set first to act
        betting_over = betting_round_over(game_state)
        print(f"DEBUG: Before next player check - betting_round_over: {betting_over}, advanced_to_new_round: {advanced_to_new_round}")
        
        if not betting_over and not advanced_to_new_round:
            print(f"DEBUG: Betting round not over, moving to next player from {game_state.get('current_player')}")
            next_player(game_state)
            print(f"DEBUG: Next player is now: {game_state.get('current_player')}")
        elif advanced_to_new_round:
            print(f"DEBUG: Just advanced to new round, staying with first to act player: {game_state.get('current_player')}")
        else:
            print(f"DEBUG: Not moving to next player - betting_over: {betting_over}, advanced_to_new_round: {advanced_to_new_round}")
        
        print(f"DEBUG: process_game_flow finished, current_player: {game_state.get('current_player')}, betting_round: {game_state.get('betting_round')}")
        
        return {
            'game_state': self._serialize_game_state(game_state),
            'hand_over': False
        }
    
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
            'dealer_pos': game_state['dealer_pos']
        }
