"""
Game abstraction system for Neural CFR

This module provides card and bet abstraction to reduce the massive poker game tree
to a manageable size for CFR training.
"""

import random
import itertools
import numpy as np
from typing import List, Dict, Tuple, Set, Optional
from collections import defaultdict
from dataclasses import dataclass

# Import from parent poker game
try:
    from ..hand_eval_lib import evaluate_hand
    from ..hardcode_ai.tier_config import TIERS, class_lookup
except ImportError:
    print("Warning: Could not import poker game modules")
    def evaluate_hand(hand, board):
        return random.randint(1000, 7462), "Unknown"
    
    # Fallback TIERS for standalone testing
    TIERS = [
        # Top tier - Premium pairs and AK
        [(14, 14), (13, 13), (12, 12), (11, 11), (10, 10), (14, 13, True), (14, 13, False)],
        # High pairs and strong suited connectors
        [(9, 9), (8, 8), (14, 12, True), (14, 11, True), (13, 12, True), (13, 11, True)],
        # Medium pairs and Broadway cards
        [(7, 7), (6, 6), (14, 10, True), (13, 10, True), (12, 11, True), (12, 10, True)],
        # Small pairs and suited aces
        [(5, 5), (4, 4), (3, 3), (2, 2), (14, 9, True), (14, 8, True), (14, 7, True)],
        # More suited connectors and offsuit broadways
        [(14, 12, False), (14, 11, False), (13, 12, False), (11, 10, True), (10, 9, True)],
        # Suited connectors and weak aces
        [(14, 6, True), (14, 5, True), (14, 4, True), (14, 3, True), (14, 2, True)],
        # More connectors
        [(9, 8, True), (8, 7, True), (7, 6, True), (6, 5, True), (5, 4, True)],
        # Offsuit connectors and weak holdings
        [(13, 10, False), (12, 11, False), (11, 10, False), (10, 9, False)],
        # Gappers and weak suited
        [(13, 9, True), (12, 9, True), (11, 9, True), (10, 8, True), (9, 7, True)],
        # Remaining hands (simplified)
        [(8, 6, True), (7, 5, True), (6, 4, True), (9, 8, False), (8, 7, False)]
    ]

@dataclass
class CardAbstraction:
    """Represents card abstraction for a specific street"""
    street: str
    num_buckets: int
    bucket_mapping: Dict[str, int]  # hand/board -> bucket_id

class BetAbstraction:
    """Represents betting action abstraction"""
    
    def __init__(self, bet_sizes_preflop: List[float], bet_sizes_postflop: List[float]):
        self.bet_sizes_preflop = bet_sizes_preflop
        self.bet_sizes_postflop = bet_sizes_postflop
        
    def get_legal_actions(self, street: str, pot_size: float, stack_size: float, 
                         facing_bet: bool = False) -> List[str]:
        """Get legal betting actions for current situation"""
        actions = []
        
        if facing_bet:
            actions.append('fold')
            actions.append('call')
        else:
            actions.append('check')
            
        # Add bet/raise actions
        bet_sizes = self.bet_sizes_preflop if street == 'preflop' else self.bet_sizes_postflop
        
        for size in bet_sizes:
            if size == float('inf'):
                if stack_size > 0:
                    actions.append('allin')
            else:
                bet_amount = pot_size * size if street != 'preflop' else size * 20  # 20 = big blind
                if bet_amount <= stack_size:
                    actions.append(f'bet_{size}' if not facing_bet else f'raise_{size}')
                    
        return actions

