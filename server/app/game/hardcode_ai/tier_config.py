"""
I now use a 11 bucket approach for freflop, where tier_config generates the buckets

This is so I can have more fine control over each step of the way, 
now I can control about 9% of the hands each adjustment

However there is flaws, different cards are different strength in diff scnearios
So there is still flaw and this might be exploitable

but apart from me going in and individually copying gto wizard charts for each pre flop scenario,
This is a more efficient way

Current config:
[T0]: AA, AKo, AKs, AQs, JJ, KK, QQ
[T1]: 99, A3s, A4s, A5s, A6s, A7s, A8s, A9s, AJs, AQo, ATs, JTs, KJs, KQs, QJs, QTs, TT
[T2]: 77, 88, 98s, A2s, A6o, A7o, A8o, A9o, AJo, ATo, J9s, K6s, K7s, K8s, K9s, KQo, KTs, Q9s, T9s
[T3]: 44, 55, 66, 87s, A2o, A3o, A4o, A5o, J8s, K2s, K3s, K4s, K5s, KJo, KTo, Q6s, Q7s, Q8s, QJo, T8s
[T4]: 22, 33, 76s, 97s, J5s, J6s, J7s, JTo, K5o, K6o, K7o, K8o, K9o, Q2s, Q3s, Q4s, Q5s, Q9o, QTo
[T5]: 65s, 86s, J2s, J3s, J4s, J8o, J9o, K2o, K3o, K4o, Q6o, Q7o, Q8o, T6s, T7s
[T6]: 54s, 75s, 96s, J6o, J7o, Q2o, Q3o, Q4o, Q5o, T2s, T3s, T4s, T5s, T8o, T9o
[T7]: 43s, 64s, 84s, 85s, 92s, 93s, 94s, 95s, 97o, 98o, J2o, J3o, J4o, J5o, T6o, T7o
[T8]: 32s, 53s, 73s, 74s, 82s, 83s, 86o, 87o, 95o, 96o, T2o, T3o, T4o, T5o
[T9]: 42s, 52s, 62s, 63s, 72s, 75o, 76o, 82o, 83o, 84o, 85o, 92o, 93o, 94o
[T10]: 32o, 42o, 43o, 52o, 53o, 54o, 62o, 63o, 64o, 65o, 72o, 73o, 74o
"""
from typing import List, Tuple, Dict

# Rank helpers ------------------------------------------------------------
RANK_TO_INT = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
               "8": 8, "9": 9, "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14}
INT_TO_RANK = {v: k for k, v in RANK_TO_INT.items()}


# Utility to build tuple representation

def hand_class_tuple(hi: int, lo: int, suited: bool = False) -> Tuple:
    if hi == lo:
        return (hi, hi)
    return (hi, lo, suited)


# Strength heuristic ------------------------------------------------------

def _strength_score(t: Tuple) -> int:
    # Pairs ---------------------------------------------------------------
    if len(t) == 2:
        rank = t[0]
        penalty = (9 - rank) * 80 if rank < 9 else 0
        return 300 + 25 * rank - penalty

    hi, lo, suited = t  # type: ignore[misc]
    gap = hi - lo

    score = hi * 20 + lo  # base high-card weight
    connected_bonus = max(0, 5 - gap) * 10
    score += connected_bonus

    if hi == 14:
        score += 30
    elif hi >= 11:
        score += 10

    if suited:
        score += 40
        if gap == 1:
            score += 60  # suited connector
        elif gap == 2:
            score += 30  # one-gap

    if hi <= 7 and lo <= 5 and not suited:
        score -= 20
    return score


# Build tiers -------------------------------------------------------------
COMBOS_PER_PAIR = 6
COMBOS_SUITED = 4
COMBOS_OFFSUIT = 12

all_classes: List[Tuple] = []
for hi in range(14, 1, -1):
    for lo in range(hi, 1, -1):
        if hi == lo:
            all_classes.append(((hi, hi), COMBOS_PER_PAIR))
        else:
            all_classes.append(((hi, lo, True), COMBOS_SUITED))
            all_classes.append(((hi, lo, False), COMBOS_OFFSUIT))

all_classes.sort(key=lambda x: _strength_score(x[0]), reverse=True)
TOTAL_COMBOS = 1326
TARGET = TOTAL_COMBOS // 10

TIERS: List[List[Tuple]] = [[] for _ in range(10)]
idx = 0
running = 0
for cl, combos in all_classes:
    if running + combos > TARGET and idx < 9:
        idx += 1
        running = 0
    TIERS[idx].append(cl)
    running += combos

# Insert elite tier 0 -----------------------------------------------------
ELITE = [
    (14, 14), (13, 13), (12, 12), (11, 11),
    (14, 13, False), (14, 13, True), (14, 12, True),
]
for h in ELITE:
    # remove from current tier
    for t in TIERS:
        if h in t:
            t.remove(h)
            break
TIERS.insert(0, ELITE)

# Pair tier overrides -----------------------------------------------------
_pair_override = {2: 4, 3: 4, 4: 3, 5: 3, 6: 3, 7: 2, 8: 2}
for rank, tier in _pair_override.items():
    pair = (rank, rank)
    # remove from wherever they are
    for t in TIERS:
        if pair in t:
            t.remove(pair)
            break
    TIERS[tier].append(pair)

# Build lookup ------------------------------------------------------------
class_lookup: Dict[Tuple, int] = {}
for tier_idx, tier in enumerate(TIERS):
    for cl in tier:
        class_lookup[cl] = tier_idx
