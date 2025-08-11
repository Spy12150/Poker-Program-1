"""
Unified action space and mappings used across CFR modules

- Preflop sizes are in big blinds (BB)
- Postflop sizes are fractions of the pot
- 'allin' represents shoving remaining stack
"""

from typing import Dict, List

# Canonical ordered action list used by neural networks and trainers
ACTION_LIST: List[str] = [
    'fold',
    'check',
    'call',
    # Preflop raise sizes 
    'raise_1.0',
    'raise_3.0',
    'raise_5.0',
    # postflop raise sizes
    'raise_0.35',
    'raise_0.7',
    'raise_1.1',
    'allin',
]

# Mapping from action string to index
ACTION_MAP: Dict[str, int] = {a: i for i, a in enumerate(ACTION_LIST)}

# Reverse mapping for convenience
INDEX_TO_ACTION: Dict[int, str] = {i: a for a, i in ACTION_MAP.items()}