class GameAbstraction:
    """Main game abstraction system combining card and bet abstractions"""
    
    def __init__(self, config):
        self.config = config
        self.card_abstractions = {}
        self.bet_abstraction = BetAbstraction(
            config.BET_SIZES_PREFLOP,
            config.BET_SIZES_POSTFLOP
        )
        
        # Initialize card abstractions
        self._build_card_abstractions()
        
    def _build_card_abstractions(self):
        """Build card abstractions for each street"""
        print("Building card abstractions...")
        
        # Preflop abstraction using existing tier system
        self.card_abstractions['preflop'] = self._build_preflop_abstraction()
        
        # Postflop abstractions - start with simplified clustering
        self.card_abstractions['flop'] = self._build_postflop_abstraction('flop')
        self.card_abstractions['turn'] = self._build_postflop_abstraction('turn')
        self.card_abstractions['river'] = self._build_postflop_abstraction('river')
        
        print(f"Card abstractions built:")
        for street, abstraction in self.card_abstractions.items():
            print(f"  {street}: {abstraction.num_buckets} buckets")
    
    def _build_preflop_abstraction(self) -> CardAbstraction:
        """Build preflop abstraction using tier system"""
        bucket_mapping = {}
        
        # Use existing tier system - each tier becomes a bucket
        for tier_idx, tier_hands in enumerate(TIERS[:self.config.PREFLOP_BUCKETS]):
            for hand_tuple in tier_hands:
                # Convert tuple back to string representation
                hand_str = self._tuple_to_hand_string(hand_tuple)
                bucket_mapping[hand_str] = tier_idx
                
        return CardAbstraction(
            street='preflop',
            num_buckets=min(len(TIERS), self.config.PREFLOP_BUCKETS),
            bucket_mapping=bucket_mapping
        )
    
    def _tuple_to_hand_string(self, hand_tuple: Tuple) -> str:
        """Convert hand tuple to string representation"""
        rank_to_char = {14: 'A', 13: 'K', 12: 'Q', 11: 'J', 10: 'T', 
                       9: '9', 8: '8', 7: '7', 6: '6', 5: '5', 4: '4', 3: '3', 2: '2'}
        
        if len(hand_tuple) == 2:  # Pair
            rank = hand_tuple[0]
            return f"{rank_to_char[rank]}{rank_to_char[rank]}"
        else:  # Suited/offsuit
            high_rank, low_rank, is_suited = hand_tuple
            suffix = 's' if is_suited else 'o'
            return f"{rank_to_char[high_rank]}{rank_to_char[low_rank]}{suffix}"
    
    def _build_postflop_abstraction(self, street: str) -> CardAbstraction:
        """Build postflop abstraction using equity-based clustering"""
        num_buckets = getattr(self.config, f"{street.upper()}_BUCKETS")
        
        # For now, create a simplified abstraction
        # In a full implementation, this would use k-means clustering on equity distributions
        bucket_mapping = {}
        
        # Generate sample boards and cluster them
        sample_boards = self._generate_sample_boards(street)
        
        # Simple hash-based bucketing for initial implementation
        for i, board in enumerate(sample_boards[:1000]):  # Limit for initial implementation
            board_str = ''.join(board)
            bucket_id = hash(board_str) % num_buckets
            bucket_mapping[board_str] = bucket_id
            
        return CardAbstraction(
            street=street,
            num_buckets=num_buckets,
            bucket_mapping=bucket_mapping
        )
    
    def _generate_sample_boards(self, street: str) -> List[List[str]]:
        """Generate sample boards for clustering"""
        suits = ['s', 'h', 'd', 'c']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        deck = [r + s for r in ranks for s in suits]
        
        boards = []
        street_to_cards = {'flop': 3, 'turn': 4, 'river': 5}
        num_cards = street_to_cards[street]
        
        # Generate random boards
        for _ in range(10000):
            board = random.sample(deck, num_cards)
            boards.append(board)
            
        return boards
    
    def get_card_bucket(self, street: str, cards: List[str], board: List[str] = None) -> int:
        """Get card bucket for given cards and board"""
        if street == 'preflop':
            # Convert cards to hand string
            hand_str = self._cards_to_hand_string(cards)
            return self.card_abstractions['preflop'].bucket_mapping.get(hand_str, 0)
        else:
            # For postflop, use board
            board_str = ''.join(sorted(board)) if board else ''
            return self.card_abstractions[street].bucket_mapping.get(board_str, 0)
    
    def _cards_to_hand_string(self, cards: List[str]) -> str:
        """Convert two cards to hand string representation"""
        if len(cards) != 2:
            return 'XX'
            
        # Extract ranks and suits
        rank1, suit1 = cards[0][0], cards[0][1]
        rank2, suit2 = cards[1][0], cards[1][1]
        
        # Convert to standard format
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, 
                      '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        
        val1, val2 = rank_values[rank1], rank_values[rank2]
        
        if val1 == val2:  # Pair
            return f"{rank1}{rank2}"
        else:
            # Sort by rank (higher first)
            if val1 > val2:
                high_rank, low_rank = rank1, rank2
                high_suit, low_suit = suit1, suit2
            else:
                high_rank, low_rank = rank2, rank1
                high_suit, low_suit = suit2, suit1
                
            # Check if suited
            if high_suit == low_suit:
                return f"{high_rank}{low_rank}s"
            else:
                return f"{high_rank}{low_rank}o"
    
    def get_legal_actions(self, game_state: Dict) -> List[str]:
        """Get legal actions for current game state"""
        street = game_state.get('betting_round', 'preflop')
        pot = game_state.get('pot', 0)
        current_player_idx = game_state.get('current_player', 0)
        current_player = game_state['players'][current_player_idx]
        stack = current_player['stack']
        
        # Check if facing a bet
        current_bet = game_state.get('current_bet', 0)
        player_bet = current_player.get('current_bet', 0)
        facing_bet = current_bet > player_bet
        
        return self.bet_abstraction.get_legal_actions(street, pot, stack, facing_bet)
    
    def abstract_action(self, action: str, amount: int, game_state: Dict) -> str:
        """Convert game action to abstract action"""
        if action in ['fold', 'check', 'call']:
            return action
        elif action in ['raise', 'bet']:
            # Determine which bet size this corresponds to
            pot = game_state.get('pot', 0)
            street = game_state.get('betting_round', 'preflop')
            
            if street == 'preflop':
                # Map to closest preflop bet size
                bb_amount = amount / 20  # Assuming 20 = big blind
                bet_sizes = self.bet_abstraction.bet_sizes_preflop
            else:
                # Map to closest postflop bet size
                pot_fraction = amount / pot if pot > 0 else 0
                bet_sizes = self.bet_abstraction.bet_sizes_postflop
                
            # Find closest bet size
            closest_size = min(bet_sizes[:-1], key=lambda x: abs(x - (bb_amount if street == 'preflop' else pot_fraction)))
            
            return f"{action}_{closest_size}"
        else:
            return action
    
    def get_bucket_info(self) -> Dict[str, int]:
        """Get information about abstraction sizes"""
        return {
            'preflop_buckets': self.card_abstractions['preflop'].num_buckets,
            'flop_buckets': self.card_abstractions['flop'].num_buckets,
            'turn_buckets': self.card_abstractions['turn'].num_buckets,
            'river_buckets': self.card_abstractions['river'].num_buckets,
            'total_card_buckets': sum(abs.num_buckets for abs in self.card_abstractions.values()),
            'preflop_bet_actions': len(self.bet_abstraction.bet_sizes_preflop),
            'postflop_bet_actions': len(self.bet_abstraction.bet_sizes_postflop),
        }

def create_game_abstraction(config) -> GameAbstraction:
    """Factory function to create game abstraction"""
    return GameAbstraction(config)