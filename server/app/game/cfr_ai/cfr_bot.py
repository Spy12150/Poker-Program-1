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
try:
    from .neural_networks import create_networks
except Exception as _e:
    # Allow running without torch/neural deps; will use tabular strategies if available
    create_networks = None  # type: ignore[assignment]
from .action_space import ACTION_MAP, ACTION_LIST

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
            if create_networks is not None:
                self.networks = create_networks(self.config, str(self.device))
            if model_path and os.path.exists(model_path):
                self.load_model(model_path)
            else:
                print("Warning: No model loaded - using random strategy or tabular if available")
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
            
            # Convert to strategy with strict normalization (set near-zero to 0)
            raw = [float(action_probs[action_map[a]]) if a in action_map else 0.0 for a in info_set.legal_actions]
            raw = np.array([max(v, 0.0) for v in raw], dtype=np.float64)
            s = raw.sum()
            if s <= 0 or not np.isfinite(s):
                prob = 1.0 / max(1, len(info_set.legal_actions))
                strategy = {a: prob for a in info_set.legal_actions}
            else:
                norm = raw / s
                norm = np.where(norm < 1e-8, 0.0, norm)
                s2 = norm.sum()
                if s2 == 0:
                    prob = 1.0 / max(1, len(info_set.legal_actions))
                    strategy = {a: prob for a in info_set.legal_actions}
                else:
                    norm = norm / s2
                    strategy = {a: float(norm[i]) for i, a in enumerate(info_set.legal_actions)}
            
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
        return ACTION_MAP
    
    def sample_action(self, strategy: Dict[str, float]) -> str:
        """Sample action from strategy"""
        if not strategy:
            return 'fold'

        # Add exploration if enabled
        if self.exploration_rate > 0 and random.random() < self.exploration_rate:
            return random.choice(list(strategy.keys()))

        # Robust weighted random selection (no tiny epsilons)
        actions = list(strategy.keys())
        probs = np.array([max(float(strategy.get(a, 0.0)), 0.0) for a in actions], dtype=np.float64)

        # Sanitize probabilities
        probs = np.nan_to_num(probs, nan=0.0, posinf=0.0, neginf=0.0)
        probs[probs < 0] = 0.0
        s = probs.sum()
        if s <= 0 or not np.isfinite(s):
            probs = np.ones_like(probs, dtype=np.float64) / len(probs)
        else:
            probs = probs / s
        # Final renormalization with clipping to avoid tiny nonzeros
        probs = probs / probs.sum()
        probs = np.where(probs < 1e-8, 0.0, probs)
        s2 = probs.sum()
        if s2 == 0:
            probs = np.ones_like(probs, dtype=np.float64) / len(probs)
        else:
            probs = probs / s2

        return np.random.choice(actions, p=probs)
    
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
                
                # Preflop first-in: size is BB multiples (2.5x)
                # Preflop facing raise: size indicates raise-to x of opponent bet
                # Postflop first-in: size is pot fraction
                # Postflop facing bet: size indicates raise-to x of opponent bet
                street = game_state.get('betting_round', 'preflop')
                to_call_local = max(0, current_bet - ai_player.get('current_bet', 0))
                facing_bet_local = to_call_local > 0
                
                if street == 'preflop':
                    bb = game_state.get('big_blind', 20)
                    if not facing_bet_local:
                        # first-in preflop: raise size in BBs
                        bet_amount = int(size * max(bb, 1))
                        total_amount = ai_player.get('current_bet', 0) + min(bet_amount, stack)
                        return ('raise', total_amount)
                    else:
                        # facing preflop raise: raise-to multiple of opponent bet (total)
                        opp_bet_total = to_call_local + ai_player.get('current_bet', 0)
                        target_total = int(size * opp_bet_total)
                        raise_to = min(target_total, ai_player.get('current_bet', 0) + stack)
                        return ('raise', raise_to)
                else:
                    if not facing_bet_local:
                        # first-in postflop: pot fraction
                        bet_amount = int(size * max(pot, 1))
                        total_amount = ai_player.get('current_bet', 0) + min(bet_amount, stack)
                        return ('raise', total_amount)
                    else:
                        # facing bet postflop: raise-to multiple of opponent bet (total)
                        opp_bet_total = to_call_local + ai_player.get('current_bet', 0)
                        target_total = int(size * opp_bet_total)
                        raise_to = min(target_total, ai_player.get('current_bet', 0) + stack)
                        return ('raise', raise_to)
                
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