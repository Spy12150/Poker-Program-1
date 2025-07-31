"""
Bladework v2

My second version of my hard coded AI
This version includes calculation of opponent ranges, and using Monte Carlo to simulate runs.
It also tracks opponent behaviour through statistics like VPIP or PFR rate.
"""

import random
import math
import json
import os
from ..hand_eval_lib import evaluate_hand
from ..config import BIG_BLIND, SMALL_BLIND
from .preflop_charts import PreflopCharts
from .postflop_strategy import PostflopStrategy

class GTOEnhancedAI:
    def __init__(self):
        # Initialize strategy components
        self.preflop_charts = PreflopCharts()
        self.postflop_strategy = PostflopStrategy()
        
        # Load heads-up charts
        self.sb_rfi_chart = self.load_sb_rfi_chart()
        
        # GTO parameters remain, but opponent_model is now dynamic
        self.gto_parameters = {
            'minimum_defense_frequency': 0.67,
            'value_bet_frequency': 0.65,
            'bluff_frequency': 0.35,
            'check_raise_frequency': 0.15,
            'donk_bet_frequency': 0.05
        }

    def estimate_opponent_preflop_range(self, game_state):
        """
        Estimates the opponent's hand range based on their preflop actions.
        Returns a list of hand tuples, e.g., [(14, 13, True), (10, 10)].
        """
        action_history = game_state.get('action_history', [])
        preflop_actions = [a for a in action_history if a.get('round') == 'preflop']
        human_actions = [a for a in preflop_actions if a['player'] == 'Player 1']
        ai_actions = [a for a in preflop_actions if a['player'] == 'Player 2']

        opponent_range_tuples = []

        # Determine the pre-flop scenario
        ai_opened = any(a['action'] == 'raise' for a in ai_actions)
        human_opened = any(a['action'] == 'raise' for a in human_actions)

        if ai_opened:
            # AI opened, Human (in BB) responded
            human_action = human_actions[-1]['action'] if human_actions else 'fold'
            if human_action == 'call':
                opponent_range_tuples = self.preflop_charts.bb_defense_range['call']
            elif human_action == 'raise':  # 3-bet
                opponent_range_tuples = self.preflop_charts.bb_defense_range['3bet']
        elif human_opened:
            # Human opened (from SB), AI is defending
            # Human's range is the RFI chart
            for hand_str, actions in self.sb_rfi_chart.items():
                # We'll assume if they can raise, it's in their opening range
                if actions.get('raise', 0) > 0:
                    opponent_range_tuples.append(self.hand_str_to_tuple(hand_str))
        else: # Limped pot or other scenario
            # Fallback to a wide, passive range (less likely to contain premium hands)
            opponent_range_tuples = self.preflop_charts.bb_defense_range['call']


        # If for some reason the range is empty, use a default wide range
        if not opponent_range_tuples:
            opponent_range_tuples = self.preflop_charts.button_opening_range['premium'] + \
                                    self.preflop_charts.button_opening_range['strong'] + \
                                    self.preflop_charts.button_opening_range['playable']

        return self.postflop_strategy.convert_range_tuples_to_hands(opponent_range_tuples)
    
    def hand_str_to_tuple(self, hand_str):
        """Converts a chart hand string like 'AKs' or 'TT' to a tuple like (14, 13, True) or (10, 10)."""
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        
        if len(hand_str) == 2:  # Pair
            rank = rank_values[hand_str[0]]
            return (rank, rank)
        
        high_rank_char = hand_str[0]
        low_rank_char = hand_str[1]
        
        high_rank = rank_values[high_rank_char]
        low_rank = rank_values[low_rank_char]
        
        if len(hand_str) > 2 and hand_str[2] == 's':
            return (high_rank, low_rank, True)
        else:  # 'o' or empty for pairs
            return (high_rank, low_rank, False)

    
    def load_sb_rfi_chart(self):
        """Load the small blind raise-first-in chart"""
        try:
            chart_path = os.path.join(os.path.dirname(__file__), 'poker_charts', 'headsup_SBRFI.json')
            print(f"DEBUG: Loading SB RFI chart from: {chart_path}")
            with open(chart_path, 'r') as f:
                chart = json.load(f)
            print(f"DEBUG: SB RFI chart loaded successfully, contains {len(chart)} hands")
            return chart
        except Exception as e:
            print(f"ERROR: Failed to load SB RFI chart: {e}")
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
        print(f"DEBUG: sb_first_action called with hand: {hand}")
        hand_str = self.hand_to_string(hand)
        print(f"DEBUG: Hand converted to string: {hand_str}")
        
        if not hand_str:
            print("DEBUG: hand_str is None, returning fold")
            return 'fold'
            
        if hand_str not in self.sb_rfi_chart:
            print(f"DEBUG: Hand {hand_str} not found in SB RFI chart, returning fold")
            return 'fold'
        
        chart_entry = self.sb_rfi_chart[hand_str]
        print(f"DEBUG: Chart entry for {hand_str}: {chart_entry}")
        
        # Use probabilities to determine action
        rand = random.random()
        print(f"DEBUG: Random number: {rand}")
        
        if rand < chart_entry['raise']:
            print("DEBUG: Action chosen: raise")
            return 'raise'
        elif rand < chart_entry['raise'] + chart_entry['call']:
            print("DEBUG: Action chosen: call")
            return 'call'
        else:
            print("DEBUG: Action chosen: fold")
            return 'fold'
    
    def decide_action(self, game_state):
        """
        Main decision function combining GTO principles with opponent modeling
        """
        print("=== AI DECISION FUNCTION CALLED ===")
        
        ai_player = game_state['players'][1]
        human_player = game_state['players'][0]
        hand = ai_player['hand']
        community = game_state['community']
        to_call = game_state.get('current_bet', 0) - ai_player['current_bet']
        pot = game_state['pot']
        betting_round = game_state['betting_round']
        
        # Update opponent model at the start of our turn if it's a new hand
        if not game_state['action_history']:
             self.update_opponent_model(game_state)

        # Calculate key metrics
        effective_stack = min(ai_player['stack'], human_player['stack'])
        stack_bb = effective_stack // BIG_BLIND
        
        # Determine position
        position = self.get_position(game_state)
        
        if betting_round == 'preflop':
            result = self.preflop_decision(hand, to_call, pot, ai_player, stack_bb, position, game_state)
            return result
        else:
            villain_range = self.estimate_opponent_preflop_range(game_state)
            result = self.postflop_decision(hand, community, to_call, pot, ai_player, stack_bb, position, betting_round, game_state, villain_range)
            return result
    
    def get_position(self, game_state):
        """Determine AI's position relative to opponent"""
        dealer_pos = game_state.get('dealer_pos', 0)
        ai_idx = 1
        
        if game_state['betting_round'] == 'preflop':
            return 'button' if ai_idx == dealer_pos else 'bb'
        else:
            return 'ip' if ai_idx == dealer_pos else 'oop'

    def preflop_decision(self, hand, to_call, pot, ai_player, stack_bb, position, game_state):
        action_history = game_state.get('action_history', [])
        preflop_actions = [a for a in action_history if a.get('round') == 'preflop']
        
        # Scenario 1: AI is SB and can Raise-First-In
        is_rfi_situation = position == 'button' and not any(a.get('action') == 'raise' for a in preflop_actions)
        if is_rfi_situation:
            chart_action = self.sb_first_action(hand)
        
        # Scenario 2: AI is BB and is facing a limp (can check or raise)
        elif position == 'bb' and to_call == 0:
             chart_action = self.preflop_charts.get_preflop_action(
                hand, position, 'limp', 0, stack_bb
            )
        
        # Scenario 3: AI is facing a raise
        else:
            raises = sum(1 for a in preflop_actions if a.get('action') == 'raise')
            action_to_hero = 'none'
            if to_call > 0: # Facing a bet
                if raises == 1:
                    action_to_hero = 'raise'
                elif raises == 2:
                    action_to_hero = '3bet'
                else:
                    action_to_hero = '4bet'
            
            raise_size_bb = to_call / BIG_BLIND if BIG_BLIND > 0 else 0
            chart_action = self.preflop_charts.get_preflop_action(
                hand, position, action_to_hero, raise_size_bb, stack_bb
            )

        adjusted_action = self.adjust_for_opponent_preflop(chart_action, hand, to_call, pot, ai_player, position, game_state)
        return self.convert_action_to_game_format(adjusted_action, to_call, pot, ai_player, 'preflop', game_state)

    def adjust_for_opponent_preflop(self, chart_action, hand, to_call, pot, ai_player, position, game_state):
        """
        Adjust preflop strategy based on opponent tendencies from game_state.
        """
        model = game_state.get('opponent_model')
        if not model or model['preflop_stats']['vpip_opportunities'] < 5: # Need a minimum sample size
            return chart_action

        stats = model['preflop_stats']
        opponent_vpip = stats['vpip'] / stats['vpip_opportunities']
        
        if opponent_vpip < 0.3 and chart_action == 'call':
            hand_strength = self.get_simple_hand_strength(hand)
            if hand_strength >= 0.85:
                return '3bet'
        
        elif opponent_vpip > 0.7 and chart_action == '3bet':
            hand_strength = self.get_simple_hand_strength(hand)
            if hand_strength < 0.85: # Don't turn strong value into a call
                return 'call'

        return chart_action
    
    def get_simple_hand_strength(self, hand):
        """
        Simple preflop hand strength evaluation (0-1 scale)
        """
        rank1, suit1 = hand[0][0], hand[0][1]
        rank2, suit2 = hand[1][0], hand[1][1]
        
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, 
                      '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        
        val1 = rank_values.get(rank1, 2)
        val2 = rank_values.get(rank2, 2)
        
        high_val = max(val1, val2)
        is_pair = val1 == val2
        
        if is_pair:
            return 0.9 if high_val >= 10 else (0.7 if high_val >= 7 else 0.5)
        
        is_suited = suit1 == suit2
        if is_suited:
            if high_val == 14 and min(val1, val2) >= 10: return 0.85
            if high_val >= 13 and min(val1, val2) >= 10: return 0.75
            return 0.5
        else: # Offsuit
            if high_val == 14 and min(val1, val2) >= 12: return 0.8
            if high_val >= 13 and min(val1, val2) >= 11: return 0.6
            return 0.3

    def postflop_decision(self, hand, community, to_call, pot, ai_player, stack_bb, position, street, game_state, villain_range=None):
        hand_strength = self.calculate_hand_strength_normalized(hand, community)
        equity = self.postflop_strategy.calculate_hand_equity(hand, community, villain_range=villain_range, num_simulations=300)
        pot_odds = self.calculate_pot_odds(to_call, pot)
        
        if to_call == 0:
            return self.decide_check_or_bet(hand_strength, equity, pot, ai_player, position, street, game_state)
        else:
            return self.decide_call_raise_fold(hand_strength, equity, pot_odds, to_call, pot, ai_player, position, street, game_state)

    def decide_check_or_bet(self, hand_strength, equity, pot, ai_player, position, street, game_state):
        if hand_strength >= 0.75: # Value bet
            bet_size = self.calculate_value_bet_size(hand_strength, pot, ai_player['stack'], street)
            return ('bet', bet_size)
        
        if equity > 0.6 and street != 'river': # Semi-bluff with strong draws
            bet_size = round(pot * 0.7)
            return ('bet', min(bet_size, ai_player['stack']))
            
        return ('check', 0)

    def decide_call_raise_fold(self, hand_strength, equity, pot_odds, to_call, pot, ai_player, position, street, game_state):
        required_equity = to_call / (pot + to_call)

        if hand_strength >= 0.85: # Raise for value with the nuts
             raise_size = self.calculate_value_raise_size(hand_strength, to_call, pot, ai_player['stack'], street)
             return ('raise', ai_player['current_bet'] + to_call + raise_size)

        if equity > required_equity:
            # Consider raising with strong hands/draws, especially in position
            if equity > 0.7 and position == 'ip':
                if random.random() < 0.4: # Mix up strategy
                    raise_size = self.calculate_value_raise_size(hand_strength, to_call, pot, ai_player['stack'], street)
                    return ('raise', ai_player['current_bet'] + to_call + raise_size)
            return ('call', 0)
        
        return ('fold', 0)

    def calculate_value_bet_size(self, hand_strength, pot, stack, street):
        if street == 'river':
            return min(stack, round(pot * 0.75))
        return min(stack, round(pot * 0.67))

    def calculate_value_raise_size(self, hand_strength, bet_to_call, pot, stack, street):
        return min(stack - bet_to_call, round((pot + bet_to_call) * 0.8))

    def calculate_hand_strength_normalized(self, hand, community):
        if not community: return self.get_simple_hand_strength(hand)
        try:
            score, _ = evaluate_hand(hand, community)
            if score <= 10: return 0.99
            elif score <= 166: return 0.95
            elif score <= 322: return 0.90
            elif score <= 1599: return 0.85
            elif score <= 1609: return 0.80
            elif score <= 2467: return 0.65
            elif score <= 3325: return 0.50
            elif score <= 6185: return 0.35
            else: return 0.15
        except: return 0.2

    def calculate_pot_odds(self, bet_to_call, pot_size):
        if bet_to_call <= 0: return float('inf')
        return pot_size / bet_to_call

    def update_opponent_model(self, game_state):
        """
        Update opponent model based on the hand history of the *previous* hand.
        Note: This is a simplified implementation. It processes the entire preflop history
        at the start of a new hand, which is not ideal but works for this structure.
        """
        model = game_state.get('opponent_model')
        history = game_state.get('action_history', [])
        
        if not model or not history: return

        human_player_name = "Player 1"
        preflop_actions = [a for a in history if a.get('round') == 'preflop']
        human_actions = [a for a in preflop_actions if a['player'] == human_player_name]

        if not human_actions: return

        model['preflop_stats']['vpip_opportunities'] += 1
        if any(a['action'] in ['call', 'raise'] for a in human_actions):
            model['preflop_stats']['vpip'] += 1
        
        model['preflop_stats']['pfr_opportunities'] += 1
        if any(a['action'] == 'raise' for a in human_actions):
            model['preflop_stats']['pfr'] += 1

    def convert_action_to_game_format(self, chart_action, to_call, pot, ai_player, street, game_state):
        if chart_action == 'fold':
            return ('fold', 0)
        if chart_action == 'check':
            return ('check', 0) if to_call == 0 else ('fold', 0)
        if chart_action == 'call':
            return ('call', 0) if to_call > 0 else ('check', 0)
        
        if chart_action in ['raise', 'bet', '3bet', '4bet']:
            if street == 'preflop':
                preflop_actions = [a for a in game_state.get('action_history', []) if a.get('round') == 'preflop']
                is_rfi = not any(a.get('action') == 'raise' for a in preflop_actions)

                if is_rfi:
                    # RFI: raise to 2.5x BB
                    total_bet_amount = BIG_BLIND * 2.5
                else:
                    # 3-bet or 4-bet+: standard sizing
                    # Raise is 3x the previous bet/raise on top
                    total_bet_amount = game_state['current_bet'] + (game_state['last_bet_amount'] * 3)
            
            else: # Postflop
                # Bet 2/3 pot
                total_bet_amount = pot * 0.67

            # Ensure the amount is an integer and doesn't exceed the player's stack
            final_amount = min(ai_player['stack'] + ai_player['current_bet'], round(total_bet_amount))
            return ('raise', final_amount)

        return ('check', 0) if to_call == 0 else ('fold', 0)

# Global instance
gto_ai = None

def decide_action_bladeworkv2(game_state):
    global gto_ai
    if gto_ai is None:
        gto_ai = GTOEnhancedAI()
    return gto_ai.decide_action(game_state)
