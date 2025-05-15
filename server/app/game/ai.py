import random

def decide_action(game_state):
    """
    Very basic AI that randomly chooses an action.
    Later, you can upgrade this to use hand strength, CFR, etc.
    """
    round = game_state.get("round", "preflop")
    pot = game_state.get("pot", 0)
    ai_stack = game_state.get("ai_stack", 1000)

    # Random for now; smarter logic later
    if round == "preflop":
        return random.choice(["call", "raise"])
    elif round in ["flop", "turn", "river"]:
        return random.choice(["check", "call", "raise", "fold"])
    else:
        return "check"

