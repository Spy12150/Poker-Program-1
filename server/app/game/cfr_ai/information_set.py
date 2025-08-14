"""
Information Set representation for Neural CFR

An information set represents all game states that are indistinguishable to a player.
In poker, this includes the player's cards, the betting history, and public board cards.
"""

import numpy as np
import hashlib
from typing import List, Dict, Tuple, Optional, Any
from collections import defaultdict
from dataclasses import dataclass, field

@dataclass
class GameState:
    """Represents a complete game state"""
    street: str  # 'preflop', 'flop', 'turn', 'river'
    board: List[str]  # Community cards
    pot: float
    current_bet: float
    players: List[Dict[str, Any]]  # Player information
    current_player: int
    betting_history: List[str]  # Sequence of actions
    hand_history: List[List[str]]  # All actions taken this hand
    # Optional extras passed through from engine for better legality handling
    dealer_pos: int = 0
    big_blind: int = 20

@dataclass 
class InformationSet:
    """
    Represents an information set - all game states indistinguishable to a player
    """
    player: int
    street: str
    card_bucket: int  # Abstracted cards
    betting_history: str  # Sequence of betting actions
    pot_size_bucket: int  # Abstracted pot size
    
    # CFR data
    regret_sum: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    strategy_sum: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    reach_probabilities: Dict[int, float] = field(default_factory=lambda: defaultdict(float))
    
    # Neural CFR specific
    features: np.ndarray = field(default=None)
    legal_actions: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize after creation"""
        if self.features is None:
            self.features = self.create_features()
    
    def get_key(self) -> str:
        """Get unique key for this information set"""
        key_components = [
            str(self.player),
            self.street,
            str(self.card_bucket), 
            self.betting_history,
            str(self.pot_size_bucket)
        ]
        key_string = '|'.join(key_components)
        
        # Hash for memory efficiency
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def create_features(self) -> np.ndarray:
        """Create feature vector for neural networks"""
        features = []
        
        # Street encoding (one-hot)
        street_encoding = [0, 0, 0, 0]
        street_map = {'preflop': 0, 'flop': 1, 'turn': 2, 'river': 3}
        if self.street in street_map:
            street_encoding[street_map[self.street]] = 1
        features.extend(street_encoding)
        
        # Card bucket (normalized)
        max_buckets = 200  # Approximate max across all streets
        features.append(self.card_bucket / max_buckets)

        # Pot size bucket (normalized)
        max_pot_buckets = 20
        features.append(self.pot_size_bucket / max_pot_buckets)

        # Improved situational features (to_call, pot odds, SPR approx)
        # These require legal_actions and are approximated from betting history where possible
        # Defaults to zeros if unavailable
        to_call = 0.0
        pot = 1.0  # avoid div by zero
        spr = 1.0
        try:
            # Heuristic extraction from betting history length
            # For full integration, pass numeric to_call/pot into InformationSet
            action_intensity = min(len(self.betting_history.split(',')) if self.betting_history else 0, 10)
            to_call = action_intensity / 10.0
            pot = 1.0 + action_intensity
            spr = 1.0 / (1.0 + action_intensity)
        except Exception:
            pass
        pot_odds = min(to_call / pot, 1.0)
        features.append(pot_odds)
        features.append(spr)
        
        # Betting history features
        history_features = self.encode_betting_history()
        features.extend(history_features)
        
        # Player position
        features.append(self.player)  # 0 or 1 for heads-up
        
        return np.array(features, dtype=np.float32)
    
    def encode_betting_history(self, max_length: int = 20) -> List[float]:
        """Encode betting history as feature vector"""
        # Simple encoding: count of each action type
        action_counts = defaultdict(int)
        
        # Parse betting history string
        actions = self.betting_history.split(',') if self.betting_history else []
        
        for action in actions:
            if action.strip():
                action_counts[action.strip()] += 1
        
        # Create feature vector
        features = []
        action_types = ['check', 'call', 'fold', 'bet', 'raise', 'allin']
        
        for action_type in action_types:
            features.append(min(action_counts[action_type], 5) / 5.0)  # Normalize to 0-1
        
        # Add sequence length information
        features.append(min(len(actions), max_length) / max_length)
        
        # Pad to fixed length
        while len(features) < 12:
            features.append(0.0)
        
        # Truncate if too long
        return features[:12]
    
    def get_strategy(self, use_regret_matching: bool = True) -> Dict[str, float]:
        """Get current strategy using regret matching"""
        if not self.legal_actions:
            return {}
            
        if use_regret_matching:
            return self.regret_matching()
        else:
            # Uniform random strategy
            prob = 1.0 / len(self.legal_actions)
            return {action: prob for action in self.legal_actions}
    
    def regret_matching(self) -> Dict[str, float]:
        """Regret matching algorithm to convert regrets to strategy"""
        strategy = {}
        normalizing_sum = 0
        
        # Calculate positive regrets
        for action in self.legal_actions:
            regret = max(0, self.regret_sum[action])
            strategy[action] = regret
            normalizing_sum += regret
        
        # Normalize to probabilities
        if normalizing_sum > 0:
            for action in self.legal_actions:
                strategy[action] /= normalizing_sum
        else:
            # Uniform strategy if no positive regrets
            prob = 1.0 / len(self.legal_actions)
            strategy = {action: prob for action in self.legal_actions}
        
        return strategy
    
    def update_regrets(self, action_utilities: Dict[str, float], reach_probability: float):
        """Update regret sums for all actions (CFR+)"""
        # Calculate counterfactual value
        strategy_utilities = sum(prob * action_utilities.get(action, 0)
                                 for action, prob in self.get_strategy().items())
        
        # Update cumulative regrets and apply CFR+ clipping (regret matching plus)
        for action in self.legal_actions:
            action_utility = action_utilities.get(action, 0)
            regret_increment = action_utility - strategy_utilities
            self.regret_sum[action] += reach_probability * regret_increment
            # CFR+: clip cumulative regrets at zero
            if self.regret_sum[action] < 0:
                self.regret_sum[action] = 0.0
    
    def update_strategy_sum(self, reach_probability: float, iteration: int = 1):
        """Update cumulative strategy sum with iteration weighting (linear)."""
        # Weight later iterations more (linear weighting by iteration number)
        weight = max(1, int(iteration))
        current_strategy = self.get_strategy()
        
        for action in self.legal_actions:
            self.strategy_sum[action] += weight * reach_probability * current_strategy[action]
    
    def get_average_strategy(self) -> Dict[str, float]:
        """Get average strategy over all iterations"""
        avg_strategy = {}
        normalizing_sum = sum(self.strategy_sum.values())
        
        if normalizing_sum > 0:
            for action in self.legal_actions:
                avg_strategy[action] = self.strategy_sum[action] / normalizing_sum
        else:
            # Uniform strategy if no history
            prob = 1.0 / len(self.legal_actions) if self.legal_actions else 0
            avg_strategy = {action: prob for action in self.legal_actions}
        
        return avg_strategy

class InformationSetManager:
    """Manages all information sets for CFR training"""
    
    def __init__(self, game_abstraction):
        self.game_abstraction = game_abstraction
        self.information_sets: Dict[str, InformationSet] = {}
        self.creation_count = 0
    
    def get_information_set(self, game_state: GameState, player: int) -> InformationSet:
        """Get or create information set for current game state and player"""
        
        # Extract relevant information
        street = game_state.street
        card_bucket = self._get_card_bucket(game_state, player)
        betting_history = self._get_betting_history(game_state)
        pot_size_bucket = self._get_pot_size_bucket(game_state.pot)
        legal_actions = self._get_legal_actions(game_state)
        
        # Create information set
        info_set = InformationSet(
            player=player,
            street=street,
            card_bucket=card_bucket,
            betting_history=betting_history,
            pot_size_bucket=pot_size_bucket,
            legal_actions=legal_actions
        )
        
        # Check if we've seen this before
        key = info_set.get_key()
        
        if key not in self.information_sets:
            self.information_sets[key] = info_set
            self.creation_count += 1
            
            if self.creation_count % 1000000 == 0:
                print(f"Created {self.creation_count:,} information sets")
        else:
            # Update legal actions in case they changed
            self.information_sets[key].legal_actions = legal_actions
        
        return self.information_sets[key]
    
    def _get_card_bucket(self, game_state: GameState, player: int) -> int:
        """Get card bucket for player's cards and board"""
        player_cards = game_state.players[player].get('hand', [])
        
        return self.game_abstraction.get_card_bucket(
            game_state.street, 
            player_cards, 
            game_state.board
        )
    
    def _get_betting_history(self, game_state: GameState) -> str:
        """Convert betting history to string representation"""
        # Use the most recent betting sequence
        if game_state.betting_history:
            return ','.join(game_state.betting_history[-20:])  # Last 20 actions
        return ""
    
    def _get_pot_size_bucket(self, pot_size: float) -> int:
        """Bucket pot size into discrete categories"""
        # Simple pot size buckets (in big blinds)
        bb_size = pot_size / 20  # Assuming BB = 20
        
        if bb_size <= 2:
            return 0
        elif bb_size <= 5:
            return 1
        elif bb_size <= 10:
            return 2
        elif bb_size <= 20:
            return 3
        elif bb_size <= 50:
            return 4
        elif bb_size <= 100:
            return 5
        else:
            return 6
    
    def _get_legal_actions(self, game_state: GameState) -> List[str]:
        """Get legal actions from game abstraction"""
        # Convert game_state to dict format expected by game_abstraction
        game_dict = {
            'betting_round': game_state.street,
            'pot': game_state.pot,
            'current_player': game_state.current_player,
            'players': game_state.players,
            'current_bet': game_state.current_bet,
            # Pass through dealer_pos and big_blind when available for preflop logic
            'dealer_pos': getattr(game_state, 'dealer_pos', 0),
            'big_blind': getattr(game_state, 'big_blind', 20),
        }
        actions = self.game_abstraction.get_legal_actions(game_dict)

        # Safety post-filter: enforce requested preflop action sets (HU)
        try:
            if game_state.street == 'preflop' and len(game_state.players) == 2:
                cp = game_state.current_player
                dealer_pos = getattr(game_state, 'dealer_pos', 0)
                facing_bet = game_state.current_bet > game_state.players[cp].get('current_bet', 0)
                is_sb = (cp == dealer_pos)
                if is_sb:
                    # SB first decision (even though to_call > 0 due to BB): allow 2.5x
                    allowed = {'fold', 'call', 'raise_2.5'}
                else:
                    if facing_bet:
                        # BB facing a raise: 3x/5x
                        allowed = {'fold', 'call', 'raise_3.0', 'raise_5.0'}
                    else:
                        # BB vs limp: check or iso-raise 3x/5x
                        allowed = {'check', 'raise_3.0', 'raise_5.0'}
                actions = [a for a in actions if a in allowed]
        except Exception:
            pass

        return actions
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about information sets"""
        return {
            'total_information_sets': len(self.information_sets),
            'creation_count': self.creation_count,
            'memory_usage_mb': len(self.information_sets) * 0.001,  # Rough estimate
        }
    
    def save_strategies(self, filepath: str):
        """Save all strategies to file"""
        import pickle
        
        strategies = {}
        for key, info_set in self.information_sets.items():
            strategies[key] = {
                'average_strategy': info_set.get_average_strategy(),
                'regret_sum': dict(info_set.regret_sum),
                'strategy_sum': dict(info_set.strategy_sum)
            }
        
        with open(filepath, 'wb') as f:
            pickle.dump(strategies, f)
        
        print(f"Saved {len(strategies)} strategies to {filepath}")
    
    def load_strategies(self, filepath: str):
        """Load strategies from file"""
        import pickle
        
        try:
            with open(filepath, 'rb') as f:
                strategies = pickle.load(f)
            
            loaded_count = 0
            for key, strategy_data in strategies.items():
                if key in self.information_sets:
                    info_set = self.information_sets[key]
                    info_set.regret_sum.update(strategy_data['regret_sum'])
                    info_set.strategy_sum.update(strategy_data['strategy_sum'])
                    loaded_count += 1
            
            print(f"Loaded {loaded_count} strategies from {filepath}")
            
        except FileNotFoundError:
            print(f"Strategy file {filepath} not found")
        except Exception as e:
            print(f"Error loading strategies: {e}")

def create_information_set_manager(game_abstraction) -> InformationSetManager:
    """Factory function to create information set manager"""
    return InformationSetManager(game_abstraction)