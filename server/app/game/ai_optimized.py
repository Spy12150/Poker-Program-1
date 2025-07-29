"""
Optimized Hardcoded Poker AI - Static, Non-Adaptive Version

This AI uses sophisticated poker theory but never learns or adapts.
It's designed to be a consistent, challenging opponent with optimal play.
"""

import random
import json
import os
from .hand_eval_lib import evaluate_hand
from .config import BIG_BLIND, SMALL_BLIND

class OptimizedHardcodedAI:
    def __init__(self):
        # Fixed strategy parameters - never change during gameplay
        self.aggression_factor = 1.8
        self.bluff_frequency = 0.12
        self.value_bet_threshold = 0.65
        self.fold_threshold = 0.25
        
        # Load preflop charts
        self.sb_rfi_chart = self.load_sb_rfi_chart()
        
    def load_sb_rfi_chart(self):
        """Load the Small Blind Raise First In chart from JSON file"""
        try:
            current_dir = os.path.dirname(__file__)
            chart_path = os.path.join(current_dir, 'poker_charts', 'headsup_SBRFI.json')
            with open(chart_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load SB RFI chart: {e}")
            return {}
    
    def hand_to_string(self, hand):
        """Convert hand array to standard poker notation (e.g., ['As', 'Kd'] -> 'AKo')"""
        card1, card2 = hand[0], hand[1]
        rank1, rank2 = card1[0], card2[0]
        suit1, suit2 = card1[1], card2[1]
        
        # Convert ranks to standard notation
        rank_order = {'A': 14, 'K': 13, 'Q': 12, 'J': 11, 'T': 10, '9': 9, '8': 8, '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2}
        val1, val2 = rank_order[rank1], rank_order[rank2]
        
        # Determine if suited
        suited = suit1 == suit2
        
        # Handle pairs
        if rank1 == rank2:
            return rank1 + rank1
        
        # Order by rank (higher first)
        if val1 > val2:
            high_rank, low_rank = rank1, rank2
        else:
            high_rank, low_rank = rank2, rank1
            
        # Add suited/offsuit designation
        if suited:
            return high_rank + low_rank + 's'
        else:
            return high_rank + low_rank + 'o'
        
    def decide_action(self, game_state):
        """
        Main decision function using game theory optimal (GTO) principles
        """
        ai_player = game_state['players'][1]
        hand = ai_player['hand']
        community = game_state['community']
        to_call = game_state.get('current_bet', 0) - ai_player['current_bet']
        pot = game_state['pot']
        betting_round = game_state['betting_round']
        
        # Stack-to-pot ratio for decision making
        effective_stack = min(ai_player['stack'], game_state['players'][0]['stack'])
        spr = effective_stack / max(pot, BIG_BLIND) if pot > 0 else effective_stack / BIG_BLIND
        
        if len(community) >= 3:
            return self.postflop_decision(hand, community, to_call, pot, ai_player, spr, betting_round)
        else:
            return self.preflop_decision(hand, to_call, pot, ai_player, spr, game_state)
    
    def preflop_decision(self, hand, to_call, pot, ai_player, spr, game_state):
        """
        Game Theory Optimal preflop strategy with SB RFI chart integration
        """
        # Check if this is SB first action (heads-up, no bet to call, preflop)
        if (to_call == 0 and 
            game_state['betting_round'] == 'preflop' and 
            len(game_state.get('action_history', [])) == 0):
            
            # Use SB RFI chart
            return self.sb_first_action(hand, ai_player)
        
        # Fall back to original preflop strategy for other situations
        hand_strength = self.evaluate_preflop_hand(hand)
        position_factor = 1.1  # AI is always in position in heads-up
        
        # Adjust strategy based on stack depth
        if spr < 10:  # Short stack play
            return self.short_stack_preflop(hand_strength, to_call, ai_player, pot)
        else:  # Deep stack play
            return self.deep_stack_preflop(hand_strength, to_call, ai_player, pot)
    
    def sb_first_action(self, hand, ai_player):
        """
        Small Blind first action using loaded chart
        """
        hand_string = self.hand_to_string(hand)
        
        # Get frequency from chart (default to 0.0 if hand not found)
        frequency = self.sb_rfi_chart.get(hand_string, 0.0)
        
        # Random decision based on frequency
        if random.random() < frequency:
            # Raise 2.3x BB, rounded up to nearest integer
            raise_size = int(BIG_BLIND * 2.3 + 0.5)  # Round up
            return ('raise', ai_player['current_bet'] + raise_size)
        else:
            # Fold (which becomes check in SB vs BB)
            return ('check', 0)
    
    def evaluate_preflop_hand(self, hand):
        """
        Advanced preflop hand evaluation using poker theory
        """
        card1, card2 = hand[0], hand[1]
        rank1, rank2 = card1[0], card2[0]
        suited = card1[1] == card2[1]
        
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, 
                      '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        val1, val2 = rank_values[rank1], rank_values[rank2]
        high_card, low_card = max(val1, val2), min(val1, val2)
        
        # Pocket pairs
        if rank1 == rank2:
            if val1 >= 10:  # TT+
                return 0.85
            elif val1 >= 7:  # 77-99
                return 0.70
            elif val1 >= 4:  # 44-66
                return 0.55
            else:  # 22-33
                return 0.45
        
        # Suited hands
        if suited:
            if high_card == 14:  # Ace suited
                if low_card >= 10:  # ATs+
                    return 0.80
                elif low_card >= 7:  # A7s-A9s
                    return 0.60
                else:  # A2s-A6s
                    return 0.50
            elif high_card == 13 and low_card >= 10:  # KQs, KJs, KTs
                return 0.75
            elif high_card == 12 and low_card >= 10:  # QJs, QTs
                return 0.65
            elif abs(high_card - low_card) <= 3 and low_card >= 6:  # Suited connectors
                return 0.55
            else:
                return 0.35
        
        # Offsuit hands
        else:
            if high_card == 14:  # Ace offsuit
                if low_card >= 11:  # AJ+
                    return 0.75
                elif low_card >= 9:  # AT, A9
                    return 0.55
                else:
                    return 0.40
            elif high_card == 13 and low_card >= 11:  # KQ, KJ
                return 0.65
            elif high_card >= 11 and low_card >= 10:  # QJ, JT type hands
                return 0.50
            else:
                return 0.30
    
    def short_stack_preflop(self, hand_strength, to_call, ai_player, pot):
        """
        Optimal short stack preflop strategy (push/fold)
        """
        if hand_strength >= 0.60:
            # Strong hands - always go all-in
            return ('raise', ai_player['stack'] + ai_player['current_bet'])
        elif hand_strength >= 0.45:
            if to_call == 0:
                return ('raise', ai_player['stack'] + ai_player['current_bet'])
            elif to_call <= ai_player['stack'] * 0.3:
                return ('call', 0)
            else:
                return ('fold', 0)
        else:
            if to_call == 0:
                return ('check', 0)
            else:
                return ('fold', 0)
    
    def deep_stack_preflop(self, hand_strength, to_call, ai_player, pot):
        """
        Optimal deep stack preflop strategy
        """
        if hand_strength >= 0.75:
            # Premium hands - always raise for value
            if to_call == 0:
                raise_size = max(BIG_BLIND * 3, pot * 0.8)
                return ('raise', ai_player['current_bet'] + min(raise_size, ai_player['stack']))
            else:
                # 3-bet with premium hands
                three_bet_size = to_call * 3
                if ai_player['stack'] >= three_bet_size:
                    return ('raise', ai_player['current_bet'] + to_call + three_bet_size)
                else:
                    return ('call', 0)
        
        elif hand_strength >= 0.55:
            # Good hands - mixed strategy
            if to_call == 0:
                if random.random() < 0.7:  # 70% raise, 30% check
                    raise_size = BIG_BLIND * 2.5
                    return ('raise', ai_player['current_bet'] + min(raise_size, ai_player['stack']))
                else:
                    return ('check', 0)
            else:
                if to_call <= BIG_BLIND * 3:
                    return ('call', 0)
                else:
                    return ('fold', 0)
        
        elif hand_strength >= 0.40:
            # Marginal hands
            if to_call == 0:
                return ('check', 0)
            elif to_call <= BIG_BLIND:
                return ('call', 0)
            else:
                return ('fold', 0)
        
        else:
            # Weak hands
            if to_call == 0:
                return ('check', 0)
            else:
                return ('fold', 0)
    
    def postflop_decision(self, hand, community, to_call, pot, ai_player, spr, betting_round):
        """
        Advanced postflop strategy using hand strength and board texture
        """
        try:
            score, hand_class = evaluate_hand(hand, community)
            hand_strength = self.calculate_hand_strength(score)
            board_texture = self.analyze_board_texture(community)
            
            # Adjust strategy based on board texture and betting round
            if betting_round == 'river':
                return self.river_strategy(hand_strength, to_call, pot, ai_player, board_texture)
            else:
                return self.flop_turn_strategy(hand_strength, to_call, pot, ai_player, board_texture, spr)
                
        except Exception:
            # Fallback to conservative play
            return self.conservative_postflop(to_call, pot, ai_player)
    
    def calculate_hand_strength(self, treys_score):
        """
        Convert treys score to normalized hand strength (0-1)
        """
        if treys_score <= 10:
            return 0.99  # Royal flush
        elif treys_score <= 166:
            return 0.95  # Straight flush
        elif treys_score <= 322:
            return 0.90  # Four of a kind
        elif treys_score <= 1599:
            return 0.85  # Full house
        elif treys_score <= 1609:
            return 0.80  # Flush
        elif treys_score <= 1609:
            return 0.75  # Straight
        elif treys_score <= 2467:
            return 0.65  # Three of a kind
        elif treys_score <= 3325:
            return 0.50  # Two pair
        elif treys_score <= 6185:
            return 0.35  # One pair
        else:
            return 0.15  # High card
    
    def analyze_board_texture(self, community):
        """
        Analyze board texture for strategic decisions
        """
        if len(community) < 3:
            return {'type': 'preflop'}
        
        ranks = [card[0] for card in community]
        suits = [card[1] for card in community]
        
        # Check for draws and textures
        flush_draw = max([suits.count(suit) for suit in suits]) >= 3
        straight_draw = self.has_straight_draw(ranks)
        paired_board = len(set(ranks)) < len(ranks)
        
        return {
            'type': 'postflop',
            'flush_draw': flush_draw,
            'straight_draw': straight_draw,
            'paired': paired_board,
            'wet': flush_draw or straight_draw,
            'dry': not (flush_draw or straight_draw or paired_board)
        }
    
    def has_straight_draw(self, ranks):
        """
        Check if board has straight draw potential
        """
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, 
                      '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        
        values = sorted([rank_values[rank] for rank in ranks])
        
        # Check for consecutive ranks or near-consecutive
        for i in range(len(values) - 1):
            if values[i+1] - values[i] == 1:
                return True
        return False
    
    def river_strategy(self, hand_strength, to_call, pot, ai_player, board_texture):
        """
        Optimal river play - value betting and bluff catching
        """
        if hand_strength >= self.value_bet_threshold:
            # Strong hands - bet for value
            if to_call == 0:
                bet_size = pot * 0.75  # Large value bet
                return ('raise', ai_player['current_bet'] + min(bet_size, ai_player['stack']))
            else:
                return ('call', 0)  # Call with strong hands
        
        elif hand_strength >= 0.45:
            # Medium strength - pot control
            if to_call == 0:
                return ('check', 0)
            elif to_call <= pot * 0.5:  # Call reasonable bets
                return ('call', 0)
            else:
                return ('fold', 0)
        
        else:
            # Weak hands - bluff or fold
            if to_call == 0:
                # Occasional bluff on dry boards
                if board_texture.get('dry', False) and random.random() < self.bluff_frequency:
                    bluff_size = pot * 0.8
                    return ('raise', ai_player['current_bet'] + min(bluff_size, ai_player['stack']))
                else:
                    return ('check', 0)
            else:
                return ('fold', 0)
    
    def flop_turn_strategy(self, hand_strength, to_call, pot, ai_player, board_texture, spr):
        """
        Flop and turn strategy with future streets in mind
        """
        if hand_strength >= 0.80:
            # Very strong hands - build pot
            if to_call == 0:
                bet_size = pot * 0.7
                return ('raise', ai_player['current_bet'] + min(bet_size, ai_player['stack']))
            else:
                return ('call', 0)
        
        elif hand_strength >= 0.60:
            # Strong hands - value bet smaller
            if to_call == 0:
                bet_size = pot * 0.5
                return ('raise', ai_player['current_bet'] + min(bet_size, ai_player['stack']))
            elif to_call <= pot * 0.6:
                return ('call', 0)
            else:
                return ('fold', 0)
        
        elif hand_strength >= 0.35:
            # Medium hands - pot control
            if to_call == 0:
                return ('check', 0)
            elif to_call <= pot * 0.4:
                return ('call', 0)
            else:
                return ('fold', 0)
        
        else:
            # Weak hands - check/fold with occasional bluffs
            if to_call == 0:
                if board_texture.get('wet', False) and random.random() < 0.15:
                    # Semi-bluff on wet boards
                    bet_size = pot * 0.6
                    return ('raise', ai_player['current_bet'] + min(bet_size, ai_player['stack']))
                else:
                    return ('check', 0)
            else:
                return ('fold', 0)
    
    def conservative_postflop(self, to_call, pot, ai_player):
        """
        Fallback conservative strategy
        """
        if to_call == 0:
            return ('check', 0)
        elif to_call <= pot * 0.3:
            return ('call', 0)
        else:
            return ('fold', 0)

# Create global optimized AI instance
optimized_ai = OptimizedHardcodedAI()

def decide_action_optimized(game_state):
    """
    Wrapper function for optimized hardcoded AI
    """
    return optimized_ai.decide_action(game_state)
