"""
Minimal GTO AI for testing imports
"""

print("DEBUG: Loading minimal GTO AI...")

class GTOEnhancedAI:
    def __init__(self):
        print("DEBUG: Creating minimal GTO AI...")
        
    def decide_action(self, game_state):
        return ('fold', 0)

# Create deferred instance
gto_ai = None

def decide_action_gto(game_state):
    global gto_ai
    if gto_ai is None:
        gto_ai = GTOEnhancedAI()
    return gto_ai.decide_action(game_state)

print("DEBUG: Minimal GTO AI module loaded successfully!")
