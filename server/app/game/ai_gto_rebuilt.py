"""
GTO-Enhanced Poker AI - Rebuilt Version

This module combines Game Theory Optimal concepts with opponent modeling
to create a more sophisticated and adaptive poker AI.
"""

import random
import math
import json
import os
from .hand_eval_lib import evaluate_hand
from .config import BIG_BLIND, SMALL_BLIND
from .preflop_charts import PreflopCharts
from .postflop_strategy import PostflopStrategy

class GTOEnhancedAI:
    def __init__(self):
        # Initialize strategy components
        self.preflop_charts = PreflopCharts()
        self.postflop_strategy = PostflopStrategy()
        
        # Load heads-up charts
        self.sb_rfi_chart = self.load_sb_rfi_chart()
        
        # Opponent modeling
        self.opponent_model = {
            'hands_played': 0,
            'preflop_stats': {
                'vpip': 0.5,  # Voluntarily Put in Pot
                'pfr': 0.3,   # Pre-flop Raise
                'three_bet': 0.1,  # 3-bet frequency
                'fold_to_three_bet': 0.7
            },
            'postflop_stats': {
                'cbet_frequency': 0.7,  # Continuation bet frequency
                'fold_to_cbet': 0.5,    # Fold to c-bet
                'turn_aggression': 0.4,  # Turn aggression factor
                'river_aggression': 0.3, # River aggression factor
                'bluff_frequency': 0.2   # Overall bluff frequency
            },
            'recent_actions': [],  # Track recent betting patterns
            'showdown_hands': []   # Track revealed hands for range updates
        }
        
        # GTO parameters
        self.gto_parameters = {
            'minimum_defense_frequency': 0.67,  # Against standard bet sizes
            'value_bet_frequency': 0.65,        # How often to bet for value
            'bluff_frequency': 0.35,            # How often to bluff
            'check_raise_frequency': 0.15,      # Check-raise frequency
            'donk_bet_frequency': 0.05          # Donk bet frequency (out of position)
        }
    
    def load_sb_rfi_chart(self):
        """Load the small blind raise-first-in chart"""
        try:
            chart_path = os.path.join(os.path.dirname(__file__), 'poker_charts', 'headsup_SBRFI.json')
            with open(chart_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading SB RFI chart: {e}")
            return {}
    
    def hand_to_string(self, hand):
        """Convert hand format to chart format (e.g., ['2h', '3s'] -> '23o')"""
        if len(hand) != 2:
            return None
        
        # Extract ranks and suits
        rank1, suit1 = hand[0][0], hand[0][1]
        rank2, suit2 = hand[1][0], hand[1][1]
        
        # Convert rank characters
        rank_order = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, 
                     '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        
        if rank1 not in rank_order or rank2 not in rank_order:
            return None
        
        # Sort by rank (higher first)
        if rank_order[rank1] > rank_order[rank2]:
            high_rank, low_rank = rank1, rank2
            high_suit, low_suit = suit1, suit2
        else:
            high_rank, low_rank = rank2, rank1
            high_suit, low_suit = suit2, suit1
        
        # Handle pairs
        if high_rank == low_rank:
            return high_rank + low_rank
        
        # Handle suited/offsuit
        if high_suit == low_suit:
            return high_rank + low_rank + 's'
        else:
            return high_rank + low_rank + 'o'
    
    def sb_first_action(self, hand):
        """Get action from SB RFI chart"""
        hand_str = self.hand_to_string(hand)
        if not hand_str or hand_str not in self.sb_rfi_chart:
            return 'fold'
        
        chart_entry = self.sb_rfi_chart[hand_str]
        
        # Use probabilities to determine action
        rand = random.random()
        
        if rand < chart_entry['raise']:
            return 'raise'
        elif rand < chart_entry['raise'] + chart_entry['call']:
            return 'call'
        else:
            return 'fold'
    
    def decide_action(self, game_state):
        """
        Main decision function combining GTO principles with opponent modeling
        """
        ai_player = game_state['players'][1]
        hand = ai_player['hand']
        to_call = game_state.get('current_bet', 0) - ai_player['current_bet']
        pot = game_state['pot']
        betting_round = game_state['betting_round']
        
        # Determine position (in heads-up, button is always 'in position' postflop)
        dealer_pos = game_state.get('dealer_pos', 0)
        ai_position = 1  # AI is player 1
        
        if game_state['betting_round'] == 'preflop':
            position = 'button' if ai_position == dealer_pos else 'bb'
        else:
            position = 'ip' if ai_position == dealer_pos else 'oop'
        
        if betting_round == 'preflop':
            return self.preflop_decision(hand, to_call, pot, ai_player, position, game_state)
        else:
            # Simplified postflop for now
            if to_call == 0:
                return ('check', 0)
            elif to_call <= pot * 0.5:  # Good pot odds
                return ('call', 0)
            else:
                return ('fold', 0)
    
    def preflop_decision(self, hand, to_call, pot, ai_player, position, game_state):
        """
        Enhanced preflop decision making using charts
        """
        # If Small Blind and unopened pot, use SB RFI chart
        if position == 'button' and to_call == 0:  # SB is button in heads-up
            chart_action = self.sb_first_action(hand)
            return self.convert_action_to_game_format(chart_action, to_call, pot, ai_player, 'preflop')
        
        # For other situations, use basic logic for now
        if to_call == 0:
            return ('check', 0)
        elif to_call <= ai_player['stack'] * 0.1:  # Small bet
            return ('call', 0)
        else:
            return ('fold', 0)
    
    def convert_action_to_game_format(self, chart_action, to_call, pot, ai_player, street):
        """
        Convert strategy action to game format
        """
        if chart_action in ['fold']:
            return ('fold', 0)
        elif chart_action in ['check']:
            return ('check', 0) if to_call == 0 else ('fold', 0)
        elif chart_action in ['call']:
            return ('call', 0) if to_call > 0 else ('check', 0)
        elif chart_action in ['raise', '3bet', '4bet', 'bet']:
            if street == 'preflop':
                if to_call == 0:
                    # SB RFI: bet 2.3 BB rounded up
                    raise_size = math.ceil(BIG_BLIND * 2.3)
                else:
                    raise_size = to_call * 3  # 3-bet sizing
            else:
                raise_size = pot * 0.67  # Standard postflop bet
            
            raise_size = min(raise_size, ai_player['stack'])
            return ('raise', ai_player['current_bet'] + raise_size)
        else:
            return ('check', 0) if to_call == 0 else ('fold', 0)

# Create global GTO AI instance (defer to avoid import errors)
gto_ai = None

def decide_action_gto(game_state):
    """
    Wrapper function for GTO-enhanced AI
    """
    global gto_ai
    if gto_ai is None:
        gto_ai = GTOEnhancedAI()
    return gto_ai.decide_action(game_state)
