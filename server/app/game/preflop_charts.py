"""
Advanced Preflop Charts for Poker AI

Implements comprehensive preflop strategy charts based on:
- Position (Button vs Big Blind in heads-up)
- Stack depth
- Action facing (unopened pot vs facing a raise)
- 3-bet and 4-bet scenarios
"""

import random

class PreflopCharts:
    def __init__(self):
        # Hands are represented as tuples: (high_rank, low_rank, suited)
        # Ranks: A=14, K=13, Q=12, J=11, T=10, 9=9, etc.
        
        # Button Opening Range (heads-up button opens ~45% of hands)
        self.button_opening_range = {
            # Premium hands (always raise)
            'premium': [
                (14, 14), (13, 13), (12, 12), (11, 11), (10, 10), (9, 9), (8, 8), (7, 7),  # Pairs
                (14, 13, True), (14, 13, False),  # AK
                (14, 12, True), (14, 12, False),  # AQ
                (14, 11, True), (13, 12, True),   # AJ, KQ suited
            ],
            
            # Strong hands (raise most of the time)
            'strong': [
                (6, 6), (5, 5), (4, 4), (3, 3), (2, 2),  # Small pairs
                (14, 10, True), (14, 9, True), (14, 8, True), (14, 7, True),  # Suited aces
                (13, 11, True), (13, 10, True), (12, 11, True), (12, 10, True),  # Suited broadway
                (14, 11, False), (14, 10, False),  # AJ, AT offsuit
                (13, 12, False), (13, 11, False),  # KQ, KJ offsuit
            ],
            
            # Playable hands (mixed strategy - position dependent)
            'playable': [
                (14, 6, True), (14, 5, True), (14, 4, True), (14, 3, True), (14, 2, True),  # Suited aces
                (13, 9, True), (13, 8, True), (12, 9, True), (11, 10, True), (11, 9, True),  # Suited connectors/gappers
                (10, 9, True), (9, 8, True), (8, 7, True), (7, 6, True), (6, 5, True), (5, 4, True),  # Suited connectors
                (14, 9, False), (14, 8, False), (13, 10, False), (12, 11, False),  # Offsuit broadway
                (10, 9, False), (9, 8, False),  # Offsuit connectors
            ]
        }
        
        # Big Blind Defense Range vs Button Open (defend ~65% vs standard raise)
        self.bb_defense_range = {
            'call': [
                # All pairs
                (14, 14), (13, 13), (12, 12), (11, 11), (10, 10), (9, 9), (8, 8), (7, 7), (6, 6), (5, 5), (4, 4), (3, 3), (2, 2),
                # Suited hands
                (14, 13, True), (14, 12, True), (14, 11, True), (14, 10, True), (14, 9, True), (14, 8, True), (14, 7, True), (14, 6, True), (14, 5, True), (14, 4, True), (14, 3, True), (14, 2, True),
                (13, 12, True), (13, 11, True), (13, 10, True), (13, 9, True), (13, 8, True), (13, 7, True),
                (12, 11, True), (12, 10, True), (12, 9, True), (12, 8, True),
                (11, 10, True), (11, 9, True), (11, 8, True), (10, 9, True), (10, 8, True), (9, 8, True), (9, 7, True), (8, 7, True), (7, 6, True), (6, 5, True), (5, 4, True),
                # Offsuit hands
                (14, 13, False), (14, 12, False), (14, 11, False), (14, 10, False), (14, 9, False), (14, 8, False), (14, 7, False),
                (13, 12, False), (13, 11, False), (13, 10, False), (12, 11, False), (11, 10, False),
            ],
            
            '3bet': [
                # Premium 3-bet hands
                (14, 14), (13, 13), (12, 12), (11, 11), (10, 10),  # Top pairs
                (14, 13, True), (14, 13, False),  # AK
                (14, 12, True),  # AQ suited
                # Bluff 3-bets (polarized strategy)
                (14, 5, True), (14, 4, True), (14, 3, True), (14, 2, True),  # Suited wheel aces
                (13, 6, True), (13, 5, True), (12, 7, True), (11, 8, True),  # Suited connectors/gappers
            ]
        }
        
        # 4-bet ranges (very tight, polarized)
        self.four_bet_range = {
            'value': [(14, 14), (13, 13), (12, 12), (14, 13, True), (14, 13, False)],
            'bluff': [(14, 5, True), (14, 4, True), (13, 5, True)]
        }
    
    def get_hand_tuple(self, hand):
        """Convert hand to comparable tuple format"""
        card1, card2 = hand[0], hand[1]
        rank1, rank2 = card1[0], card2[0]
        suited = card1[1] == card2[1]
        
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, 
                      '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        val1, val2 = rank_values[rank1], rank_values[rank2]
        
        if val1 == val2:  # Pair
            return (val1, val1)
        elif suited:
            return (max(val1, val2), min(val1, val2), True)
        else:
            return (max(val1, val2), min(val1, val2), False)
    
    def should_open_button(self, hand, stack_bb=100):
        """Determine if hand should be opened from button"""
        hand_tuple = self.get_hand_tuple(hand)
        
        # Stack depth adjustments
        if stack_bb < 20:  # Short stack - tighter range
            return hand_tuple in self.button_opening_range['premium']
        elif stack_bb < 50:  # Medium stack
            return (hand_tuple in self.button_opening_range['premium'] or 
                   hand_tuple in self.button_opening_range['strong'])
        else:  # Deep stack - full range
            return (hand_tuple in self.button_opening_range['premium'] or 
                   hand_tuple in self.button_opening_range['strong'] or 
                   hand_tuple in self.button_opening_range['playable'])
    
    def should_defend_bb(self, hand, raise_size_bb=3, stack_bb=100):
        """Determine BB defense strategy vs button open"""
        hand_tuple = self.get_hand_tuple(hand)
        
        # Adjust defense range based on raise size
        if raise_size_bb > 4:  # Large raise - tighter defense
            return hand_tuple in self.bb_defense_range['3bet']
        
        # Stack depth adjustments
        if stack_bb < 20:  # Short stack - more calling, less 3-betting
            return hand_tuple in self.bb_defense_range['call'][:50]  # Top 50 hands
        
        # Normal defense
        if hand_tuple in self.bb_defense_range['3bet']:
            return '3bet'
        elif hand_tuple in self.bb_defense_range['call']:
            return 'call'
        else:
            return 'fold'
    
    def get_preflop_action(self, hand, position, action_to_hero, raise_size_bb=0, stack_bb=100):
        """
        Comprehensive preflop decision making
        
        Args:
            hand: Player's hole cards
            position: 'button' or 'bb' (heads-up)
            action_to_hero: 'none' (unopened), 'raise', '3bet', '4bet'
            raise_size_bb: Size of raise in big blinds
            stack_bb: Effective stack in big blinds
        """
        hand_tuple = self.get_hand_tuple(hand)
        
        if position == 'button':
            if action_to_hero == 'none':
                # Unopened pot
                if self.should_open_button(hand, stack_bb):
                    return 'raise'
                else:
                    return 'fold'  # Actually 'check' in implementation
            
            elif action_to_hero == '3bet':
                # Facing BB 3-bet
                if hand_tuple in self.four_bet_range['value']:
                    return '4bet_value'
                elif hand_tuple in self.four_bet_range['bluff'] and stack_bb > 50:
                    return '4bet_bluff' if random.random() < 0.3 else 'fold'
                elif hand_tuple in self.button_opening_range['premium'][:10]:  # Top hands
                    return 'call'
                else:
                    return 'fold'
        
        else:  # Big Blind
            if action_to_hero == 'raise':
                # Facing button open
                defense = self.should_defend_bb(hand, raise_size_bb, stack_bb)
                return defense if defense != 'fold' else 'fold'
            
            elif action_to_hero == '4bet':
                # Facing button 4-bet (after our 3-bet)
                if hand_tuple in [(14, 14), (13, 13), (14, 13, True)]:  # Only the nuts
                    return 'call'  # or '5bet' with AA/KK
                else:
                    return 'fold'
        
        return 'fold'
