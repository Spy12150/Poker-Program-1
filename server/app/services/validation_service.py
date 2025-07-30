"""
Validation Service - Handles input validation and business rule enforcement
"""
from typing import Dict, Any, Tuple, Optional


class ValidationService:
    """Service class for validating game inputs and business rules"""
    
    @staticmethod
    def validate_game_id(game_id: Optional[str]) -> Tuple[bool, str]:
        """
        Validate game ID format and presence
        
        Args:
            game_id: The game ID to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not game_id:
            return False, "Game ID is required"
        
        if not isinstance(game_id, str):
            return False, "Game ID must be a string"
        
        if len(game_id.strip()) == 0:
            return False, "Game ID cannot be empty"
        
        return True, ""
    
    @staticmethod
    def validate_player_action(action: Optional[str], amount: Optional[Any] = None) -> Tuple[bool, str]:
        """
        Validate player action inputs
        
        Args:
            action: The action to validate
            amount: The amount for raise actions
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        valid_actions = ['fold', 'call', 'check', 'raise']
        
        if not action:
            return False, "Action is required"
        
        if action not in valid_actions:
            return False, f"Invalid action. Must be one of: {', '.join(valid_actions)}"
        
        # Validate amount for raise actions
        if action == 'raise':
            if amount is None:
                return False, "Amount is required for raise action"
            
            try:
                amount_int = int(amount)
                if amount_int <= 0:
                    return False, "Raise amount must be positive"
            except (ValueError, TypeError):
                return False, "Raise amount must be a valid number"
        
        return True, ""
    
    @staticmethod
    def validate_raise_amount(game_state: Dict, player_idx: int, amount: int) -> Tuple[bool, str]:
        """
        Validate raise amount against game rules and player stack
        
        Args:
            game_state: Current game state
            player_idx: Index of the player making the raise
            amount: Amount being raised
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if player_idx >= len(game_state['players']):
            return False, "Invalid player index"
        
        player = game_state['players'][player_idx]
        
        # Check if player has enough chips
        max_raise = player['stack'] + player['current_bet']  # All-in amount
        
        if amount > max_raise:
            return False, f"Maximum bet is ${max_raise} (all-in)"
        
        # Check minimum raise requirements (this logic should match poker.py)
        current_bet = game_state.get('current_bet', 0)
        last_bet_amount = game_state.get('last_bet_amount', 0)
        big_blind = 20  # From config
        
        if current_bet == 0:
            # First bet of the round - minimum is big blind
            min_raise = big_blind
        else:
            # Must raise by at least the size of the last bet/raise
            min_raise = current_bet + max(last_bet_amount, big_blind)
        
        if amount < min_raise:
            return False, f"Minimum raise is ${min_raise}"
        
        return True, ""
    
    @staticmethod
    def validate_player_turn(game_state: Dict, expected_player: int) -> Tuple[bool, str]:
        """
        Validate that it's the expected player's turn
        
        Args:
            game_state: Current game state
            expected_player: Index of player who should be acting
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        current_player = game_state.get('current_player')
        
        if current_player != expected_player:
            return False, "Not your turn"
        
        # Check if player is active
        if expected_player >= len(game_state['players']):
            return False, "Invalid player index"
        
        player = game_state['players'][expected_player]
        if player['status'] not in ['active', 'all-in']:
            return False, "Player is not active in this hand"
        
        return True, ""
    
    @staticmethod
    def validate_new_hand_requirements(game_state: Dict) -> Tuple[bool, str]:
        """
        Validate that a new hand can be started
        
        Args:
            game_state: Current game state
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if there are enough players with chips
        active_players = [p for p in game_state['players'] if p['stack'] > 0]
        
        if len(active_players) < 2:
            return False, "Game over - insufficient players with chips"
        
        return True, ""
    
    @staticmethod
    def validate_game_state(game_state: Dict) -> Tuple[bool, str]:
        """
        Validate basic game state structure and consistency
        
        Args:
            game_state: Game state to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(game_state, dict):
            return False, "Game state must be a dictionary"
        
        required_keys = ['players', 'pot', 'current_player', 'betting_round']
        for key in required_keys:
            if key not in game_state:
                return False, f"Missing required key: {key}"
        
        # Validate players structure
        players = game_state.get('players', [])
        if not isinstance(players, list) or len(players) == 0:
            return False, "Players must be a non-empty list"
        
        for i, player in enumerate(players):
            if not isinstance(player, dict):
                return False, f"Player {i} must be a dictionary"
            
            required_player_keys = ['name', 'stack', 'current_bet', 'status']
            for key in required_player_keys:
                if key not in player:
                    return False, f"Player {i} missing required key: {key}"
        
        # Validate current_player index
        current_player = game_state.get('current_player')
        if current_player is not None and (current_player < 0 or current_player >= len(players)):
            return False, "Invalid current_player index"
        
        return True, ""
