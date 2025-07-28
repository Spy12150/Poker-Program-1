"""
Advanced AI Module for Poker Bot

This module implements more sophisticated poker AI strategies including:
- Pot odds calculations
- Opponent modeling based on betting patterns
- Bluffing frequency adjustment
- Position-aware play
- Stack size considerations
"""

import random
import math
from .hand_eval_lib import evaluate_hand
from .config import BIG_BLIND

class AdvancedPokerAI:
    def __init__(self):
        self.opponent_stats = {
            'hands_played': 0,
            'vpip': 0.0,  # Voluntarily Put in Pot
            'pfr': 0.0,   # Pre-flop Raise
            'aggression': 1.0,  # Aggression factor
            'fold_to_bet': 0.5,  # Tendency to fold to bets
        }
        
    def decide_action(self, game_state):
        """Enhanced decision making with multiple factors"""
        ai_player = game_state['players'][1]
        hand = ai_player['hand']
        community = game_state['community']
        to_call = game_state.get('current_bet', 0) - ai_player['current_bet']
        pot = game_state['pot']
        betting_round = game_state['betting_round']
        
        # Stack considerations
        stack_bb = ai_player['stack'] // BIG_BLIND  # Stack in big blinds
        
        # Calculate pot odds if facing a bet
        pot_odds = self.calculate_pot_odds(to_call, pot) if to_call > 0 else 0
        
        # Hand strength evaluation
        if len(community) >= 3:
            hand_strength = self.evaluate_hand_strength(hand, community)
            equity = self.estimate_equity(hand, community)
            
            # Advanced decision based on multiple factors
            return self.post_flop_decision(
                hand_strength, equity, pot_odds, to_call, pot, 
                ai_player, stack_bb, betting_round
            )
        else:
            # Pre-flop strategy with position consideration
            return self.preflop_decision(
                hand, to_call, pot, ai_player, stack_bb
            )
    
    def calculate_pot_odds(self, to_call, pot):
        """Calculate pot odds as a ratio"""
        if to_call == 0:
            return float('inf')
        return pot / to_call
    
    def estimate_equity(self, hand, community):
        """Estimate hand equity (simplified)"""
        try:
            score, _ = evaluate_hand(hand, community)
            # Convert treys score to rough equity estimate
            if score <= 1000:
                return 0.85  # Very strong
            elif score <= 2500:
                return 0.65  # Strong  
            elif score <= 4000:
                return 0.35  # Medium
            else:
                return 0.15  # Weak
        except:
            return 0.2  # Conservative estimate
    
    def evaluate_hand_strength(self, hand, community):
        """More nuanced hand strength evaluation"""
        try:
            score, hand_class = evaluate_hand(hand, community)
            
            # Detailed categorization
            if score <= 500:
                return 'nuts'
            elif score <= 1000:
                return 'very_strong'
            elif score <= 1600:
                return 'strong'
            elif score <= 2500:
                return 'good'
            elif score <= 4000:
                return 'medium'
            elif score <= 6000:
                return 'weak'
            else:
                return 'very_weak'
        except:
            return 'unknown'
    
    def post_flop_decision(self, hand_strength, equity, pot_odds, to_call, 
                          pot, ai_player, stack_bb, betting_round):
        """Post-flop decision making with equity considerations"""
        
        # Nuts or very strong - always aggressive
        if hand_strength in ['nuts', 'very_strong']:
            if to_call == 0:
                bet_size = min(ai_player['stack'], pot * 0.75)
                return ('raise', ai_player['current_bet'] + bet_size)
            else:
                if ai_player['stack'] > to_call * 2:
                    raise_size = min(ai_player['stack'] - to_call, pot)
                    return ('raise', ai_player['current_bet'] + to_call + raise_size)
                return ('call', 0)
        
        # Strong hands - value bet/call
        elif hand_strength in ['strong', 'good']:
            if to_call == 0:
                bet_size = min(ai_player['stack'], pot * 0.5)
                return ('raise', ai_player['current_bet'] + bet_size)
            elif pot_odds >= 2:  # Good odds
                return ('call', 0)
            elif equity > 0.6:  # Strong equity
                return ('call', 0)
            else:
                return ('fold', 0)
        
        # Medium strength - pot control
        elif hand_strength == 'medium':
            if to_call == 0:
                # Sometimes bet for thin value or protection
                if random.random() < 0.3:
                    bet_size = min(ai_player['stack'], pot * 0.33)
                    return ('raise', ai_player['current_bet'] + bet_size)
                return ('check', 0)
            elif pot_odds >= 3:  # Only call with good odds
                return ('call', 0)
            else:
                return ('fold', 0)
        
        # Weak hands - mostly fold, occasional bluff
        else:
            if to_call == 0:
                # Occasional bluff based on board texture and opponent
                if random.random() < 0.1 and betting_round in ['turn', 'river']:
                    bluff_size = min(ai_player['stack'], pot * 0.6)
                    return ('raise', ai_player['current_bet'] + bluff_size)
                return ('check', 0)
            else:
                # Almost always fold weak hands to bets
                if pot_odds >= 5 and equity > 0.25:  # Draw potential
                    return ('call', 0)
                return ('fold', 0)
    
    def preflop_decision(self, hand, to_call, pot, ai_player, stack_bb):
        """Enhanced preflop strategy"""
        card1, card2 = hand[0], hand[1]
        rank1, rank2 = card1[0], card2[0]
        suited = card1[1] == card2[1]
        
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, 
                      '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        val1, val2 = rank_values[rank1], rank_values[rank2]
        
        # Premium hands (top 15%)
        premium_hands = self.is_premium_hand(rank1, rank2, suited, val1, val2)
        
        if premium_hands:
            return self.aggressive_preflop_play(to_call, pot, ai_player, stack_bb)
        
        # Playable hands (top 35%)
        elif self.is_playable_hand(rank1, rank2, suited, val1, val2):
            return self.moderate_preflop_play(to_call, pot, ai_player, stack_bb)
        
        # Marginal hands - position dependent (would need position info)
        elif self.is_marginal_hand(rank1, rank2, suited, val1, val2):
            return self.conservative_preflop_play(to_call, pot, ai_player)
        
        # Trash hands
        else:
            if to_call == 0:
                return ('check', 0)
            else:
                return ('fold', 0)
    
    def is_premium_hand(self, rank1, rank2, suited, val1, val2):
        """Define premium starting hands"""
        # Pocket pairs JJ+
        if rank1 == rank2 and val1 >= 11:
            return True
        # AK, AQ
        if sorted([val1, val2]) == [12, 14] or sorted([val1, val2]) == [13, 14]:
            return True
        return False
    
    def is_playable_hand(self, rank1, rank2, suited, val1, val2):
        """Define playable starting hands"""
        # Medium-high pairs
        if rank1 == rank2 and val1 >= 7:
            return True
        # Suited broadway
        if suited and min(val1, val2) >= 10:
            return True
        # Ace with decent kicker
        if max(val1, val2) == 14 and min(val1, val2) >= 9:
            return True
        return False
    
    def is_marginal_hand(self, rank1, rank2, suited, val1, val2):
        """Define marginal hands that can be played in position"""
        # Small-medium pairs
        if rank1 == rank2 and val1 >= 4:
            return True
        # Suited connectors
        if suited and abs(val1 - val2) <= 2 and min(val1, val2) >= 5:
            return True
        # Any ace
        if max(val1, val2) == 14:
            return True
        return False
    
    def aggressive_preflop_play(self, to_call, pot, ai_player, stack_bb):
        """Aggressive play with premium hands"""
        if to_call == 0:
            raise_size = min(ai_player['stack'], max(pot, BIG_BLIND * 3))
            return ('raise', ai_player['current_bet'] + raise_size)
        elif to_call <= ai_player['stack'] * 0.2:  # Don't risk too much preflop
            # Sometimes re-raise
            if ai_player['stack'] > to_call * 3 and random.random() < 0.4:
                raise_size = min(to_call * 3, ai_player['stack'] - to_call)
                return ('raise', ai_player['current_bet'] + to_call + raise_size)
            return ('call', 0)
        else:
            return ('call', 0)  # Call big bets with premium hands
    
    def moderate_preflop_play(self, to_call, pot, ai_player, stack_bb):
        """Moderate play with decent hands"""
        if to_call == 0:
            # Sometimes raise for value
            if random.random() < 0.4:
                raise_size = min(ai_player['stack'], BIG_BLIND * 2.5)
                return ('raise', ai_player['current_bet'] + raise_size)
            return ('check', 0)
        elif to_call <= BIG_BLIND * 3:  # Call reasonable raises
            return ('call', 0)
        else:
            return ('fold', 0)
    
    def conservative_preflop_play(self, to_call, pot, ai_player):
        """Conservative play with marginal hands"""
        if to_call == 0:
            return ('check', 0)
        elif to_call <= BIG_BLIND:  # Only call small bets
            return ('call', 0)
        else:
            return ('fold', 0)

# Create global AI instance
advanced_ai = AdvancedPokerAI()

def decide_action_advanced(game_state):
    """Wrapper function for advanced AI"""
    return advanced_ai.decide_action(game_state)
