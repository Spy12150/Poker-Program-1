#!/usr/bin/env python3
"""
Simple test script for hand conversion logic
"""

def hand_to_string(hand):
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

# Test cases
test_hands = [
    (['As', 'Kd'], 'AKo'),
    (['Ah', 'Ks'], 'AKs'),  # Different suits = offsuit
    (['Qc', 'Qd'], 'QQ'),
    (['7h', '2s'], '72o'),  # Fixed expected result
    (['Ts', '9s'], 'T9s'),
    (['2c', '7d'], '72o')
]

print("Testing hand conversion:")
for hand, expected in test_hands:
    result = hand_to_string(hand)
    status = "✓" if result == expected else "✗"
    card1, card2 = hand[0], hand[1]
    suited = card1[1] == card2[1]
    print(f"{status} {hand} -> {result} (expected: {expected}) [suited: {suited}]")
