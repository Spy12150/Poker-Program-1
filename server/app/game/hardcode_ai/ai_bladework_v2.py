"""
Bladework v2

My second version of my hard coded AI
This version includes calculation of opponent ranges, and using Monte Carlo to simulate runs.
It also tracks opponent behaviour through statistics like VPIP or PFR rate (per session)

Good enough to beat my dad, myself, and most novice/intermediate players
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
        
        # Advanced board analysis
        board_analysis = self.analyze_board_comprehensive(community, street)
        
        # Create/update multi-street plan
        betting_plan = self.create_multi_street_plan(hand, community, street, position, stack_bb, hand_strength)
        
        # River gets specialized treatment
        if street == 'river':
            return self.river_decision_logic(hand, community, to_call, pot, ai_player, position, game_state, board_analysis)
        
        if to_call == 0:
            return self.decide_check_or_bet_advanced(hand_strength, equity, pot, ai_player, position, street, game_state, board_analysis, betting_plan)
        else:
            return self.decide_call_raise_fold_advanced(hand_strength, equity, pot_odds, to_call, pot, ai_player, position, street, game_state, board_analysis)

    def decide_check_or_bet_advanced(self, hand_strength, equity, pot, ai_player, position, street, game_state, board_analysis, betting_plan):
        """Advanced betting decision with dynamic sizing and sophisticated logic."""
        stack = ai_player['stack']
        
        # Protection betting logic
        if self.needs_protection(hand_strength, board_analysis, street):
            protection_size = self.calculate_protection_bet_size(hand_strength, pot, stack, board_analysis)
            print(f"DEBUG: Protection bet - hand_strength: {hand_strength:.3f}, size: {protection_size}")
            return ('raise', ai_player['current_bet'] + protection_size)
        
        # Strong value betting
        if hand_strength >= 0.75:
            bet_size = self.calculate_optimal_bet_size(hand_strength, board_analysis, position, street, pot, stack, 'value')
            print(f"DEBUG: Strong value bet - hand_strength: {hand_strength:.3f}, size: {bet_size}")
            return ('raise', ai_player['current_bet'] + bet_size)

        # Medium strength - mixed strategy
        elif hand_strength >= 0.55:
            # Bet more often in position and on favorable boards
            bet_frequency = 0.75 if position == 'ip' else 0.60
            
            # Adjust for board texture
            if board_analysis.get('static', False):
                bet_frequency += 0.10
            elif board_analysis.get('draw_heavy', False):
                bet_frequency += 0.15  # Bet more on draw-heavy boards
                
            if random.random() < bet_frequency:
                bet_size = self.calculate_optimal_bet_size(hand_strength, board_analysis, position, street, pot, stack, 'thin_value')
                print(f"DEBUG: Thin value bet - hand_strength: {hand_strength:.3f}, size: {bet_size}")
                return ('raise', ai_player['current_bet'] + bet_size)
            else:
                print(f"DEBUG: Check behind - hand_strength: {hand_strength:.3f} (pot control)")
                return ('check', 0)

        # Semi-bluffing with draws
        elif equity >= 0.30 and street != 'river':
            if self.should_semi_bluff(hand_strength, equity, board_analysis, position, street):
                bet_size = self.calculate_optimal_bet_size(hand_strength, board_analysis, position, street, pot, stack, 'semi_bluff')
                print(f"DEBUG: Semi-bluff - equity: {equity:.3f}, size: {bet_size}")
                return ('raise', ai_player['current_bet'] + bet_size)
            else:
                return ('check', 0)

        # Pure bluffs
        elif hand_strength <= 0.25 and self.should_bluff_advanced(hand_strength, board_analysis, position, street, pot, stack):
            bet_size = self.calculate_optimal_bet_size(hand_strength, board_analysis, position, street, pot, stack, 'bluff')
            print(f"DEBUG: Pure bluff - hand_strength: {hand_strength:.3f}, size: {bet_size}")
            return ('raise', ai_player['current_bet'] + bet_size)

        # Default to check
        print(f"DEBUG: Check - hand_strength: {hand_strength:.3f}, equity: {equity:.3f}")
        return ('check', 0)

    def decide_call_raise_fold_advanced(self, hand_strength, equity, pot_odds, to_call, pot, ai_player, position, street, game_state, board_analysis):
        """Advanced call/raise/fold decision with sophisticated logic."""
        required_equity = to_call / (pot + to_call) if (pot + to_call) > 0 else 0
        bet_size_ratio = to_call / pot if pot > 0 else 0
        stack = ai_player['stack']
        
        # Enhanced hand classification
        is_strong_draw = equity >= 0.32 and street != 'river'
        is_made_hand = hand_strength >= 0.35
        is_premium = hand_strength >= 0.85
        
        # Dynamic minimum strength thresholds based on board texture
        base_thresholds = {
            0.0:  0.10,   0.33: 0.15,   0.5:  0.20,   0.67: 0.30,
            1.0:  0.45,   1.5:  0.65,   2.0:  0.80,
        }
        
        # Adjust thresholds for board texture
        min_strength = 0.10
        for threshold_ratio in sorted(base_thresholds.keys()):
            if bet_size_ratio >= threshold_ratio:
                min_strength = base_thresholds[threshold_ratio]
        
        # Board texture adjustments
        if board_analysis.get('draw_heavy', False):
            min_strength -= 0.05  # Can call lighter on draw-heavy boards
        if board_analysis.get('action_cards'):
            min_strength += 0.05  # Need stronger hands on action cards
            
        # Premium hands - always consider raising
        if is_premium:
            raise_size = self.calculate_optimal_raise_size(hand_strength, to_call, pot, stack, street, board_analysis, 'value')
            print(f"DEBUG: Premium value raise - hand_strength: {hand_strength:.3f}, raise_size: {raise_size}")
            return ('raise', ai_player['current_bet'] + to_call + raise_size)

        # Strong hands - mixed strategy
        elif hand_strength >= 0.65:
            # Sometimes raise, sometimes call based on position and board
            raise_frequency = 0.50 if position == 'ip' else 0.35
            
            # Adjust for board texture
            if board_analysis.get('static', False):
                raise_frequency -= 0.15  # Raise less on static boards
            elif board_analysis.get('draw_heavy', False):
                raise_frequency += 0.15  # Raise more for protection
                
            if random.random() < raise_frequency:
                raise_size = self.calculate_optimal_raise_size(hand_strength, to_call, pot, stack, street, board_analysis, 'value')
                print(f"DEBUG: Strong value raise - hand_strength: {hand_strength:.3f}, raise_size: {raise_size}")
                return ('raise', ai_player['current_bet'] + to_call + raise_size)

        # Check minimum strength requirements
        if hand_strength < min_strength and not is_strong_draw:
            print(f"DEBUG: Folding weak hand - strength: {hand_strength:.3f} < required: {min_strength:.3f}")
            return ('fold', 0)

        # Equity-based decisions
        adjusted_required_equity = required_equity
        
        # Adjust for implied odds with draws
        if is_strong_draw:
            adjusted_required_equity *= 0.85  # Account for implied odds
            
        # Adjust for position
        if position == 'ip':
            adjusted_required_equity *= 0.95  # Slight discount in position
            
        # Semi-bluff raising with strong draws
        if is_strong_draw and position == 'ip' and street != 'river':
            semi_bluff_frequency = 0.25 if equity >= 0.40 else 0.15
            
            if random.random() < semi_bluff_frequency:
                raise_size = self.calculate_optimal_raise_size(hand_strength, to_call, pot, stack, street, board_analysis, 'semi_bluff')
                print(f"DEBUG: Semi-bluff raise - equity: {equity:.3f}, raise_size: {raise_size}")
                return ('raise', ai_player['current_bet'] + to_call + raise_size)

        # Final equity check
        if equity >= adjusted_required_equity:
            print(f"DEBUG: Calling - equity: {equity:.3f} >= required: {adjusted_required_equity:.3f}")
            return ('call', 0)
        else:
            print(f"DEBUG: Folding - equity: {equity:.3f} < required: {adjusted_required_equity:.3f}")
            return ('fold', 0)

    # ----- Advanced bet sizing and strategy methods -----
    def calculate_optimal_bet_size(self, hand_strength, board_analysis, position, street, pot, stack, bet_type):
        """Calculate optimal bet size based on multiple factors."""
        base_size = pot * 0.67  # Starting point
        
        # Adjust based on bet type
        if bet_type == 'value':
            if hand_strength >= 0.90:  # Nuts
                if street == 'turn':
                    # Turn nuts get more variety: 75%, 100%, or 125% pot
                    size_options = [0.75, 1.0, 1.25] if board_analysis.get('static', False) else [0.75, 0.90, 1.10]
                    multiplier = random.choice(size_options)
                elif board_analysis.get('static', False):
                    multiplier = 0.85  # Can bet large on safe boards
                else:
                    multiplier = 0.75  # Standard large bet on coordinated boards
            elif hand_strength >= 0.80:
                if street == 'turn':
                    # Strong turn hands: 60%, 75%, or 90% pot
                    multiplier = random.choice([0.60, 0.75, 0.90])
                else:
                    multiplier = 0.70
            else:  # 0.75-0.79
                if street == 'turn':
                    # Medium-strong turn hands: 50%, 65%, or 80% pot
                    multiplier = random.choice([0.50, 0.65, 0.80])
                else:
                    multiplier = 0.60
                
        elif bet_type == 'thin_value':
            multiplier = 0.50  # Smaller for thin value
            
        elif bet_type == 'semi_bluff':
            if street == 'turn':
                # Turn semi-bluffs get more variety
                if board_analysis.get('draw_heavy', False):
                    # Draw-heavy boards: 60%, 75%, or 90% pot
                    multiplier = random.choice([0.60, 0.75, 0.90])
                else:
                    # Static boards: 50%, 65%, or 80% pot
                    multiplier = random.choice([0.50, 0.65, 0.80])
            else:
                # Flop semi-bluffs remain standard
                if board_analysis.get('draw_heavy', False):
                    multiplier = 0.65  # Medium size on draw-heavy boards
                else:
                    multiplier = 0.55  # Smaller on static boards
                
        elif bet_type == 'bluff':
            if street == 'turn':
                # Turn bluffs get more variety and bigger sizes for balance
                if board_analysis.get('texture_type') in ['coordinated_wet', 'double_draw']:
                    # Large bluffs on scary boards: 75%, 90%, or 110% pot
                    multiplier = random.choice([0.75, 0.90, 1.10])
                elif board_analysis.get('static', False):
                    # Small-medium bluffs on dry boards: 40%, 55%, or 75% pot
                    multiplier = random.choice([0.40, 0.55, 0.75])
                else:
                    # Standard bluff variety: 60%, 75%, or 95% pot
                    multiplier = random.choice([0.60, 0.75, 0.95])
            else:
                # Flop bluffs remain the same
                if board_analysis.get('texture_type') in ['coordinated_wet', 'double_draw']:
                    multiplier = 0.80  # Large bluffs on scary boards
                elif board_analysis.get('static', False):
                    multiplier = 0.45  # Small bluffs on dry boards
                else:
                    multiplier = 0.65  # Standard bluff size
        else:
            multiplier = 0.67  # Default
            
        # Position adjustments
        if position == 'oop':
            multiplier += 0.05  # Bet slightly larger out of position
            
        # Street adjustments
        if street == 'flop':
            multiplier *= 0.95  # Slightly smaller on flop
        elif street == 'turn':
            multiplier *= 1.05  # Slightly larger on turn
            
        # Board texture fine-tuning
        if board_analysis.get('paired', False):
            multiplier *= 0.90  # Smaller on paired boards
        if board_analysis.get('connectivity_score', 0) >= 7:
            multiplier *= 1.10  # Larger on highly connected boards
            
        final_size = min(stack, max(round(pot * 0.25), round(pot * multiplier)))
        return final_size

    def calculate_optimal_raise_size(self, hand_strength, bet_to_call, pot, stack, street, board_analysis, raise_type):
        """Calculate optimal raise size for different situations."""
        if raise_type == 'value':
            if hand_strength >= 0.90:  # Nuts
                raise_amount = min(stack - bet_to_call, round((pot + bet_to_call) * 1.0))
            elif hand_strength >= 0.80:  # Very strong
                raise_amount = min(stack - bet_to_call, round((pot + bet_to_call) * 0.8))
            else:  # Strong
                raise_amount = min(stack - bet_to_call, round((pot + bet_to_call) * 0.6))
                
        elif raise_type == 'semi_bluff':
            # Semi-bluff raises should be substantial but not huge
            raise_amount = min(stack - bet_to_call, round((pot + bet_to_call) * 0.7))
            
        else:  # Default
            raise_amount = min(stack - bet_to_call, round((pot + bet_to_call) * 0.8))
            
        return max(bet_to_call, raise_amount)  # Ensure minimum raise

    def needs_protection(self, hand_strength, board_analysis, street):
        """Determine if hand needs protection betting."""
        if hand_strength < 0.55 or street == 'river':  # Not strong enough or no more cards
            return False
            
        # Calculate opponent's potential equity
        draw_equity = 0
        if board_analysis.get('flush_draws', 0) >= 1:
            draw_equity += 0.20  # Approximate flush draw equity
        if board_analysis.get('straight_draws', 0) >= 1:
            draw_equity += 0.17  # Approximate straight draw equity
        if board_analysis.get('backdoor_draws', 0) >= 1:
            draw_equity += 0.05  # Backdoor equity
            
        # Protect if opponent likely has significant equity
        return draw_equity >= 0.25

    def calculate_protection_bet_size(self, hand_strength, pot, stack, board_analysis):
        """Calculate bet size for protection."""
        # Protection bets should be substantial to charge draws properly
        if board_analysis.get('draw_heavy', False):
            multiplier = 0.80  # Large bet on very draw-heavy boards
        elif board_analysis.get('total_draws', 0) >= 1:
            multiplier = 0.70  # Good-sized bet with some draws
        else:
            multiplier = 0.60  # Medium bet
            
        return min(stack, round(pot * multiplier))

    def should_semi_bluff(self, hand_strength, equity, board_analysis, position, street):
        """Determine if this is a good semi-bluff spot."""
        if street == 'river' or equity < 0.25:  # No draws on river or too weak
            return False
            
        semi_bluff_score = 0
        
        # Equity considerations
        if equity >= 0.40:  # Strong draws
            semi_bluff_score += 30
        elif equity >= 0.30:  # Decent draws
            semi_bluff_score += 20
            
        # Position advantage
        if position == 'ip':
            semi_bluff_score += 15
            
        # Board texture
        if board_analysis.get('draw_heavy', False):
            semi_bluff_score += 10  # Good to semi-bluff on draw-heavy boards
        if board_analysis.get('connectivity_score', 0) >= 6:
            semi_bluff_score += 10
            
        # Convert to probability
        probability = min(0.70, semi_bluff_score / 100)
        
        return random.random() < probability

    def should_bluff_advanced(self, hand_strength, board_analysis, position, street, pot, stack):
        """Advanced bluff selection with multiple factors."""
        if street == 'river':
            return False  # River bluffs handled separately
            
        bluff_score = 0
        
        # Base bluff frequencies by street
        base_frequencies = {'flop': 0.25, 'turn': 0.20}
        base_score = base_frequencies.get(street, 0.15) * 100
        
        # Position advantage
        if position == 'ip':
            bluff_score += 20
        else:
            bluff_score += 5  # Some bluffs out of position
            
        # Board texture considerations
        texture_type = board_analysis.get('texture_type', 'rainbow_dry')
        if texture_type in ['coordinated_wet', 'double_draw']:
            bluff_score += 25  # More bluffs on scary boards
        elif texture_type == 'rainbow_dry':
            bluff_score += 10  # Some bluffs on dry boards
        elif texture_type == 'paired_dry':
            bluff_score += 15  # Medium bluffs on paired boards
            
        # Connectivity and action considerations
        if board_analysis.get('connectivity_score', 0) >= 7:
            bluff_score += 15
        if board_analysis.get('action_cards'):
            bluff_score += 20
            
        # Stack depth considerations
        stack_pot_ratio = stack / pot if pot > 0 else 10
        if stack_pot_ratio >= 3:  # Deep stacks
            bluff_score += 10
        elif stack_pot_ratio <= 1.5:  # Short stacks
            bluff_score -= 15
            
        # Hand-specific factors (simplified blocker analysis)
        if hand_strength <= 0.15:  # Very weak hands are better bluffs
            bluff_score += 10
            
        final_probability = min(0.50, (base_score + bluff_score) / 100)
        
        return random.random() < final_probability

    def calculate_value_bet_size(self, hand_strength, pot, stack, street):
        if street == 'river':
            return min(stack, round(pot * 0.75))
        return min(stack, round(pot * 0.67))

    def calculate_value_raise_size(self, hand_strength, bet_to_call, pot, stack, street):
        return self.calculate_optimal_raise_size(hand_strength, bet_to_call, pot, stack, street, {}, 'value')

    def calculate_hand_strength_normalized(self, hand, community):
        if not community: return self.get_simple_hand_strength(hand)
        try:
            score, _ = evaluate_hand(hand, community)
            # Hand score scaling, for rough strength estimat 
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

    # board texture analysis
    def analyze_board_comprehensive(self, community, street):
        """Advanced comprehensive board analysis for strategic decisions"""
        if len(community) < 3:
            return {'type': 'preflop', 'texture_type': 'preflop', 'static': True, 'draw_heavy': False}

        ranks = [card[0] for card in community]
        suits = [card[1] for card in community]
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
                       'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        values = sorted([rank_values[r] for r in ranks])

        # Draw analysis
        flush_draws = self.count_flush_draws(community)
        straight_draws = self.count_straight_draws(community)
        backdoor_draws = self.count_backdoor_draws(community, street)

        # Board coordination
        connectivity_score = self.calculate_connectivity(community)
        rank_spread = max(values) - min(values)
        gap_count = self.count_gaps_in_sequence(community)

        # Pairing analysis
        paired = len(set(ranks)) < len(ranks)
        trips_plus = any(ranks.count(rank) >= 3 for rank in ranks)

        # Texture categorization
        texture_type = self.categorize_texture_type(community, flush_draws, straight_draws, paired)
        draw_heavy = flush_draws + straight_draws >= 2 or (flush_draws >= 1 and straight_draws >= 1)
        static = not draw_heavy and not paired and rank_spread <= 6

        # Street-specific analysis
        action_cards = self.identify_action_cards(community, street) if street in ['turn', 'river'] else []
        brick_cards = self.identify_brick_cards(community, street) if street in ['turn', 'river'] else []

        return {
            'type': 'postflop',
            'street': street,
            
            # Draw information
            'flush_draws': flush_draws,
            'straight_draws': straight_draws,
            'backdoor_draws': backdoor_draws,
            'total_draws': flush_draws + straight_draws,
            
            # Board coordination
            'connectivity_score': connectivity_score,  # 0-10 scale
            'rank_spread': rank_spread,
            'gap_count': gap_count,
            
            # Texture categories
            'texture_type': texture_type,
            'draw_heavy': draw_heavy,
            'static': static,
            'paired': paired,
            'trips_plus': trips_plus,
            
            # Legacy compatibility
            'wet': draw_heavy or paired,
            'dry': static and not paired,
            
            # Street-specific
            'action_cards': action_cards,
            'brick_cards': brick_cards,
        }

    def count_flush_draws(self, community):
        """Count flush draws on board."""
        suits = [card[1] for card in community]
        suit_counts = {}
        for suit in suits:
            suit_counts[suit] = suit_counts.get(suit, 0) + 1
        
        flush_draws = 0
        for count in suit_counts.values():
            if count == 3:  # flush draw
                flush_draws += 1
            elif count >= 4:  # flush
                flush_draws += 2  
        return flush_draws

    def count_straight_draws(self, community):
        """Count straight draws on board."""
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
                       'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        values = sorted(list(set([rank_values[card[0]] for card in community])))
        
        straight_draws = 0
        
        # Check for open-ended straight draws
        for i in range(len(values) - 2):
            if i + 3 < len(values) and values[i+3] - values[i] == 3:  # 4 in a row
                straight_draws += 2  # Open-ended = 2 points
            elif i + 2 < len(values) and values[i+2] - values[i] <= 4:  # Potential straight
                straight_draws += 1  # Gutshot/weak draw = 1 point
        
        # Special case for wheel draws (A-2-3-4-5)
        if 14 in values and 2 in values and 3 in values:
            straight_draws += 1
            
        return min(straight_draws, 3)  # Cap at 3 for very coordinated boards

    def count_backdoor_draws(self, community, street):
        """Count backdoor draw potential."""
        if street != 'flop' or len(community) != 3:
            return 0
            
        backdoor_count = 0
        
        # Backdoor flush draws (2 of same suit)
        suits = [card[1] for card in community]
        suit_counts = {}
        for suit in suits:
            suit_counts[suit] = suit_counts.get(suit, 0) + 1
        
        for count in suit_counts.values():
            if count == 2:
                backdoor_count += 1
        
        # Backdoor straight draws (simplified)
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
                       'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        values = sorted([rank_values[card[0]] for card in community])
        
        # Check if there's potential for backdoor straights
        if len(set(values)) >= 2 and max(values) - min(values) <= 8:
            backdoor_count += 1
            
        return min(backdoor_count, 2)

    def calculate_connectivity(self, community):
        """Calculate board connectivity score (0-10)."""
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
                       'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        values = sorted([rank_values[card[0]] for card in community])
        
        connectivity = 0
        
        # Points for consecutive ranks
        for i in range(len(values) - 1):
            if values[i+1] - values[i] == 1:
                connectivity += 3
            elif values[i+1] - values[i] == 2:
                connectivity += 2
            elif values[i+1] - values[i] == 3:
                connectivity += 1
                
        # Points for suit coordination
        suits = [card[1] for card in community]
        suit_counts = list(suit_counts.values()) if (suit_counts := {suit: suits.count(suit) for suit in set(suits)}) else []
        
        for count in suit_counts:
            if count >= 3:
                connectivity += 3
            elif count == 2:
                connectivity += 1
                
        return min(connectivity, 10)

    def count_gaps_in_sequence(self, community):
        """Count gaps in rank sequence."""
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
                       'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        values = sorted(list(set([rank_values[card[0]] for card in community])))
        
        if len(values) < 2:
            return 0
            
        gaps = 0
        for i in range(len(values) - 1):
            gap_size = values[i+1] - values[i] - 1
            gaps += max(0, gap_size)
            
        return gaps

    def categorize_texture_type(self, community, flush_draws, straight_draws, paired):
        """Categorize the overall board texture."""
        if paired:
            if flush_draws >= 1 or straight_draws >= 1:
                return 'paired_coordinated'
            else:
                return 'paired_dry'
        elif flush_draws >= 1 and straight_draws >= 1:
            return 'double_draw'
        elif flush_draws >= 2 or straight_draws >= 2:
            return 'coordinated_wet'
        elif flush_draws >= 1 or straight_draws >= 1:
            return 'single_draw'
        else:
            return 'rainbow_dry'

    def identify_action_cards(self, community, street):
        """Identify cards that create action (complete draws, etc.)."""
        if street == 'flop' or len(community) < 4:
            return []
            
        action_cards = []
        prev_community = community[:-1]  # Board before this card
        new_card = community[-1]
        
        # Check if new card completed a flush
        suits = [card[1] for card in community]
        prev_suits = [card[1] for card in prev_community]
        
        suit_counts = {suit: suits.count(suit) for suit in set(suits)}
        prev_suit_counts = {suit: prev_suits.count(suit) for suit in set(prev_suits)}
        
        for suit in suit_counts:
            if suit_counts[suit] >= 4 and prev_suit_counts.get(suit, 0) == 3:
                action_cards.append('flush_complete')
                break
                
        # Check if new card completed a straight (simplified)
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
                       'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        values = sorted([rank_values[card[0]] for card in community])
        
        # Simple straight detection
        consecutive_count = 1
        max_consecutive = 1
        for i in range(len(values) - 1):
            if values[i+1] - values[i] == 1:
                consecutive_count += 1
                max_consecutive = max(max_consecutive, consecutive_count)
            else:
                consecutive_count = 1
                
        if max_consecutive >= 4:
            action_cards.append('straight_possible')
            
        return action_cards

    def identify_brick_cards(self, community, street):
        """Identify cards that don't change much (bricks)."""
        if street == 'flop' or len(community) < 4:
            return []
            
        new_card = community[-1]
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
                       'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        
        brick_cards = []
        
        # Low cards that don't connect
        new_rank = rank_values[new_card[0]]
        board_ranks = [rank_values[card[0]] for card in community[:-1]]
        
        # If new card is low and doesn't connect to existing ranks
        if new_rank <= 6:
            min_existing = min(board_ranks)
            if new_rank < min_existing - 2:  # Doesn't connect
                brick_cards.append('low_brick')
                
        # If new card doesn't create flush draws or straight draws
        prev_analysis = self.analyze_board_comprehensive(community[:-1], 'turn' if street == 'river' else 'flop')
        current_draws = self.count_flush_draws(community) + self.count_straight_draws(community)
        prev_draws = prev_analysis['total_draws']
        
        if current_draws <= prev_draws:  # Didn't increase draw potential
            brick_cards.append('non_action')
            
        return brick_cards

    def analyze_board_texture_advanced(self, community):
        """Legacy method - redirect to comprehensive analysis."""
        analysis = self.analyze_board_comprehensive(community, 'flop')
        return {
            'dry': analysis['dry'],
            'wet': analysis['wet'], 
            'paired': analysis['paired'],
            'flush_draw': analysis['flush_draws'] >= 1,
            'straight_draw': analysis['straight_draws'] >= 1
        }

    # ----- Multi-street planning system -----
    def create_multi_street_plan(self, hand, community, street, position, stack_bb, hand_strength):
        """Create a multi-street betting plan for consistency."""
        hand_category = self.categorize_hand(hand, community, hand_strength)
        
        plan = {
            'current_street': street,
            'hand_category': hand_category,
            'position': position,
            'stack_depth': 'short' if stack_bb <= 25 else 'medium' if stack_bb <= 60 else 'deep',
            'planned_actions': {},
            'reasoning': ''
        }
        
        if hand_category == 'premium_value':  # 0.85+ hand strength
            plan['planned_actions'] = {
                'flop': 'bet_large',
                'turn': 'bet_large', 
                'river': 'bet_large'
            }
            plan['reasoning'] = 'Extract maximum value across all streets'
            
        elif hand_category == 'strong_value':  # 0.65-0.84 hand strength
            plan['planned_actions'] = {
                'flop': 'bet_medium',
                'turn': 'bet_medium_or_check',
                'river': 'thin_value_or_check'
            }
            plan['reasoning'] = 'Value bet but be cautious on dangerous runouts'
            
        elif hand_category == 'medium_made':  # 0.40-0.64 hand strength
            plan['planned_actions'] = {
                'flop': 'check_or_small_bet',
                'turn': 'check_call',
                'river': 'check_call_thin'
            }
            plan['reasoning'] = 'Pot control, call reasonable bets'
            
        elif hand_category == 'strong_draw':  # <0.40 strength but high equity
            plan['planned_actions'] = {
                'flop': 'semi_bluff',
                'turn': 'evaluate_improvement',
                'river': 'give_up_or_bluff'
            }
            plan['reasoning'] = 'Semi-bluff early, evaluate improvement'
            
        elif hand_category == 'weak_draw':  # Some equity but weak
            plan['planned_actions'] = {
                'flop': 'check_call_or_fold',
                'turn': 'check_fold',
                'river': 'check_fold'
            }
            plan['reasoning'] = 'Draw cheaply, fold to pressure'
            
        else:  # 'air' - very weak hands
            plan['planned_actions'] = {
                'flop': 'check_fold_or_bluff',
                'turn': 'check_fold',
                'river': 'bluff_or_give_up'
            }
            plan['reasoning'] = 'Occasional bluffs, mostly give up'
            
        return plan

    def categorize_hand(self, hand, community, hand_strength):
        """Categorize hand for multi-street planning."""
        equity = self.postflop_strategy.calculate_hand_equity(hand, community, num_simulations=200)
        
        if hand_strength >= 0.85:
            return 'premium_value'
        elif hand_strength >= 0.65:
            return 'strong_value'
        elif hand_strength >= 0.40:
            return 'medium_made'
        elif equity >= 0.35:  # Strong draws
            return 'strong_draw'
        elif equity >= 0.20:  # Weak draws
            return 'weak_draw'
        else:
            return 'air'

    # ----- Betting line analysis system -----
    def analyze_betting_line(self, game_state, current_street):
        """Analyze the complete betting sequence to understand opponent's line"""
        action_history = game_state.get('action_history', [])
        
        line_analysis = {
            'opponent_aggressed_streets': [],
            'bet_sizes_by_street': {},
            'line_type': None,
            'delayed_cbet': False,
            'river_sizing_tell': None,
            'total_aggression': 0,
            'passive_streets': 0
        }
        
        # Track opponent actions by street
        streets = ['preflop', 'flop', 'turn', 'river']
        street_actions = {street: [] for street in streets}
        
        for action in action_history:
            if action.get('player') == 'Player 1':  # Opponent (human player)
                street = action.get('round')
                if street in street_actions:
                    street_actions[street].append(action)
        
        # Analyze each street for aggression
        for street in ['flop', 'turn', 'river']:
            street_betting_actions = [a for a in street_actions[street] if a.get('action') in ['bet', 'raise']]
            
            if street_betting_actions:
                line_analysis['opponent_aggressed_streets'].append(street)
                line_analysis['total_aggression'] += 1
                
                # Record bet sizes (convert to pot-relative if possible)
                last_bet = street_betting_actions[-1]
                bet_amount = last_bet.get('amount', 0)
                line_analysis['bet_sizes_by_street'][street] = bet_amount
            else:
                # Count check/call as passive
                passive_actions = [a for a in street_actions[street] if a.get('action') in ['check', 'call']]
                if passive_actions:
                    line_analysis['passive_streets'] += 1
        
        # Classify specific betting lines
        aggressed = line_analysis['opponent_aggressed_streets']
        
        if 'flop' not in aggressed and 'turn' not in aggressed and 'river' in aggressed:
            line_analysis['line_type'] = 'check_check_bet'
            line_analysis['delayed_cbet'] = True
            
        elif 'flop' in aggressed and 'turn' not in aggressed and 'river' in aggressed:
            line_analysis['line_type'] = 'cbet_check_bet'
            
        elif 'flop' in aggressed and 'turn' in aggressed and 'river' in aggressed:
            line_analysis['line_type'] = 'triple_barrel'
            
        elif 'flop' in aggressed and 'turn' in aggressed and 'river' not in aggressed:
            line_analysis['line_type'] = 'double_barrel_check'
            
        elif len(aggressed) == 0:
            line_analysis['line_type'] = 'passive_line'
            
        else:
            line_analysis['line_type'] = 'mixed_aggression'
        
        # Analyze river bet sizing if there is one
        if 'river' in aggressed and current_street == 'river':
            river_bet = line_analysis['bet_sizes_by_street'].get('river', 0)
            pot_size = game_state.get('pot', 1)  # Avoid division by zero
            
            bet_pot_ratio = river_bet / pot_size if pot_size > 0 else 0
            
            if bet_pot_ratio <= 0.4:
                line_analysis['river_sizing_tell'] = 'small'
            elif bet_pot_ratio <= 0.75:
                line_analysis['river_sizing_tell'] = 'medium'  
            elif bet_pot_ratio <= 1.2:
                line_analysis['river_sizing_tell'] = 'large'
            else:
                line_analysis['river_sizing_tell'] = 'overbet'
        
        return line_analysis

    def calculate_river_hand_strength(self, hand, community, line_analysis, board_analysis):
        """Context-aware hand strength that considers board texture and betting line"""
        
        # Get base hand strength  
        base_strength = self.calculate_hand_strength_normalized(hand, community)
        
        # Board texture adjustments
        if board_analysis.get('draw_heavy', False):
            # On wet boards, made hands become more valuable relative to draws
            if base_strength >= 0.55:  # Made hands get boost
                base_strength *= 1.05
            else:  # Weak hands/draws lose value
                base_strength *= 0.90
                
        elif board_analysis.get('static', False):
            # On dry boards, pairs become more valuable
            if 0.20 <= base_strength <= 0.45:  # Pair range gets boost
                base_strength *= 1.15
            # But very weak hands still weak
            elif base_strength < 0.20:
                base_strength *= 0.95
        
        # Pairing adjustments
        if board_analysis.get('paired', False):
            # On paired boards, full houses/quads more valuable, pairs less valuable
            if base_strength >= 0.80:  # Full house+ range
                base_strength *= 1.08
            elif base_strength <= 0.40:  # Weak pairs become much weaker
                base_strength *= 0.85
        
        # Betting line adjustments (this is key for river play)
        if line_analysis.get('delayed_cbet', False):
            # On check-check-bet lines, opponent range is polarized
            # Medium hands lose significant value
            if 0.35 <= base_strength <= 0.70:  # Medium range hurt most
                base_strength *= 0.85
                print(f"DEBUG: Downgrading medium hand vs delayed c-bet: {base_strength:.3f}")
            # Very strong hands keep most value vs polarized range
            elif base_strength >= 0.85:
                base_strength *= 1.02
                
        elif line_analysis.get('line_type') == 'triple_barrel':
            # Against triple barrels, be more conservative with medium hands
            if 0.45 <= base_strength <= 0.75:
                base_strength *= 0.92
                
        elif line_analysis.get('line_type') == 'passive_line':
            # If opponent was passive then suddenly bets, be very suspicious
            if base_strength <= 0.70:
                base_strength *= 0.80  # Major downgrade
                print(f"DEBUG: Major downgrade vs passive-then-bet line: {base_strength:.3f}")
        
        # River sizing adjustments
        if line_analysis.get('river_sizing_tell') == 'overbet':
            # Overbets are very polarized - medium hands lose value
            if 0.40 <= base_strength <= 0.75:
                base_strength *= 0.88
        elif line_analysis.get('river_sizing_tell') == 'small':
            # Small bets can be wider range - medium hands gain value
            if 0.30 <= base_strength <= 0.60:
                base_strength *= 1.08
        
        # Ensure we don't go over 0.99 or under 0.05
        adjusted_strength = min(0.99, max(0.05, base_strength))
        
        if abs(adjusted_strength - base_strength) > 0.02:  # Log significant adjustments
            print(f"DEBUG: Hand strength adjusted from {base_strength:.3f} to {adjusted_strength:.3f} due to context")
        
        return adjusted_strength

    def has_river_blockers(self, hand_strength, community, line_analysis):
        """Improved blocker analysis for river decisions"""
        # This replaces the placeholder has_strong_blockers method
        
        # Simple blocker analysis - check if we block opponent's likely strong hands
        # Note: In this implementation, we'll use a simplified approach since hand is passed separately
        # In a full implementation, you'd track the current hand being analyzed
        board_cards = [card[0] for card in community]
        
        blocker_score = 0
        
        # For now, use a simplified random-based approach
        # In practice, you'd analyze the actual hand being played
        # Ace and King cards are common blockers
        if 'A' in board_cards:
            blocker_score += 10  # Assume we might have ace blockers
            
        # Against delayed c-bets, any decent hand has some blocking value
        if line_analysis.get('delayed_cbet', False):
            blocker_score += 12
            
        # Convert to boolean with some randomness to avoid being too predictable
        return blocker_score >= 15 and random.random() < 0.6

    # ----- River specialization system -----
    def river_decision_logic(self, hand, community, to_call, pot, ai_player, position, game_state, board_analysis):
        """Specialized river decision logic."""
        hand_strength = self.calculate_hand_strength_normalized(hand, community)
        
        # Analyze betting line for improved decision making
        line_analysis = self.analyze_betting_line(game_state, 'river')
        
        # Calculate context-aware hand strength
        adjusted_hand_strength = self.calculate_river_hand_strength(hand, community, line_analysis, board_analysis)
        
        if to_call == 0:  # We can bet or check
            return self.river_betting_decision(adjusted_hand_strength, community, pot, ai_player, position, board_analysis)
        else:  # Facing a bet
            return self.river_calling_decision(adjusted_hand_strength, to_call, pot, community, position, board_analysis, line_analysis)

    def river_betting_decision(self, hand_strength, community, pot, ai_player, position, board_analysis):
        """River betting decision with polarized strategy."""
        stack = ai_player['stack']
        
        # River betting is more polarized - strong hands and bluffs, fewer medium bets
        # TIGHTENED value betting threshold from 0.70 to 0.75+ for better river play
        if hand_strength >= 0.75:  # Strong value betting range (was 0.70)
            bet_size = self.calculate_river_value_size(hand_strength, pot, stack, board_analysis)
            print(f"DEBUG: River value bet - hand_strength: {hand_strength:.3f}, bet_size: {bet_size}")
            return ('raise', ai_player['current_bet'] + bet_size)
            
        elif hand_strength <= 0.25 and self.should_river_bluff(hand_strength, community, position, pot, board_analysis):
            bluff_size = self.calculate_river_bluff_size(pot, stack, board_analysis)
            print(f"DEBUG: River bluff - hand_strength: {hand_strength:.3f}, bluff_size: {bluff_size}")
            return ('raise', ai_player['current_bet'] + bluff_size)
            
        else:  # Medium hands - mostly check for pot control
            print(f"DEBUG: River check - hand_strength: {hand_strength:.3f} (medium range)")
            return ('check', 0)

    def river_calling_decision(self, hand_strength, to_call, pot, community, position, board_analysis, line_analysis):
        """River calling decision with much tighter ranges and betting line awareness."""
        pot_odds = pot / (pot + to_call) if (pot + to_call) > 0 else 0
        bet_size_ratio = to_call / pot if pot > 0 else 0
        
        # MUCH TIGHTER calling thresholds (increased by 0.15-0.20)
        calling_thresholds = {
            0.25: 0.50,   # Small bet (1/4 pot) - need decent two pair+ (was 0.35)
            0.33: 0.55,   # 1/3 pot - need strong two pair+ (new threshold)  
            0.50: 0.65,   # Medium bet (1/2 pot) - need trips+ (was 0.45)
            0.75: 0.75,   # Large bet (3/4 pot) - need strong trips+ (was 0.55)
            1.00: 0.80,   # Pot bet - need very strong trips+ (was 0.65)
            1.50: 0.90,   # Large overbet - need near nuts (was 0.75)
            2.00: 0.95,   # Huge overbet - need nuts (was 0.85)
        }
        
        # Find appropriate threshold
        required_strength = 0.50  # Default much higher (was 0.35)
        for size_threshold in sorted(calling_thresholds.keys()):
            if bet_size_ratio >= size_threshold:
                required_strength = calling_thresholds[size_threshold]
        
        # MAJOR ADJUSTMENTS for betting lines (this is the key improvement)
        if line_analysis.get('line_type') == 'check_check_bet':
            required_strength += 0.15  # Much tighter vs delayed c-bet - very suspicious!
            print(f"DEBUG: Check-check-bet line detected, tightening by +0.15")
            
        elif line_analysis.get('line_type') == 'cbet_check_bet':
            required_strength += 0.10  # Tighter vs missed c-bet then river bet
            
        elif line_analysis.get('line_type') == 'triple_barrel':
            required_strength -= 0.05  # Slightly looser vs consistent aggression (more likely to bluff)
            
        elif line_analysis.get('line_type') == 'passive_line':
            required_strength += 0.20  # If they suddenly bet after passive line, be very tight!
        
        # River sizing adjustments
        if line_analysis.get('river_sizing_tell') == 'small':
            required_strength -= 0.05  # Small bets can be called lighter
        elif line_analysis.get('river_sizing_tell') == 'overbet':
            required_strength += 0.05  # Overbets are more polarized
        
        # Board texture adjustments (more conservative)
        if board_analysis.get('action_cards'):
            required_strength += 0.08  # More cautious on action boards (was 0.05)
        if board_analysis.get('brick_cards'):
            required_strength -= 0.03  # Less liberal on brick cards (was 0.05)
        
        # Opponent model integration
        opponent_model = getattr(self, 'opponent_model', {})
        postflop_stats = opponent_model.get('postflop_stats', {})
        
        # If opponent folds to c-bet a lot, they're probably tighter on river
        fold_to_cbet = postflop_stats.get('fold_to_cbet', 0) / max(1, postflop_stats.get('fold_to_cbet_opportunities', 1))
        if fold_to_cbet > 0.6:  # Tight opponent
            required_strength -= 0.05
        elif fold_to_cbet < 0.4:  # Loose opponent  
            required_strength += 0.05
            
        # Blocker analysis (simplified but functional)
        if self.has_river_blockers(hand_strength, community, line_analysis):
            required_strength -= 0.05  # Can call lighter with blockers
            
        # Clamp to reasonable bounds
        required_strength = min(0.95, max(0.45, required_strength))
            
        print(f"DEBUG: River call decision - hand_strength: {hand_strength:.3f}, required: {required_strength:.3f}, bet_ratio: {bet_size_ratio:.2f}, line: {line_analysis.get('line_type', 'unknown')}")
        
        if hand_strength >= required_strength:
            return ('call', 0)
        else:
            return ('fold', 0)

    def calculate_river_value_size(self, hand_strength, pot, stack, board_analysis):
        """Calculate optimal river value bet size with expanded variety up to 150% pot."""
        # River value betting - size based on hand strength and board
        if hand_strength >= 0.90:  # Near nuts
            if board_analysis.get('static', False):
                # Variety on dry boards: 100%, 125%, or 150% pot
                size_options = [1.0, 1.25, 1.5]
                multiplier = random.choice(size_options)
                return min(stack, round(pot * multiplier))
            else:
                # Wet boards get variety: 75%, 90%, or 110% pot
                size_options = [0.75, 0.90, 1.10]
                multiplier = random.choice(size_options)
                return min(stack, round(pot * multiplier))
                
        elif hand_strength >= 0.80:  # Very strong
            # Variety: 65%, 80%, or 95% pot
            size_options = [0.65, 0.80, 0.95]
            multiplier = random.choice(size_options)
            return min(stack, round(pot * multiplier))
            
        elif hand_strength >= 0.70:  # Strong but not nuts
            # Variety: 50%, 65%, or 80% pot
            size_options = [0.50, 0.65, 0.80]
            multiplier = random.choice(size_options)
            return min(stack, round(pot * multiplier))
            
        else:  # Shouldn't be value betting this weak on river
            return min(stack, round(pot * 0.45))

    def calculate_river_bluff_size(self, pot, stack, board_analysis):
        """Calculate optimal river bluff size with high-bet variety for balance."""
        # River bluffs should be polarized - either small or large
        # Now including overbets to balance large value bets
        if board_analysis.get('texture_type') in ['coordinated_wet', 'double_draw']:
            # Large bluffs on scary boards: 80%, 100%, or 120% pot
            size_options = [0.80, 1.0, 1.20]
            multiplier = random.choice(size_options)
            return min(stack, round(pot * multiplier))
        elif board_analysis.get('static', False):
            # Variety on static boards: 50%, 75%, or 100% pot  
            # Include some large bluffs to balance overbets
            size_options = [0.50, 0.75, 1.0]
            multiplier = random.choice(size_options)
            return min(stack, round(pot * multiplier))
        else:
            # Standard bluff variety: 60%, 80%, or 110% pot
            size_options = [0.60, 0.80, 1.10]
            multiplier = random.choice(size_options)
            return min(stack, round(pot * multiplier))

    def should_river_bluff(self, hand_strength, community, position, pot, board_analysis):
        """Determine if this is a good river bluff spot."""
        # River bluffing factors
        bluff_score = 0
        
        # Position advantage
        if position == 'ip':
            bluff_score += 15
            
        # Board texture considerations
        if board_analysis.get('action_cards'):
            bluff_score += 20  # Bluff more on action cards
        if board_analysis.get('brick_cards'):
            bluff_score -= 10  # Bluff less on brick cards
            
        # Hand-specific factors (blockers)
        if self.has_strong_blockers(community, position):
            bluff_score += 25
            
        # Stack considerations (simplified)
        # Deep stacks favor more bluffing
        bluff_score += 5
        
        # Frequency balance - don't bluff too often
        base_bluff_frequency = 0.25  # 25% base frequency
        
        # Convert score to probability
        bluff_probability = min(0.45, base_bluff_frequency + (bluff_score / 100))
        
        return random.random() < bluff_probability

    def has_strong_blockers(self, community, position):
        """Check if we have strong blockers (simplified analysis)."""
        # This is a simplified blocker check
        # In practice, you'd analyze specific card combinations
        return random.random() < 0.3  # Placeholder

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
    print("⚔️ BLADEWORK V2 AI IS MAKING A DECISION! ⚔️")
    global gto_ai
    if gto_ai is None:
        gto_ai = GTOEnhancedAI()
    return gto_ai.decide_action(game_state)
