"""
GTO-Enhanced Poker AI

This module combines Game Theory Optimal concepts with opponent modeling
to create a more sophisticated and adaptive poker AI.
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
        print(f"FULL GAME STATE: {game_state}")
        
        ai_player = game_state['players'][1]
        human_player = game_state['players'][0]
        hand = ai_player['hand']
        community = game_state['community']
        to_call = game_state.get('current_bet', 0) - ai_player['current_bet']
        pot = game_state['pot']
        betting_round = game_state['betting_round']
        
        # Debug logging
        print(f"DEBUG: AI hand: {hand}, position: {self.get_position(game_state)}, to_call: {to_call}, betting_round: {betting_round}")
        
        # Update opponent model with recent action
        self.update_opponent_model(game_state)
        
        # Calculate key metrics
        effective_stack = min(ai_player['stack'], human_player['stack'])
        stack_bb = effective_stack // BIG_BLIND
        pot_odds = self.calculate_pot_odds(to_call, pot)
        
        # Determine position (in heads-up, button is always 'in position' postflop)
        position = self.get_position(game_state)
        
        if betting_round == 'preflop':
            result = self.preflop_decision(hand, to_call, pot, ai_player, stack_bb, position, game_state)
            print(f"DEBUG: Preflop decision: {result}")
            return result
        else:
            result = self.postflop_decision(hand, community, to_call, pot, ai_player, stack_bb, position, betting_round, game_state)
            print(f"DEBUG: Postflop decision: {result}")
            return result
    
    def get_position(self, game_state):
        """Determine AI's position relative to opponent"""
        # In heads-up: dealer/button acts first preflop, last postflop
        dealer_pos = game_state.get('dealer_pos', 0)
        ai_position = 1  # AI is player 1
        
        if game_state['betting_round'] == 'preflop':
            return 'button' if ai_position == dealer_pos else 'bb'
        else:
            return 'ip' if ai_position == dealer_pos else 'oop'  # in position / out of position
    
    def preflop_decision(self, hand, to_call, pot, ai_player, stack_bb, position, game_state):
        """
        Enhanced preflop decision making using charts and opponent modeling
        """
        print(f"DEBUG: Preflop - position: {position}, to_call: {to_call}")
        print(f"DEBUG: dealer_pos: {game_state.get('dealer_pos')}, ai_position: 1")
        print(f"DEBUG: current_player: {game_state.get('current_player')}")
        
        # Check if this is truly SB RFI situation:
        # 1. AI must be the Small Blind (button in heads-up)
        # 2. No one has acted yet (no action history for this round)
        # 3. In heads-up, SB can complete (call BB) or raise - this is SB RFI territory
        action_history = game_state.get('action_history', [])
        preflop_actions = [a for a in action_history if a.get('round') == 'preflop']
        is_first_action = len(preflop_actions) == 0
        
        # In heads-up, SB posts 10, BB posts 20, so SB has to_call=10 to complete
        # This is still considered "SB RFI" because SB is first to act voluntarily
        is_sb_completing_blind = (position == 'button' and to_call == SMALL_BLIND and is_first_action)
        
        print(f"DEBUG: is_first_action: {is_first_action}, preflop_actions: {len(preflop_actions)}")
        print(f"DEBUG: action_history: {action_history}")
        print(f"DEBUG: SB RFI conditions check:")
        print(f"  - position == 'button': {position == 'button'}")
        print(f"  - to_call == SMALL_BLIND: {to_call == SMALL_BLIND}")
        print(f"  - is_first_action: {is_first_action}")
        print(f"  - is_sb_completing_blind: {is_sb_completing_blind}")
        
        # SB RFI: Small Blind acting first preflop (completing the blind counts as first action)
        if is_sb_completing_blind:
            print("*** USING SB RFI CHART ***")
            hand_str = self.hand_to_string(hand)
            print(f"DEBUG: Hand string conversion: {hand} -> {hand_str}")
            
            if hand_str in self.sb_rfi_chart:
                chart_entry = self.sb_rfi_chart[hand_str]
                print(f"DEBUG: Chart entry for {hand_str}: {chart_entry}")
            else:
                print(f"DEBUG: Hand {hand_str} NOT FOUND in SB RFI chart")
                
            chart_action = self.sb_first_action(hand)
            print(f"DEBUG: SB RFI - hand: {hand}, chart_action: {chart_action}")
            
            # Apply opponent adjustments
            adjusted_action = self.adjust_for_opponent_preflop(
                chart_action, hand, to_call, pot, ai_player, position
            )
            print(f"DEBUG: Adjusted action: {adjusted_action}")
            
            result = self.convert_action_to_game_format(adjusted_action, to_call, pot, ai_player, 'preflop')
            print(f"DEBUG: Final SB RFI result: {result}")
            return result
        else:
            print(f"*** NOT USING SB RFI CHART - Condition failed ***")
            print(f"   position: {position} (should be 'button')")
            print(f"   to_call: {to_call} (should be {SMALL_BLIND})")
            print(f"   is_first_action: {is_first_action} (should be True)")
            print(f"   is_sb_completing_blind: {is_sb_completing_blind} (should be True)")
        
        # For all other situations, use existing preflop charts logic
        if to_call == 0:
            # In heads-up, if to_call is 0, BB has option to check/raise after SB called
            position = self.get_position(game_state)
            if position == 'bb' and len(preflop_actions) > 0:
                # BB after SB called - this is actually a "no raise" situation
                # BB should mostly check, occasionally raise with strong hands
                hand_strength = self.get_simple_hand_strength(hand)
                print(f"DEBUG: BB option to check/raise, hand_strength: {hand_strength}")
                
                if hand_strength >= 0.8:  # Very strong hands - raise
                    return self.convert_action_to_game_format('raise', to_call, pot, ai_player, 'preflop')
                elif hand_strength >= 0.6:  # Good hands - sometimes raise
                    if random.random() < 0.3:  # 30% of the time
                        return self.convert_action_to_game_format('raise', to_call, pot, ai_player, 'preflop')
                    else:
                        return self.convert_action_to_game_format('check', to_call, pot, ai_player, 'preflop')
                else:
                    # Weak/medium hands - just check
                    return self.convert_action_to_game_format('check', to_call, pot, ai_player, 'preflop')
            else:
                action_to_hero = 'none'  # Unopened pot
                raise_size_bb = 0
        else:
            # Determine if this is a raise, 3-bet, or 4-bet based on action history
            if len(preflop_actions) <= 1:
                action_to_hero = 'raise'
                raise_size_bb = to_call / BIG_BLIND
            else:
                # Count raises this round
                raises = sum(1 for a in preflop_actions if a.get('action') == 'raise')
                if raises == 2:
                    action_to_hero = '3bet'
                elif raises == 3:
                    action_to_hero = '4bet'
                else:
                    action_to_hero = 'raise'
                raise_size_bb = to_call / BIG_BLIND
        
        print(f"DEBUG: Using preflop charts - action_to_hero: {action_to_hero}, raise_size_bb: {raise_size_bb}")
        print(f"DEBUG: Hand: {hand}, Position: {position}, Stack BB: {stack_bb}")
        
        # Count total raises to pass to the comprehensive system
        total_raises = sum(1 for a in preflop_actions if a.get('action') == 'raise')
        pot_bb = pot / BIG_BLIND if BIG_BLIND > 0 else 0
        
        # Get chart-based decision
        try:
            chart_action = self.preflop_charts.get_preflop_action(
                hand, position, action_to_hero, raise_size_bb, stack_bb, pot_bb, total_raises
            )
            print(f"DEBUG: Chart action: {chart_action}")
        except Exception as e:
            print(f"DEBUG: Error in preflop_charts.get_preflop_action: {e}")
            chart_action = 'fold'  # Fallback
        
        # Use chart action if it's valid, otherwise fall back to simple logic
        if chart_action in ['call', '3bet', '4bet', 'raise', 'fold']:
            print(f"DEBUG: Using chart action: {chart_action}")
        else:
            print(f"DEBUG: Chart returned invalid action '{chart_action}', using simple hand strength logic")
            # Fallback to simple hand strength logic
            hand_strength = self.get_simple_hand_strength(hand)
            print(f"DEBUG: Hand strength: {hand_strength}")
            
            if action_to_hero == 'none':
                # Unopened pot - should never happen here since SB RFI handles this
                chart_action = 'fold'
            elif action_to_hero == 'raise':
                # Facing a raise - defend based on hand strength and position
                if position == 'bb':  # Big blind defending
                    if hand_strength >= 0.6:  # Strong hands
                        chart_action = 'call'
                    elif hand_strength >= 0.4:  # Medium hands - sometimes call
                        chart_action = 'call' if random.random() < 0.6 else 'fold'
                    else:
                        chart_action = 'fold'
                else:  # Button facing 3-bet
                    if hand_strength >= 0.8:  # Very strong hands
                        chart_action = 'call'
                    elif hand_strength >= 0.6:  # Strong hands - sometimes call
                        chart_action = 'call' if random.random() < 0.4 else 'fold'
                    else:
                        chart_action = 'fold'
            else:
                # 3-bet, 4-bet situations - be very tight
                if hand_strength >= 0.85:
                    chart_action = 'call'
                else:
                    chart_action = 'fold'
            
            print(f"DEBUG: Fallback chart action: {chart_action}")
        
        # Apply opponent adjustments
        adjusted_action = self.adjust_for_opponent_preflop(
            chart_action, hand, to_call, pot, ai_player, position
        )
        print(f"DEBUG: Final adjusted action: {adjusted_action}")
        
        result = self.convert_action_to_game_format(adjusted_action, to_call, pot, ai_player, 'preflop')
        print(f"DEBUG: Final preflop result: {result}")
        return result
    
    def adjust_for_opponent_preflop(self, chart_action, hand, to_call, pot, ai_player, position):
        """
        Adjust preflop strategy based on opponent tendencies
        """
        opponent_vpip = self.opponent_model['preflop_stats']['vpip']
        opponent_pfr = self.opponent_model['preflop_stats']['pfr']
        opponent_fold_to_3bet = self.opponent_model['preflop_stats']['fold_to_three_bet']
        
        # Against tight opponents (low VPIP), 3-bet more for value
        if opponent_vpip < 0.3 and chart_action == 'call':
            try:
                hand_strength = self.preflop_charts.get_hand_tuple(hand)
                if hand_strength in [(14, 14), (13, 13), (12, 12), (14, 13, True)]:
                    chart_action = '3bet'
            except:
                # Fallback if get_hand_tuple fails
                hand_strength = self.get_simple_hand_strength(hand)
                if hand_strength >= 0.85:
                    chart_action = '3bet'
        
        # Against loose opponents (high VPIP), call more and 3-bet less
        elif opponent_vpip > 0.7 and chart_action == '3bet':
            if random.random() < 0.4:  # Sometimes just call instead
                chart_action = 'call'
        
        # Against opponents who fold too much to 3-bets, bluff 3-bet more
        if opponent_fold_to_3bet > 0.8 and position == 'bb':
            if chart_action == 'fold' and random.random() < 0.15:
                chart_action = '3bet'  # Light 3-bet bluff
        
        # Against opponents who don't fold enough to 3-bets, reduce bluff frequency
        elif opponent_fold_to_3bet < 0.5 and chart_action == '3bet':
            # Only 3-bet with strong hands
            try:
                hand_strength = self.preflop_charts.get_hand_tuple(hand)
                value_3bets = [(14, 14), (13, 13), (12, 12), (11, 11), (10, 10), 
                              (14, 13, True), (14, 13, False), (14, 12, True)]
                if hand_strength not in value_3bets:
                    chart_action = 'call'  # Convert bluff 3-bets to calls
            except:
                hand_strength = self.get_simple_hand_strength(hand)
                if hand_strength < 0.8:  # Not strong enough for value 3-bet
                    chart_action = 'call'
        
        return chart_action
    
    def get_simple_hand_strength(self, hand):
        """
        Simple preflop hand strength evaluation (0-1 scale)
        """
        rank1, suit1 = hand[0][0], hand[0][1]
        rank2, suit2 = hand[1][0], hand[1][1]
        
        # Convert ranks to numeric values
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, 
                      '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        
        val1 = rank_values.get(rank1, 2)
        val2 = rank_values.get(rank2, 2)
        
        high_val = max(val1, val2)
        low_val = min(val1, val2)
        is_suited = suit1 == suit2
        is_pair = val1 == val2
        
        # Pocket pairs
        if is_pair:
            if high_val >= 10:  # TT+
                return 0.9
            elif high_val >= 7:  # 77-99
                return 0.7
            else:  # 22-66
                return 0.5
        
        # Suited hands
        if is_suited:
            if high_val == 14 and low_val >= 10:  # AK, AQ, AJ, AT suited
                return 0.85
            elif high_val >= 13 and low_val >= 10:  # KQ, KJ, KT suited
                return 0.75
            elif high_val >= 12 and low_val >= 9:  # QJ, QT suited
                return 0.65
            elif high_val >= 11 and low_val >= 9:  # JT suited
                return 0.6
            else:
                return 0.4
        
        # Offsuit hands
        else:
            if high_val == 14 and low_val >= 12:  # AK, AQ offsuit
                return 0.8
            elif high_val == 14 and low_val >= 10:  # AJ, AT offsuit
                return 0.65
            elif high_val >= 13 and low_val >= 11:  # KQ, KJ offsuit
                return 0.6
            else:
                return 0.3
    
    def postflop_decision(self, hand, community, to_call, pot, ai_player, stack_bb, position, street, game_state):
        """
        Advanced postflop decision making with GTO concepts
        """
        # Calculate hand strength and equity
        hand_strength = self.calculate_hand_strength_normalized(hand, community)
        
        # Calculate equity
        equity = self.postflop_strategy.calculate_hand_equity(hand, community, num_simulations=300)
        
        # Analyze board texture
        board_texture = self.analyze_board_texture_advanced(community)
        
        # Calculate pot odds and implied odds
        pot_odds = self.calculate_pot_odds(to_call, pot)
        implied_odds = self.calculate_implied_odds(to_call, pot, ai_player['stack'], hand_strength)
        
        # Determine if we're the aggressor or facing aggression
        aggression_context = self.analyze_aggression_context(game_state, street)
        
        # Main decision logic
        if to_call == 0:
            # We can check or bet
            return self.decide_check_or_bet(
                hand_strength, equity, pot, ai_player, board_texture, 
                position, street, aggression_context
            )
        else:
            # We must call, raise, or fold
            return self.decide_call_raise_fold(
                hand_strength, equity, pot_odds, implied_odds, to_call, 
                pot, ai_player, board_texture, position, street, aggression_context
            )
    
    def decide_check_or_bet(self, hand_strength, equity, pot, ai_player, board_texture, position, street, aggression_context):
        """
        Decide between checking and betting when facing no bet
        """
        # Strong hands - almost always bet for value
        if hand_strength >= 0.75:
            bet_size = self.calculate_value_bet_size(hand_strength, pot, ai_player['stack'], street)
            return ('raise', ai_player['current_bet'] + bet_size)
        
        # Good hands - mixed strategy
        elif hand_strength >= 0.55:
            # Bet more often in position
            bet_frequency = 0.8 if position == 'ip' else 0.6
            
            if random.random() < bet_frequency:
                bet_size = self.calculate_value_bet_size(hand_strength, pot, ai_player['stack'], street)
                return ('raise', ai_player['current_bet'] + bet_size)
            else:
                return ('check', 0)
        
        # Medium hands - mostly check, occasional small bet
        elif hand_strength >= 0.35:
            if position == 'ip' and random.random() < 0.3:
                bet_size = min(ai_player['stack'], round(pot * 0.4))  # Small bet
                return ('raise', ai_player['current_bet'] + bet_size)
            else:
                return ('check', 0)
        
        # Weak hands - check or bluff
        else:
            # Bluff considerations
            if self.should_bluff_gto(hand_strength, board_texture, position, street, pot, ai_player['stack']):
                bluff_size = self.calculate_bluff_size(board_texture, pot, ai_player['stack'], street)
                return ('raise', ai_player['current_bet'] + bluff_size)
            else:
                return ('check', 0)
    
    def decide_call_raise_fold(self, hand_strength, equity, pot_odds, implied_odds, to_call, pot, ai_player, board_texture, position, street, aggression_context):
        """
        Decide between calling, raising, or folding when facing a bet
        """
        # Very strong hands - raise for value
        if hand_strength >= 0.85:
            raise_size = self.calculate_value_raise_size(hand_strength, to_call, pot, ai_player['stack'], street)
            return ('raise', ai_player['current_bet'] + to_call + raise_size)
        
        # Strong hands - call or raise
        elif hand_strength >= 0.65:
            # Sometimes raise, sometimes call
            if random.random() < 0.4:  # 40% raise, 60% call
                raise_size = self.calculate_value_raise_size(hand_strength, to_call, pot, ai_player['stack'], street)
                return ('raise', ai_player['current_bet'] + to_call + raise_size)
            else:
                return ('call', 0)
        
        # Medium hands - mostly call if odds are good
        elif hand_strength >= 0.4:
            if pot_odds >= 2.5 or equity >= 0.35:
                return ('call', 0)
            else:
                return ('fold', 0)
        
        # Drawing hands - use pot odds and implied odds
        elif equity >= 0.3:
            total_odds = max(pot_odds, implied_odds)
            required_odds = (1 - equity) / equity
            
            if total_odds >= required_odds:
                return ('call', 0)
            else:
                return ('fold', 0)
        
        # Weak hands - mostly fold, occasional bluff-raise
        else:
            # Check for good bluff spots
            if self.should_bluff_raise(hand_strength, board_texture, position, street, to_call, pot, ai_player['stack']):
                bluff_raise_size = self.calculate_bluff_raise_size(to_call, pot, ai_player['stack'], street)
                return ('raise', ai_player['current_bet'] + to_call + bluff_raise_size)
            else:
                return ('fold', 0)
    
    def should_bluff_gto(self, hand_strength, board_texture, position, street, pot, stack):
        """
        GTO-based bluff frequency calculation
        """
        # Base bluff frequencies by street
        base_frequencies = {'flop': 0.3, 'turn': 0.25, 'river': 0.2}
        base_freq = base_frequencies.get(street, 0.2)
        
        # Adjust for position
        if position == 'ip':
            base_freq *= 1.2
        
        # Adjust for board texture
        if board_texture.get('wet', False):
            base_freq *= 1.3  # More bluffs on wet boards
        elif board_texture.get('dry', False):
            base_freq *= 0.8  # Fewer bluffs on dry boards
        
        # Consider stack size - more nuanced stack adjustments
        if stack < pot * 1.5:  # Very short stack
            base_freq *= 0.5  # Much fewer bluffs
        elif stack < pot * 3:  # Short stack
            base_freq *= 0.7  # Fewer bluffs
        elif stack > pot * 8:   # Deep stack
            base_freq *= 1.1    # Slightly more bluffs with deep stacks
        
        return random.random() < base_freq
    
    def should_bluff_raise(self, hand_strength, board_texture, position, street, bet_size, pot, stack):
        """
        Determine if this is a good spot for a bluff-raise
        """
        # Much more selective with bluff-raises
        base_freq = 0.1 if street == 'river' else 0.15
        
        # Need good blockers or semi-bluff equity
        # This is simplified - in reality you'd check for specific blockers
        if hand_strength < 0.2:  # Very weak hands are better bluffs
            base_freq *= 1.5
        
        # Less likely against large bets
        if bet_size > pot * 0.75:
            base_freq *= 0.5
        
        return random.random() < base_freq
    
    def calculate_value_bet_size(self, hand_strength, pot, stack, street):
        """
        Calculate optimal value bet size
        """
        if hand_strength >= 0.9:  # Nuts
            if street == 'river':
                bet_size = min(stack, pot * 1.2)  # Overbet for max value
            else:
                bet_size = min(stack, pot * 0.8)  # Build pot for future streets
        elif hand_strength >= 0.75:
            bet_size = min(stack, pot * 0.67)  # Standard value bet
        else:
            bet_size = min(stack, pot * 0.4)   # Smaller value bet
        
        return round(bet_size)
    
    def calculate_bluff_size(self, board_texture, pot, stack, street):
        """
        Calculate optimal bluff size
        """
        if board_texture.get('wet', False):
            bet_size = min(stack, pot * 0.8)  # Larger bluffs on wet boards
        else:
            bet_size = min(stack, pot * 0.6)  # Smaller bluffs on dry boards
        
        return round(bet_size)
    
    def calculate_value_raise_size(self, hand_strength, bet_to_call, pot, stack, street):
        """
        Calculate raise size for value
        """
        if hand_strength >= 0.85:
            raise_size = min(stack - bet_to_call, pot + bet_to_call)  # Large raise
        else:
            raise_size = min(stack - bet_to_call, (pot + bet_to_call) * 0.6)  # Moderate raise
        
        return round(raise_size)
    
    def calculate_bluff_raise_size(self, bet_to_call, pot, stack, street):
        """
        Calculate raise size for bluffs
        """
        # Bluff raises should be polarizing - either small or large
        if random.random() < 0.3:  # 30% small bluff-raise
            raise_size = min(stack - bet_to_call, bet_to_call * 2)
        else:  # 70% large bluff-raise
            raise_size = min(stack - bet_to_call, pot + bet_to_call)
        
        return round(raise_size)
    
    def calculate_hand_strength_normalized(self, hand, community):
        """
        Calculate normalized hand strength (0-1 scale)
        """
        try:
            score, _ = evaluate_hand(hand, community)
            # Convert treys score to 0-1 scale
            if score <= 10:
                return 0.99
            elif score <= 166:
                return 0.95
            elif score <= 322:
                return 0.90
            elif score <= 1599:
                return 0.85
            elif score <= 1609:
                return 0.80
            elif score <= 1609:
                return 0.75
            elif score <= 2467:
                return 0.65
            elif score <= 3325:
                return 0.50
            elif score <= 6185:
                return 0.35
            else:
                return 0.15
        except:
            return 0.2  # Conservative fallback
    
    def analyze_board_texture_advanced(self, community):
        """
        Advanced board texture analysis
        """
        if len(community) < 3:
            return {'type': 'preflop'}
        
        ranks = [card[0] for card in community]
        suits = [card[1] for card in community]
        
        # Flush analysis
        suit_counts = {}
        for suit in suits:
            suit_counts[suit] = suit_counts.get(suit, 0) + 1
        max_suit = max(suit_counts.values())
        
        # Straight analysis
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, 
                      '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        values = sorted([rank_values[rank] for rank in ranks])
        
        # Check for straights and draws
        straight_possible = False
        straight_draw = False
        
        if len(set(values)) >= 3:
            for i in range(len(values) - 2):
                if len(values) >= 3 and values[i+2] - values[i] <= 4:
                    straight_draw = True
                if len(values) >= 3 and values[i+2] - values[i] == 2:
                    straight_possible = True
        
        # Pair analysis
        paired = len(set(ranks)) < len(ranks)
        trips_plus = any(ranks.count(rank) >= 3 for rank in ranks)
        
        return {
            'type': 'postflop',
            'flush_draw': max_suit >= 3,
            'flush_possible': max_suit >= 3,
            'straight_draw': straight_draw,
            'straight_possible': straight_possible,
            'paired': paired,
            'trips_plus': trips_plus,
            'wet': max_suit >= 3 or straight_draw,
            'dry': max_suit <= 2 and not straight_draw and not paired,
            'coordinated': max_suit >= 3 or straight_draw or paired
        }
    
    def calculate_pot_odds(self, bet_to_call, pot_size):
        """
        Calculate pot odds
        """
        if bet_to_call <= 0:
            return float('inf')
        return pot_size / bet_to_call
    
    def calculate_implied_odds(self, bet_to_call, pot_size, remaining_stack, hand_strength):
        """
        Estimate implied odds based on hand strength and remaining stack
        """
        if bet_to_call <= 0:
            return float('inf')
        
        # Estimate how much more we can win if we hit our draw
        if hand_strength < 0.3:  # Drawing hand
            implied_value = min(remaining_stack * 0.3, pot_size * 0.5)
            return (pot_size + implied_value) / bet_to_call
        else:
            return pot_size / bet_to_call
    
    def analyze_aggression_context(self, game_state, street):
        """
        Analyze who has been the aggressor this hand
        """
        action_history = game_state.get('action_history', [])
        street_actions = [a for a in action_history if a.get('round') == street]
        
        ai_aggression = sum(1 for a in street_actions if a.get('player') == 'Player 2' and a.get('action') in ['raise', 'bet'])
        opponent_aggression = sum(1 for a in street_actions if a.get('player') == 'Player 1' and a.get('action') in ['raise', 'bet'])
        
        return {
            'ai_is_aggressor': ai_aggression > opponent_aggression,
            'opponent_is_aggressor': opponent_aggression > ai_aggression,
            'ai_aggression_count': ai_aggression,
            'opponent_aggression_count': opponent_aggression
        }
    
    def update_opponent_model(self, game_state):
        """
        Update opponent model based on observed actions
        """
        # This is a simplified version - in practice you'd track more detailed stats
        action_history = game_state.get('action_history', [])
        
        # Update hand count
        self.opponent_model['hands_played'] += 1
        
        # Track recent actions for pattern recognition
        if len(action_history) > 0:
            last_action = action_history[-1]
            if len(self.opponent_model['recent_actions']) >= 10:
                self.opponent_model['recent_actions'].pop(0)
            self.opponent_model['recent_actions'].append(last_action)
    
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
        elif chart_action in ['raise', 'bet']:
            if street == 'preflop':
                if to_call == SMALL_BLIND:
                    # SB RFI when completing blind: raise to 2.3 BB total
                    RFI_multiplyer = random.uniform(2.25,2.5)
                    total_raise_amount = math.ceil(BIG_BLIND * RFI_multiplyer)
                    raise_size = total_raise_amount - ai_player['current_bet']
                elif to_call == 0:
                    # Standard SB RFI: bet 2.3 BB rounded up
                    raise_size = math.ceil(BIG_BLIND * 2.3)
                else:
                    raise_size = to_call * 3  # 3-bet sizing
            else:
                raise_size = round(pot * 0.67)  # Standard postflop bet
            
            raise_size = min(raise_size, ai_player['stack'])
            return ('raise', ai_player['current_bet'] + raise_size)
        elif chart_action in ['3bet']:
            three_bet_size = max(to_call * 3, BIG_BLIND * 8)
            three_bet_size = min(three_bet_size, ai_player['stack'])
            return ('raise', ai_player['current_bet'] + three_bet_size)
        elif chart_action in ['4bet']:
            # 4-bet sizing: typically 2.2-2.5x the 3-bet size
            four_bet_size = max(to_call * 2.3, BIG_BLIND * 16)
            four_bet_size = min(four_bet_size, ai_player['stack'])
            return ('raise', ai_player['current_bet'] + four_bet_size)
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
