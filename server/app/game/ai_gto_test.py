"""
Minimal test version of GTO AI to debug import issues
"""

class GTOEnhancedAI:
    def __init__(self):
        print("Creating GTO AI instance...")
        
    def decide_action(self, game_state):
        return ('fold', 0)

# Create global instance
gto_ai = GTOEnhancedAI()

def decide_action_gto(game_state):
    """Wrapper function for GTO-enhanced AI"""
    return gto_ai.decide_action(game_state)

print("GTO test module loaded successfully")
