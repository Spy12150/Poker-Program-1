import random

def decide_action(game_state):
    """
    Simple random AI for debugging purposes.
    Returns: (action, amount) tuple
    """
    print("🐸 FROGGIE AI IS MAKING A DECISION! 🐸")
    ai_player = game_state['players'][1]  # AI is player 1
    to_call = game_state.get('current_bet', 0) - ai_player['current_bet']
    
    # Debug print
    print(f"AI deciding action: current_bet={game_state.get('current_bet', 0)}, ai_current_bet={ai_player['current_bet']}, to_call={to_call}, ai_stack={ai_player['stack']}")
    
    # If no chips left, can only check/call if possible
    if ai_player['stack'] == 0:
        action = 'check' if to_call == 0 else 'call'
        return debug_action(action, 0)
    
    # Random action selection
    if to_call == 0:
        # Can check or bet/raise
        action = random.choice(['check', 'raise'])
        if action == 'check':
            return debug_action('check', 0)
        else:
            # Calculate raise amount properly
            big_blind = 10  # From config
            min_raise = big_blind  # Minimum first bet
            max_raise = ai_player['current_bet'] + ai_player['stack']  # All-in
            
            if max_raise > min_raise:
                reasonable_max = min(max_raise, min_raise + 100)
                raise_amount = random.randint(min_raise, reasonable_max)
                return debug_action('raise', raise_amount)
            else:
                return debug_action('check', 0)  # Can't raise, just check
    else:
        # Must call, raise, or fold
        # 60% call, 20% raise, 20% fold
        action = random.choices(['call', 'raise', 'fold'], weights=[60, 20, 20])[0]
        
        if action == 'fold':
            return debug_action('fold', 0)
        elif action == 'call':
            return debug_action('call', 0)
        else:  # raise
            if ai_player['stack'] > to_call:
                # Calculate total raise amount (not additional raise)
                current_bet = game_state.get('current_bet', 0)
                min_raise = current_bet * 2  # Minimum raise is double current bet
                max_raise = ai_player['current_bet'] + ai_player['stack']  # All-in amount
                
                if max_raise > min_raise:
                    # Random raise between min raise and reasonable amount
                    reasonable_max = min(max_raise, current_bet + 100)
                    raise_amount = random.randint(min_raise, reasonable_max)
                    return debug_action('raise', raise_amount)
            # Fall back to call if can't raise
            return debug_action('call', 0)

# Add debug print at the end of functions
def debug_action(action, amount):
    print(f"AI chose action: {action}, amount: {amount}")
    return (action, amount)

