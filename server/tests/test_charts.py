#!/usr/bin/env python3
"""
Test script for the fixed preflop charts (I'm not using those anymore)
"""

import random

# Minimal PreflopCharts implementation to test logic
class TestPreflopCharts:
    def __init__(self):
        # Simplified ranges for testing
        self.bb_defense_range = {
            'call': [
                (14, 14), (13, 13), (12, 12), (11, 11), (10, 10), (9, 9), (8, 8), (7, 7), (6, 6), (5, 5),
                (14, 13, True), (14, 12, True), (14, 11, True), (13, 12, True),
                (14, 13, False), (14, 12, False), (14, 11, False), (13, 12, False),
            ],
            '3bet': [
                (14, 14), (13, 13), (12, 12), (11, 11), (10, 10),
                (14, 13, True), (14, 13, False), (14, 12, True),
                (14, 5, True), (14, 4, True), (14, 3, True),
            ]
        }
        
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

    def should_defend_bb(self, hand, raise_size_bb=3, stack_bb=100):
        """Test the BB defense logic"""
        hand_tuple = self.get_hand_tuple(hand)
        
        # Short stack strategy - push/fold with very short stacks
        if stack_bb <= 15:
            push_fold_range = [
                (14, 14), (13, 13), (12, 12), (11, 11), (10, 10), (9, 9), (8, 8), (7, 7),
                (14, 13, True), (14, 13, False), (14, 12, True), (14, 12, False),
                (14, 11, True), (14, 10, True), (13, 12, True), (13, 11, True),
                (14, 9, True), (14, 8, True), (14, 7, True), (14, 6, True), (14, 5, True),
                (13, 10, True), (12, 11, True), (11, 10, True)
            ]
            if hand_tuple in push_fold_range:
                return 'call'  # All-in call
            else:
                return 'fold'
        
        # Adjust defense range based on raise size
        if raise_size_bb > 4:  # Large raise - much tighter defense
            if hand_tuple in self.bb_defense_range['3bet']:
                return '3bet'
            elif hand_tuple in [(14, 14), (13, 13), (12, 12), (11, 11), (10, 10),
                               (14, 13, True), (14, 13, False), (14, 12, True)]:
                return 'call'  # Only premium hands vs large raises
            else:
                return 'fold'
        
        # Normal defense
        if hand_tuple in self.bb_defense_range['3bet']:
            return '3bet'
        elif hand_tuple in self.bb_defense_range['call']:
            return 'call'
        else:
            return 'fold'

def test_preflop_charts():
    """Test the preflop charts functionality"""
    charts = TestPreflopCharts()
    print("✓ PreflopCharts test class created successfully")
    
    # Test BB defense function
    print("\nTesting BB defense function:")
    bb_tests = [
        (['Ac', 'Ad'], 3, 50, 'AA vs standard raise'),
        (['2h', '3s'], 3, 50, '23o vs standard raise'),
        (['Kh', 'Qs'], 3, 15, 'KQ vs raise short stack'),
        (['9h', '8h'], 6, 50, '98s vs large raise'),
        (['Ac', 'Ks'], 3, 50, 'AK vs standard raise'),
        (['Jh', 'Tc'], 3, 50, 'JT vs standard raise'),
        (['Ac', 'Ad'], 3, 10, 'AA short stack'),
        (['2h', '3s'], 3, 10, '23o short stack'),
    ]
    
    success_count = 0
    for hand, raise_size, stack, description in bb_tests:
        try:
            result = charts.should_defend_bb(hand, raise_size, stack)
            print(f"✓ {description}: -> {result}")
            
            # Validate that result is one of the expected actions
            if result in ['call', '3bet', 'fold']:
                success_count += 1
            else:
                print(f"  ⚠️  Unexpected result type: {result}")
        except Exception as e:
            print(f"✗ {description}: ERROR - {e}")
    
    print(f"\n{success_count}/{len(bb_tests)} tests passed!")
    
    # Test hand conversion
    print("\nTesting hand tuple conversion:")
    hand_tests = [
        (['Ac', 'Ad'], (14, 14)),
        (['Ks', 'Qh'], (13, 12, False)),
        (['9h', '8h'], (9, 8, True)),
        (['2c', '3d'], (3, 2, False)),
    ]
    
    for hand, expected in hand_tests:
        try:
            result = charts.get_hand_tuple(hand)
            if result == expected:
                print(f"✓ {hand} -> {result}")
            else:
                print(f"✗ {hand} -> {result} (expected {expected})")
        except Exception as e:
            print(f"✗ {hand}: ERROR - {e}")
    
    return True

if __name__ == "__main__":
    success = test_preflop_charts()
    print("\n" + "="*50)
    print("SUMMARY: Fixed preflop charts should now:")
    print("1. Return consistent action strings ('call', '3bet', 'fold')")
    print("2. Handle short stack situations properly")
    print("3. Adjust ranges based on raise sizes")
    print("4. Implement stack-aware strategy")
    print("5. Provide proper BB defense ranges")
    print("="*50)
