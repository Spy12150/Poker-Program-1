import random

def decide_action(game_state):
    """
    Simple random AI for debugging purposes.
    Returns: (action, amount) tuple
    """
    ai_player = game_state['players'][1]  # AI is player 1
    to_call = game_state.get('current_bet', 0) - ai_player['current_bet']
    
    # If no chips left, can only check/call if possible
    if ai_player['stack'] == 0:
        return ('check' if to_call == 0 else 'call', 0)
    
    # Random action selection
    if to_call == 0:
        # Can check or bet/raise
        action = random.choice(['check', 'raise'])
        if action == 'check':
            return ('check', 0)
        else:
            # Random raise amount between 20 and min(stack/2, 100)
            max_raise = min(ai_player['stack'], 100)
            raise_amount = random.randint(20, max(20, max_raise))
            return ('raise', ai_player['current_bet'] + raise_amount)
    else:
        # Must call, raise, or fold
        # 60% call, 20% raise, 20% fold
        action = random.choices(['call', 'raise', 'fold'], weights=[60, 20, 20])[0]
        
        if action == 'fold':
            return ('fold', 0)
        elif action == 'call':
            return ('call', 0)
        else:  # raise
            if ai_player['stack'] > to_call:
                # Random raise amount
                available_for_raise = ai_player['stack'] - to_call
                max_raise = min(available_for_raise, 100)
                if max_raise > 0:
                    raise_amount = random.randint(20, max(20, max_raise))
                    return ('raise', ai_player['current_bet'] + to_call + raise_amount)
            # Fall back to call if can't raise
            return ('call', 0)

