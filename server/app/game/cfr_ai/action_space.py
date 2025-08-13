"""
Unified action space and mappings used across CFR modules

- Preflop sizes are in big blinds (BB)
- Postflop sizes are fractions of the pot
- 'allin' represents shoving remaining stack
"""

from typing import Dict, List

# Canonical ordered action list used by neural networks and trainers
# Note: Legality/availability depends on street and whether facing a bet
ACTION_LIST: List[str] = [
    'fold',
    'check',
    'call',
    # Preflop first-in (SB): raise 2.5x BB
    'raise_2.5',
    # Preflop vs raise: raise to 3x or 5x opponent bet
    'raise_3.0',
    'raise_5.0',
    # Postflop first-in: 35%, 70%, 110% pot
    'raise_0.35',
    'raise_0.7',
    'raise_1.1',
    # Postflop vs raise: raise to 2.3x or 3.5x opponent bet
    'raise_2.3',
    'raise_3.5',
]

# Mapping from action string to index
ACTION_MAP: Dict[str, int] = {a: i for i, a in enumerate(ACTION_LIST)}

# Reverse mapping for convenience
INDEX_TO_ACTION: Dict[int, str] = {i: a for a, i in ACTION_MAP.items()}