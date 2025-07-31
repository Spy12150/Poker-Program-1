#!/usr/bin/env python3
"""
Test file to display all hand tiers from tier_config.py
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'server', 'app', 'game'))

from hardcode_ai.tier_config import TIERS, INT_TO_RANK

def tuple_to_hand_string(hand_tuple):
    """Convert hand tuple to readable string like 'AA', 'AKs', 'AKo'"""
    if len(hand_tuple) == 2:  # Pair
        rank = INT_TO_RANK[hand_tuple[0]]
        return f"{rank}{rank}"
    else:  # Non-pair
        hi, lo, suited = hand_tuple
        hi_rank = INT_TO_RANK[hi]
        lo_rank = INT_TO_RANK[lo]
        suffix = "s" if suited else "o"
        return f"{hi_rank}{lo_rank}{suffix}"

def print_all_tiers():
    """Print all hand tiers in simple format"""
    for tier_num in range(len(TIERS)):
        tier_hands = TIERS[tier_num]
        
        # Convert tuples to readable strings
        hand_strings = [tuple_to_hand_string(hand_tuple) for hand_tuple in tier_hands]
        hand_strings.sort()
        
        # Print in format: [T0]: AA, KK, QQ, ...
        hands_str = ", ".join(hand_strings)
        print(f"[T{tier_num}]: {hands_str}")

def print_tier_examples():
    """Not used in simple format"""
    pass

if __name__ == "__main__":
    print_all_tiers()