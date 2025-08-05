"""
CFR Bot

This module implements the CFR bot that uses trained strategies to play poker.
It interfaces with the existing poker game engine.
"""

import random
import numpy as np
import torch
from typing import List, Dict, Tuple, Optional, Any
import os

from .config import get_config
from .game_abstraction import create_game_abstraction
from .information_set import create_information_set_manager, GameState, InformationSet
from .neural_networks import create_networks

class CFRBot:
    """
    CFR Bot that plays poker using trained strategies
    """
    
    def __init__(self, model_path: Optional[str] = None, config=None, simplified: bool = True):
        self.config = config or get_config(simplified=simplified)
        self.device = torch.device(self.config.DEVICE)
        
        # Initialize components
        self.game_abstraction = create_game_abstraction(self.config)
        self.info_set_manager = create_information_set_manager(self.game_abstraction)
        
        # Initialize neural networks
        self.networks = None
        try:
            self.networks = create_networks(self.config, str(self.device))
            if model_path and os.path.exists(model_path):
                self.load_model(model_path)
            else:
                print("Warning: No model loaded - using random strategy")
        except Exception as e:
            print(f"Warning: Could not initialize neural networks: {e}")
        
        # Strategy mode
        self.use_neural_strategy = True
        self.exploration_rate = 0.0  # No exploration during play
        
        print(f"Initialized CFR Bot")
        print(f"Model loaded: {model_path is not None and os.path.exists(model_path) if model_path else False}")
        print(f"Neural networks: {'Available' if self.networks else 'Not available'}")
    
    def decide_action(self, game_state: Dict[str, Any]) -> Tuple[str, int]:
        """
        Main decision function - interface with existing poker game
        
        Args:
            game_state: Game state from poker.py
            
        Returns:
            Tuple of (action, amount) for the game engine
        """
        try:
            # Convert game state to internal format
            cfr_game_state = self.convert_game_state(game_state)
            
            # Get information set
            ai_player = 1  # Assuming AI is always player 1
            info_set = self.info_set_manager.get_information_set(cfr_game_state, ai_player)
            
            # Get strategy
            if self.networks and self.use_neural_strategy:
                strategy = self.get_neural_strategy(info_set)
            else:
                strategy = self.get_tabular_strategy(info_set)
            
            # Sample action
            action = self.sample_action(strategy)
            
            # Convert back to game format
            game_action, amount = self.convert_to_game_action(action, game_state)
            
            print(f"CFR Bot chose: {game_action} {amount} (strategy: {strategy})")
            
            return game_action, amount
            
        except Exception as e:
            print(f"CFR Bot error: {e}")
            # Fallback to random action
            return self.get_fallback_action(game_state)
    
    def convert_game_state(self, game_state: Dict[str, Any]) -> GameState:
        """Convert poker game state to CFR game state format"""
        
        # Extract information
        street = game_state.get('betting_round', 'preflop')
        board = game_state.get('community', [])
        pot = game_state.get('pot', 0)
        current_bet = game_state.get('current_bet', 0)
        players = game_state.get('players', [])
        current_player = game_state.get('current_player', 0)
        action_history = game_state.get('action_history', [])
        
        # Convert action history to betting history
        betting_history = []
        for action_data in action_history[-10:]:  # Last 10 actions
            if isinstance(action_data, dict):
                action = action_data.get('action', 'unknown')
                betting_history.append(action)
            else:
                betting_history.append(str(action_data))
        
        return GameState(
            street=street,
            board=board,
            pot=pot,
            current_bet=current_bet,
            players=players,
            current_player=current_player,
            betting_history=betting_history,
            hand_history=[]
        )
    
    def get_neural_strategy(self, info_set: InformationSet) -> Dict[str, float]:
        """Get strategy using neural network"""
        if not self.networks:
            return self.get_tabular_strategy(info_set)
        
        try:
            # Prepare features
            features = torch.tensor(info_set.features).unsqueeze(0).to(self.device)
            
            # Create action mask
            action_map = self.get_action_mapping()
            action_mask = torch.zeros(1, len(action_map)).to(self.device)
            
            for action in info_set.legal_actions:
                if action in action_map:
                    action_mask[0, action_map[action]] = 1
            
            # Get prediction
            with torch.no_grad():
                action_probs = self.networks.predict_policy(features, action_mask)
                action_probs = action_probs.cpu().numpy()[0]
            
            # Convert to strategy
            strategy = {}
            total_prob = 0
            
            for action in info_set.legal_actions:
                if action in action_map:
                    prob = action_probs[action_map[action]]
                    strategy[action] = max(prob, 1e-6)
                    total_prob += strategy[action]
                else:
                    strategy[action] = 1e-6
                    total_prob += 1e-6
            
            # Normalize
            if total_prob > 0:
                for action in strategy:
                    strategy[action] /= total_prob
            else:
                # Uniform fallback
                prob = 1.0 / len(info_set.legal_actions)
                strategy = {action: prob for action in info_set.legal_actions}
            
            return strategy
            
        except Exception as e:
            print(f"Neural strategy failed: {e}")
            return self.get_tabular_strategy(info_set)
    
    def get_tabular_strategy(self, info_set: InformationSet) -> Dict[str, float]:
        """Get strategy using tabular regret matching"""
        # Use information set's built-in strategy
        strategy = info_set.get_strategy()
        
        if not strategy or sum(strategy.values()) == 0:
            # Uniform fallback
            if info_set.legal_actions:
                prob = 1.0 / len(info_set.legal_actions)
                strategy = {action: prob for action in info_set.legal_actions}
            else:
                strategy = {'fold': 1.0}  # Emergency fallback
        
        return strategy
    
    def get_action_mapping(self) -> Dict[str, int]:
        """Get action mapping for neural networks"""
        return {
            'fold': 0,
            'check': 1,
            'call': 2,
            'bet_0.5': 3,
            'bet_1.0': 4,
            'raise_2.5': 5,
            'allin': 6
        }
    
    def sample_action(self, strategy: Dict[str, float]) -> str:
        """Sample action from strategy"""
        if not strategy:
            return 'fold'
        
        # Add exploration if enabled
        if self.exploration_rate > 0:
            if random.random() < self.exploration_rate:
                return random.choice(list(strategy.keys()))
        
        # Weighted random selection
        actions = list(strategy.keys())
        weights = list(strategy.values())
        
        # Ensure weights are positive and sum to 1
        weights = [max(w, 1e-6) for w in weights]
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]
        
        return np.random.choice(actions, p=weights)
    
    def convert_to_game_action(self, cfr_action: str, game_state: Dict[str, Any]) -> Tuple[str, int]:
        """Convert CFR action to game engine format"""
        
        ai_player = game_state['players'][1]
        current_bet = game_state.get('current_bet', 0)
        pot = game_state.get('pot', 0)
        to_call = current_bet - ai_player.get('current_bet', 0)
        stack = ai_player.get('stack', 0)
        
        # Handle basic actions
        if cfr_action == 'fold':
            return ('fold', 0)
        elif cfr_action == 'check':
            if to_call > 0:
                return ('call', 0)  # Convert check to call if facing bet
            else:
                return ('check', 0)
        elif cfr_action == 'call':
            return ('call', 0)
        elif cfr_action == 'allin':
            total_amount = ai_player.get('current_bet', 0) + stack
            return ('raise', total_amount)
        
        # Handle bet/raise actions
        elif 'bet' in cfr_action or 'raise' in cfr_action:
            try:
                # Extract size from action (e.g., 'bet_0.5' -> 0.5)
                size_str = cfr_action.split('_')[1]
                size = float(size_str)
                
                if game_state.get('betting_round') == 'preflop':
                    # Preflop: size is in big blinds
                    bb = 20  # Assuming BB = 20
                    bet_amount = int(size * bb)
                else:
                    # Postflop: size is pot fraction
                    bet_amount = int(size * pot)
                
                # Ensure we have enough chips
                bet_amount = min(bet_amount, stack)
                
                # Calculate total amount including current bet
                total_amount = ai_player.get('current_bet', 0) + bet_amount
                
                return ('raise', total_amount)
                
            except (IndexError, ValueError):
                # Fallback for malformed action
                return ('call', 0) if to_call > 0 else ('check', 0)
        
        # Default fallback
        return ('fold', 0)
    
    def get_fallback_action(self, game_state: Dict[str, Any]) -> Tuple[str, int]:
        """Get fallback action when CFR fails"""
        ai_player = game_state['players'][1]
        current_bet = game_state.get('current_bet', 0)
        to_call = current_bet - ai_player.get('current_bet', 0)
        
        if to_call > 0:
            # Facing a bet - randomly call or fold
            if random.random() < 0.6:  # 60% call rate
                return ('call', 0)
            else:
                return ('fold', 0)
        else:
            # No bet - randomly check or bet
            if random.random() < 0.7:  # 70% check rate
                return ('check', 0)
            else:
                pot = game_state.get('pot', 0)
                bet_amount = min(ai_player['stack'], pot // 2)
                total_amount = ai_player.get('current_bet', 0) + bet_amount
                return ('raise', total_amount)
    
    def load_model(self, model_path: str):
        """Load trained model"""
        if not self.networks:
            print("No neural networks available for loading")
            return
        
        try:
            if model_path.endswith('.pkl'):
                # Load tabular strategies
                self.info_set_manager.load_strategies(model_path)
                self.use_neural_strategy = False
                print(f"Loaded tabular strategies from {model_path}")
            
            elif model_path.endswith('.pth'):
                # Load neural networks
                self.networks.load_models(model_path)
                self.use_neural_strategy = True
                print(f"Loaded neural networks from {model_path}")
            
            else:
                print(f"Unknown model format: {model_path}")
                
        except Exception as e:
            print(f"Error loading model: {e}")
    
    def set_exploration_rate(self, rate: float):
        """Set exploration rate for training/evaluation"""
        self.exploration_rate = max(0.0, min(1.0, rate))
        print(f"Set exploration rate to {self.exploration_rate:.3f}")
    
    def get_bot_info(self) -> Dict[str, Any]:
        """Get information about the bot"""
        return {
            'type': 'CFR Bot',
            'neural_networks': self.networks is not None,
            'strategy_mode': 'neural' if self.use_neural_strategy else 'tabular',
            'exploration_rate': self.exploration_rate,
            'information_sets': len(self.info_set_manager.information_sets),
            'game_abstraction': self.game_abstraction.get_bucket_info(),
        }
    
    def reset_for_new_hand(self):
        """Reset bot state for new hand (if needed)"""
        # CFR bot is stateless between hands
        pass

# Factory functions for different bot types
def create_cfr_bot(model_path: Optional[str] = None, simplified: bool = True) -> CFRBot:
    """Create a CFR bot with optional model loading"""
    return CFRBot(model_path=model_path, simplified=simplified)

def create_trained_cfr_bot(model_directory: str, simplified: bool = True) -> CFRBot:
    """Create CFR bot with the latest trained model"""
    
    # Look for latest model files
    neural_model = os.path.join(model_directory, "final_networks.pth")
    tabular_model = os.path.join(model_directory, "final_strategy.pkl")
    
    # Prefer neural model if available
    if os.path.exists(neural_model):
        return CFRBot(model_path=neural_model, simplified=simplified)
    elif os.path.exists(tabular_model):
        return CFRBot(model_path=tabular_model, simplified=simplified)
    else:
        print(f"No trained models found in {model_directory}")
        return CFRBot(simplified=simplified)

# Integration function for existing game
def decide_action_cfr(game_state: Dict[str, Any], bot_instance: Optional[CFRBot] = None) -> Tuple[str, int]:
    """
    Main interface function for existing poker game
    
    This function can be called from poker game engine like other AI functions
    """
    global _cfr_bot_instance
    
    # Create bot instance if not provided
    if bot_instance is None:
        if '_cfr_bot_instance' not in globals():
            _cfr_bot_instance = create_cfr_bot(simplified=True)
        bot_instance = _cfr_bot_instance
    
    return bot_instance.decide_action(game_state)

# Global bot instance for compatibility
_cfr_bot_instance = None