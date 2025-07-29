"""
Test version to isolate import issue
"""

print("DEBUG: Starting test import module...")

try:
    import random
    import math
    import json
    import os
    print("DEBUG: Basic imports OK")
    
    from .hand_eval_lib import evaluate_hand
    from .config import BIG_BLIND, SMALL_BLIND
    print("DEBUG: Game imports OK")
    
    from .preflop_charts import PreflopCharts
    from .postflop_strategy import PostflopStrategy
    print("DEBUG: Strategy imports OK")
    
    class GTOEnhancedAI:
        def __init__(self):
            print("DEBUG: GTOEnhancedAI init...")
            self.preflop_charts = PreflopCharts()
            self.postflop_strategy = PostflopStrategy()
            print("DEBUG: GTOEnhancedAI init complete")
            
        def decide_action(self, game_state):
            return ('fold', 0)
    
    print("DEBUG: Class defined")
    
    gto_ai = None
    
    def decide_action_gto(game_state):
        global gto_ai
        if gto_ai is None:
            gto_ai = GTOEnhancedAI()
        return gto_ai.decide_action(game_state)
    
    print("DEBUG: Function defined")
    print("DEBUG: Test module loaded successfully!")
    
except Exception as e:
    print(f"DEBUG: Error during import: {e}")
    import traceback
    traceback.print_exc()
