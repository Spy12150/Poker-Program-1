"""
Bladework v2

My second version of my hard coded AI
This version includes calculation of opponent ranges, and using Monte Carlo to simulate runs.
It also tracks opponent behaviour through statistics like VPIP or PFR rate.
"""

import random
import math
from ..hand_eval_lib import evaluate_hand
from ..config import BIG_BLIND, SMALL_BLIND
from .preflop_charts import PreflopCharts
from .postflop_strategy import PostflopStrategy
from .tier_config import TIERS

class GTOEnhancedAI:
    def __init__(self):
        # Initialize strategy components
        self.preflop_charts = PreflopCharts()
        self.postflop_strategy = PostflopStrategy()
        
        # GTO parameters remain, but opponent_model is now dynamic
        self.gto_parameters = {
            'minimum_defense_frequency': 0.67,
            'value_bet_frequency': 0.65,
            'bluff_frequency': 0.35,
            'check_raise_frequency': 0.15,
            'donk_bet_frequency': 0.05
        }

        # Global opponent model (persists across hands)
        self.opponent_model = {
            'hands_played': 0,
            'preflop_stats': {
                'vpip': 0,
                'vpip_opportunities': 0,
                'pfr': 0,
                'pfr_opportunities': 0
            },
            'postflop_stats': {
                'cbet_frequency': 0,
                'cbet_opportunities': 0,
                'fold_to_cbet': 0,
                'fold_to_cbet_opportunities': 0
            },
            'recent_actions': [],
            'showdown_hands': []
        }

    def estimate_opponent_preflop_range(self, game_state):
        """
        Estimates the opponent's hand range based on their preflop actions using tier system.
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
        raises = sum(1 for a in preflop_actions if a.get('action') == 'raise')

        if ai_opened:
            # AI opened, Human (in BB) responded
            human_action = human_actions[-1]['action'] if human_actions else 'fold'
            if human_action == 'call':
                # Human called our open - estimate BB calling range (tiers 0-6)
                for tier_idx in range(7):  # tiers 0-6
                    if tier_idx < len(TIERS):
                        opponent_range_tuples.extend(TIERS[tier_idx])
            elif human_action == 'raise':  # 3-bet
                if raises == 2:  # Standard 3-bet
                    # Human 3-bet - estimate 3-betting range (tiers 0-2)
                    for tier_idx in range(3):  # tiers 0-2
                        if tier_idx < len(TIERS):
                            opponent_range_tuples.extend(TIERS[tier_idx])
                else:  # 4-bet or higher
                    # Very tight range (tier 0 only)
                    if len(TIERS) > 0:
                        opponent_range_tuples.extend(TIERS[0])
        elif human_opened:
            # Human opened (from SB), estimate SB RFI range (tiers 0-8)
            for tier_idx in range(9):  # tiers 0-8  
                if tier_idx < len(TIERS):
                    opponent_range_tuples.extend(TIERS[tier_idx])
        else: 
            # Limped pot - estimate wide passive range (tiers 0-7)
            for tier_idx in range(8):  # tiers 0-7
                if tier_idx < len(TIERS):
                    opponent_range_tuples.extend(TIERS[tier_idx])

        # If for some reason the range is empty, use a default medium range
        if not opponent_range_tuples:
            for tier_idx in range(6):  # tiers 0-5 as fallback
                if tier_idx < len(TIERS):
                    opponent_range_tuples.extend(TIERS[tier_idx])

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
        
        # Update opponent model each decision
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
        """
        Comprehensive preflop decision using the tier-based preflop charts system
        """
        print(f"DEBUG: Preflop decision - Hand: {hand}, Position: {position}, To call: {to_call}")
        
        action_history = game_state.get('action_history', [])
        preflop_actions = [a for a in action_history if a.get('round') == 'preflop']
        raises = sum(1 for a in preflop_actions if a.get('action') == 'raise')
        
        # Extract bet history for proper sizing analysis
        bet_history = self._extract_bet_history(preflop_actions)
        print(f"DEBUG: Bet history: {bet_history}, Raises: {raises}")
        
        # Convert amounts to big blinds
        raise_size_bb = to_call / BIG_BLIND if BIG_BLIND > 0 else 0
        pot_bb = pot / BIG_BLIND if BIG_BLIND > 0 else 0
        
        # Determine the action facing the AI
        if position == 'button' and raises == 0:
            action_to_hero = 'none'  # SB first action
        elif position == 'bb' and to_call == 0 and raises == 0:
            action_to_hero = 'limp'  # SB limped
        elif to_call > 0:
            action_to_hero = 'raise'  # Facing a raise (could be 1st raise, 3-bet, 4-bet, etc.)
        else:
            action_to_hero = 'none'  # Fallback
        
        print(f"DEBUG: Action to hero: {action_to_hero}, Raise size: {raise_size_bb}bb")
        
        # Get chart-based decision using comprehensive system
        try:
            chart_action = self.preflop_charts.get_preflop_action(
                hand=hand,
                position=position,
                action_to_hero=action_to_hero,
                raise_size_bb=raise_size_bb,
                stack_bb=stack_bb,
                pot_bb=pot_bb,
                num_raises=raises,
                bet_history=bet_history
            )
            print(f"DEBUG: Chart action: {chart_action}")
        except Exception as e:
            print(f"ERROR: Preflop charts failed: {e}")
            # Fallback to conservative play
            tier = self.preflop_charts.get_hand_tier(hand)
            if tier <= 1:
                chart_action = 'call' if to_call > 0 else 'raise'
            else:
                chart_action = 'fold'
        
        # Apply opponent adjustments
        adjusted_action = self.adjust_for_opponent_preflop(chart_action, hand, to_call, pot, ai_player, position, game_state)
        print(f"DEBUG: Adjusted action: {adjusted_action}")
        
        # Convert to game format
        result = self.convert_action_to_game_format(adjusted_action, to_call, pot, ai_player, 'preflop', game_state)
        print(f"DEBUG: Final preflop result: {result}")
        return result
    
    def _extract_bet_history(self, preflop_actions):
        """
        Extract bet sizes from preflop action history for proper bet sizing analysis
        Returns list of bet sizes in big blinds: [original_raise, 3bet, 4bet, ...]
        """
        bet_history = []
        
        for action in preflop_actions:
            if action.get('action') == 'raise':
                # Extract bet amount from action
                amount = action.get('amount', 0)
                if amount > 0:
                    amount_bb = amount / BIG_BLIND if BIG_BLIND > 0 else 0
                    bet_history.append(amount_bb)
                elif action.get('raise_to'):
                    # Some action formats use 'raise_to'
                    amount_bb = action['raise_to'] / BIG_BLIND if BIG_BLIND > 0 else 0
                    bet_history.append(amount_bb)
                else:
                    # Fallback estimation based on position in sequence
                    estimated_amount = 3.0 * (2 ** len(bet_history))  # 3bb, 6bb, 12bb, 24bb...
                    bet_history.append(estimated_amount)
        
        return bet_history

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
        board_texture = self.analyze_board_texture_advanced(game_state.get('community', []))

        # Value betting
        if hand_strength >= 0.75:
            if board_texture.get('dry'):
                bet_size = min(ai_player['stack'], round(pot * 0.33))
            else:
                bet_size = self.calculate_value_bet_size(hand_strength, pot, ai_player['stack'], street)
            return ('bet', bet_size)

        # Semi-bluffing with strong equity hands/draws
        if equity > 0.6 and street != 'river':
            sizing = 0.5 if board_texture.get('dry') else 0.7
            bet_size = round(pot * sizing)
            return ('bet', min(bet_size, ai_player['stack']))

        return ('check', 0)

    def decide_call_raise_fold(self, hand_strength, equity, pot_odds, to_call, pot, ai_player, position, street, game_state):
        required_equity = to_call / (pot + to_call)
        bet_size_ratio = to_call / pot if pot > 0 else 0
        
        # Identify strong draws early (used throughout function)
        is_strong_draw = equity >= 0.32 and street != 'river'  # Strong draws get special treatment
        
        # CRITICAL FIX: Add hand strength filters for big bets
        min_hand_strength_thresholds = {
            # Bet size ratio -> minimum hand strength to call
            0.0:  0.10,   # Small bets: can call with weak hands
            0.33: 0.15,   # 1/3 pot: need some strength  
            0.5:  0.20,   # 1/2 pot: need decent strength (pairs OK)
            0.67: 0.30,   # 2/3 pot: need good strength
            1.0:  0.45,   # Pot bet: need strong hand
            1.5:  0.65,   # 1.5x pot: need very strong hand
            2.0:  0.80,   # 2x pot: need nuts/near-nuts
        }
        
        # Find the appropriate threshold based on bet size
        min_strength = 0.10
        for threshold_ratio in sorted(min_hand_strength_thresholds.keys()):
            if bet_size_ratio >= threshold_ratio:
                min_strength = min_hand_strength_thresholds[threshold_ratio]
        
        # CRITICAL CHECK: Don't call big bets with weak hands (BUT allow strong draws)
        if hand_strength < min_strength and not is_strong_draw:
            print(f"DEBUG: Folding weak hand (strength {hand_strength:.3f} < required {min_strength:.3f}) vs {bet_size_ratio:.1f}x pot bet")
            return ('fold', 0)
        elif is_strong_draw and hand_strength < min_strength:
            print(f"DEBUG: Allowing draw (strength {hand_strength:.3f}, equity {equity:.3f}) vs {bet_size_ratio:.1f}x pot bet")

        # Adjust required equity based on bet size (bigger bets need higher equity)
        bet_size_adjustment = min(0.15, bet_size_ratio * 0.05)  # Up to 15% increase
        
        # Be more lenient with equity requirements for strong draws (implied odds)
        if is_strong_draw:
            bet_size_adjustment *= 0.5  # Reduce adjustment for draws
            
        adjusted_required_equity = required_equity + bet_size_adjustment

        if hand_strength >= 0.85: # Raise for value with the nuts
             raise_size = self.calculate_value_raise_size(hand_strength, to_call, pot, ai_player['stack'], street)
             return ('raise', ai_player['current_bet'] + to_call + raise_size)

        if equity > adjusted_required_equity:
            # Consider raising with strong hands/draws, especially in position
            should_raise = False
            
            # Raise with very strong made hands
            if equity > 0.7 and position == 'ip' and hand_strength > 0.6:
                should_raise = random.random() < 0.4
            
            # Also raise with monster draws (combo draws, strong flush draws)
            elif equity >= 0.42 and is_strong_draw and position == 'ip' and street != 'river':
                should_raise = random.random() < 0.3  # Semi-bluff raise with strong draws
                print(f"DEBUG: Considering semi-bluff raise with draw (equity {equity:.3f})")
            
            if should_raise:
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
            # More conservative hand strength scaling
            if score <= 10: return 0.99      # Royal flush, straight flush
            elif score <= 166: return 0.94   # Four of a kind  
            elif score <= 322: return 0.88   # Full house
            elif score <= 1599: return 0.80  # Flush
            elif score <= 1609: return 0.72  # Straight
            elif score <= 2467: return 0.55  # Three of a kind
            elif score <= 3325: return 0.40  # Two pair
            elif score <= 6185: return 0.25  # One pair
            else: return 0.10                # High card (was 0.15, now more realistic)
        except: 
            # More conservative fallback for errors
            return 0.10

    def calculate_pot_odds(self, bet_to_call, pot_size):
        if bet_to_call <= 0: return float('inf')
        return pot_size / bet_to_call

    # ----- Advanced board texture analysis (imported from GTO Enhanced AI) -----
    def analyze_board_texture_advanced(self, community):
        """Return simple texture flags for sizing decisions."""
        if len(community) < 3:
            return {'type': 'preflop'}

        ranks = [card[0] for card in community]
        suits = [card[1] for card in community]

        suit_counts = {}
        for s in suits:
            suit_counts[s] = suit_counts.get(s, 0) + 1
        max_suit = max(suit_counts.values())

        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
                       'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        values = sorted([rank_values[r] for r in ranks])

        straight_draw = False
        if len(set(values)) >= 3:
            for i in range(len(values) - 2):
                if values[i+2] - values[i] <= 4:
                    straight_draw = True
                    break

        paired = len(set(ranks)) < len(ranks)

        return {
            'dry': max_suit <= 2 and not straight_draw and not paired,
            'wet': max_suit >= 3 or straight_draw,
            'paired': paired,
            'flush_draw': max_suit >= 3,
            'straight_draw': straight_draw
        }

    def update_opponent_model(self, game_state):
        """
        Lightweight opponent model tracking across hands. Only a few basic stats are
        collected for now but this can be extended later.
        """
        action_history = game_state.get('action_history', [])
        if not action_history:
            return

        # Increment hands played only when a new hand starts. We infer this from a
        # preflop 'deal' action if your engine emits one, otherwise this will just
        # count every decision which is harmless.
        self.opponent_model['hands_played'] += 1

        last_action = action_history[-1]
        if len(self.opponent_model['recent_actions']) >= 10:
            self.opponent_model['recent_actions'].pop(0)
        self.opponent_model['recent_actions'].append(last_action)

        # Simple VPIP / PFR tracking for Player 1 (human)
        if last_action.get('round') == 'preflop' and last_action.get('player') == 'Player 1':
            self.opponent_model['preflop_stats']['vpip_opportunities'] += 1
            if last_action.get('action') in ['call', 'raise']:
                self.opponent_model['preflop_stats']['vpip'] += 1
            if last_action.get('action') == 'raise':
                self.opponent_model['preflop_stats']['pfr'] += 1
                self.opponent_model['preflop_stats']['pfr_opportunities'] += 1

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

                effective_stack = min(ai_player['stack'], game_state['players'][0]['stack'])
                stack_bb = effective_stack / BIG_BLIND if BIG_BLIND else 100

                if is_rfi:
                    # Stack-aware open sizing
                    if stack_bb < 20:
                        total_bet_amount = BIG_BLIND * 2.2
                    elif stack_bb < 40:
                        total_bet_amount = BIG_BLIND * 2.3
                    else:
                        total_bet_amount = BIG_BLIND * 2.5
                else:
                    # Facing a raise – 3-bet / 4-bet sizing at 4.5x opponent's last bet
                    if stack_bb < 25:
                        total_bet_amount = ai_player['current_bet'] + effective_stack  # shove
                    else:
                        # Use 4.5x multiplier for all stack depths
                        multiplier = 4.5
                        total_bet_amount = game_state['current_bet'] + (game_state['last_bet_amount'] * multiplier)
            
            else:  # Postflop
                board_texture = self.analyze_board_texture_advanced(game_state.get('community', []))
                total_bet_amount = pot * (0.33 if board_texture.get('dry') else 0.67)

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
