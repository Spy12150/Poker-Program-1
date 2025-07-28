import random
from .hand_eval_lib import evaluate_hand

def decide_action(game_state):
    """
    Enhanced AI that considers hand strength, pot odds, and position.
    Returns: (action, amount) tuple
    """
    ai_player = game_state['players'][1]  # AI is player 1
    hand = ai_player['hand']
    community = game_state['community']
    to_call = game_state.get('current_bet', 0) - ai_player['current_bet']
    pot = game_state['pot']
    betting_round = game_state['betting_round']
    
    # If no chips left, can only check/call if possible
    if ai_player['stack'] == 0:
        return ('check' if to_call == 0 else 'call', 0)
    
    # Calculate hand strength if we have community cards
    if len(community) >= 3:
        try:
            score, hand_class = evaluate_hand(hand, community)
            hand_strength = get_hand_strength_category(score)
            
            if hand_strength == 'very_strong':
                # Always bet/raise with very strong hands
                if to_call == 0:
                    raise_amount = min(ai_player['stack'], max(pot // 2, game_state['current_bet'] * 2))
                    return ('raise', ai_player['current_bet'] + raise_amount)
                else:
                    # Raise if we can, otherwise call
                    if ai_player['stack'] > to_call:
                        raise_amount = min(ai_player['stack'] - to_call, pot)
                        return ('raise', ai_player['current_bet'] + to_call + raise_amount)
                    else:
                        return ('call', 0)
            
            elif hand_strength == 'strong':
                # Bet for value or call reasonable bets
                if to_call == 0:
                    bet_amount = min(ai_player['stack'], pot // 3)
                    if bet_amount > 0:
                        return ('raise', ai_player['current_bet'] + bet_amount)
                    else:
                        return ('check', 0)
                elif to_call <= pot * 0.4:  # Good pot odds
                    return ('call', 0)
                else:
                    return ('fold', 0)
            
            elif hand_strength == 'medium':
                # Play cautiously
                if to_call == 0:
                    return ('check', 0)
                elif to_call <= pot * 0.25:  # Only call small bets
                    return ('call', 0)
                else:
                    return ('fold', 0)
            
            else:  # weak hand
                if to_call == 0:
                    return ('check', 0)
                else:
                    return ('fold', 0)
                    
        except Exception:
            # If hand evaluation fails, play conservatively
            return conservative_play(to_call, pot, ai_player)
    
    else:
        # Preflop strategy
        return preflop_strategy(hand, to_call, pot, ai_player, betting_round)

def get_hand_strength_category(score):
    """Convert treys score to strength category"""
    if score <= 1000:  # Very strong (straight flush, quads, full house, flush)
        return 'very_strong'
    elif score <= 2500:  # Strong (straight, trips, two pair)
        return 'strong' 
    elif score <= 4000:  # Medium (pair)
        return 'medium'
    else:  # Weak (high card)
        return 'weak'

def preflop_strategy(hand, to_call, pot, ai_player, betting_round):
    """Simple preflop strategy based on hole cards"""
    card1, card2 = hand[0], hand[1]
    rank1, rank2 = card1[0], card2[0]
    suited = card1[1] == card2[1]
    
    # Convert face cards to numbers for comparison
    rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, 
                   '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
    val1, val2 = rank_values[rank1], rank_values[rank2]
    
    # Pocket pairs
    if rank1 == rank2:
        if val1 >= 10:  # High pairs (TT+)
            return aggressive_play(to_call, pot, ai_player)
        elif val1 >= 7:  # Medium pairs (77-99)
            return moderate_play(to_call, pot, ai_player)
        else:  # Low pairs (22-66)
            return conservative_play(to_call, pot, ai_player)
    
    # High cards
    high_card_threshold = 11  # Jack or higher
    if val1 >= high_card_threshold or val2 >= high_card_threshold:
        if suited and abs(val1 - val2) <= 4:  # Suited connectors/gappers
            return moderate_play(to_call, pot, ai_player)
        elif val1 >= 13 or val2 >= 13:  # King or Ace
            return moderate_play(to_call, pot, ai_player)
        else:
            return conservative_play(to_call, pot, ai_player)
    
    # Suited connectors
    if suited and abs(val1 - val2) <= 2 and min(val1, val2) >= 6:
        return conservative_play(to_call, pot, ai_player)
    
    # Weak hands
    return weak_hand_play(to_call, ai_player)

def aggressive_play(to_call, pot, ai_player):
    """Aggressive betting strategy"""
    if to_call == 0:
        raise_amount = min(ai_player['stack'], max(pot // 2, 40))  # Decent raise
        return ('raise', ai_player['current_bet'] + raise_amount)
    elif to_call <= ai_player['stack']:
        return ('call', 0)
    else:
        return ('call', 0)  # All-in call

def moderate_play(to_call, pot, ai_player):
    """Moderate betting strategy"""
    if to_call == 0:
        if random.random() < 0.3:  # Sometimes bet
            bet_amount = min(ai_player['stack'], pot // 3)
            if bet_amount > 0:
                return ('raise', ai_player['current_bet'] + bet_amount)
        return ('check', 0)
    elif to_call <= pot * 0.3:  # Call reasonable bets
        return ('call', 0)
    else:
        return ('fold', 0)

def conservative_play(to_call, pot, ai_player):
    """Conservative betting strategy"""
    if to_call == 0:
        return ('check', 0)
    elif to_call <= pot * 0.2:  # Only call small bets
        return ('call', 0)
    else:
        return ('fold', 0)

def weak_hand_play(to_call, ai_player):
    """Strategy for weak hands"""
    if to_call == 0:
        return ('check', 0)
    else:
        return ('fold', 0)

