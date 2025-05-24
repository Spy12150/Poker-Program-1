import random
from .hand_eval_lib import evaluate_hand

"""
Poker Game Flow (Basic Logic)

1. Initialize hand:
    - Shuffle deck and assign dealer/button position.
    - Deal two hole cards to each player.
    - Post blinds (small and big blind).

2. Preflop betting round:
    - Begin with player left of big blind.
    - In turn, each active player can fold, call, or raise.
    - Betting continues until all bets are matched or only one player remains.

3. Flop:
    - Deal three community cards face up.
    - Start new betting round with first active player left of dealer.

4. Turn:
    - Deal one community card (the turn).
    - Start new betting round.

5. River:
    - Deal final community card (the river).
    - Start last betting round.

6. Showdown:
    - If more than one player remains after final betting:
        - Reveal all active players' hole cards.
        - Evaluate each player's best 5-card hand using their two hole cards plus five community cards.
        - Player(s) with the strongest hand(s) win the pot (split if tied).

7. Cleanup and prepare for next hand:
    - Award chips from pot to winner(s).
    - Rotate dealer/button and blinds.
    - Reset player statuses, bets, and game state.
    - Start next hand.

Note:
- If at any point all but one player folds, last remaining player wins the pot immediately.
- Side pots may be created if players go all-in for different amounts (optional in initial implementation).
"""


def create_deck():
    suits = ['s', 'h', 'd', 'c']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
    return [r + s for r in ranks for s in suits]

def deal_cards(deck, num_players=2):
    return [ [deck.pop(), deck.pop()] for _ in range(num_players) ]

def init_players(num_players=2, stack=1000):
    return [
        {"name": f"Player {i+1}", "hand": [], "stack": stack, "current_bet": 0, "status": "active"}
        for i in range(num_players)
    ]

def start_new_game(num_players=2, stack=1000):
    deck = create_deck()
    random.shuffle(deck)
    players = init_players(num_players, stack)
    hands = deal_cards(deck, num_players)
    for i, hand in enumerate(hands):
        players[i]['hand'] = hand

    return {
        "players": players,
        "deck": deck,
        "community": [],
        "pot": 0,
        "dealer_pos": 0,
        "current_player": (0 + 1) % num_players,  # big blind goes first after preflop
        "betting_round": "preflop"
    }

def deal_community_cards(game_state):
    # progress the game to the next betting round
    deck = game_state['deck']
    community = game_state['community']
    round = game_state['betting_round']

    if round == "preflop":
        community.extend([deck.pop() for _ in range(3)])
        game_state['betting_round'] = "flop"
    elif round == "flop":
        community.append(deck.pop())
        game_state['betting_round'] = "turn"
    elif round == "turn":
        community.append(deck.pop())
        game_state['betting_round'] = "river"
    # no cards on river (after river go to showdown)
    return game_state

def next_player(game_state):
    num_players = len(game_state['players'])
    i = game_state['current_player']
    for _ in range(num_players):
        i = (i + 1) % num_players
        if game_state['players'][i]['status'] == "active":
            game_state['current_player'] = i
            return

def apply_action(game_state, action, amount=0):
    """
    action: 'fold', 'call', 'raise', 'check'
    amount: only used for 'raise'
    """
    player = game_state['players'][game_state['current_player']]
    to_call = game_state.get('current_bet', 0) - player['current_bet']
    min_raise = max(game_state.get('current_bet', 0) * 2, 2)  # Example min raise, can adjust

    if action == 'fold':
        player['status'] = 'folded'
    elif action == 'call':
        call_amt = min(to_call, player['stack'])
        player['stack'] -= call_amt
        player['current_bet'] += call_amt
        game_state['pot'] += call_amt
        if player['stack'] == 0:
            player['status'] = 'all-in'
    elif action == 'raise':
        total_bet = amount
        raise_amt = total_bet - player['current_bet']
        if raise_amt < min_raise:
            raise_amt = min_raise  # enforce min raise
        to_pay = min(raise_amt, player['stack'])
        player['stack'] -= to_pay
        player['current_bet'] += to_pay
        game_state['pot'] += to_pay
        game_state['current_bet'] = player['current_bet']
        if player['stack'] == 0:
            player['status'] = 'all-in'
    elif action == 'check':
        if to_call != 0:
            raise ValueError("Cannot check when facing a bet")
    else:
        raise ValueError("Invalid action")

    # Move to next player (handled outside in your round controller)

def betting_round_over(game_state):
    """
    Betting round is over if:
    - All players but one are folded
    - All active players have matched the current bet or are all-in
    """
    active = [p for p in game_state['players'] if p['status'] == 'active']
    if len(active) <= 1:
        return True

    for player in active:
        if player['stack'] > 0 and player['current_bet'] != game_state.get('current_bet', 0):
            return False
    return True

def reset_bets(game_state):
    for player in game_state['players']:
        player['current_bet'] = 0
    game_state['current_bet'] = 0

def run_betting_round(game_state, action_sequence):
    """
    action_sequence: list of tuples (action, amount)
    For actual play, you’ll step this as each player acts.
    """
    for action, amount in action_sequence:
        apply_action(game_state, action, amount)
        if betting_round_over(game_state):
            break
        next_player(game_state)
    reset_bets(game_state)  # When moving to next street


def determine_winner(active_players, community):
    """
    Evaluates all active players' hands at showdown and returns the winner(s).
    Returns: a list of winning player(s) and their hand info.
    """
    scores = []
    for player in active_players:
        score, hand_class = evaluate_hand(player['hand'], community)
        scores.append((score, player['name'], hand_class))
    scores.sort()  # lowest score (best hand) first

    # Find all players with the best score (tie = split pot)
    best_score = scores[0][0]
    winners = [tup for tup in scores if tup[0] == best_score]

    return winners  # Each is (score, name, hand_class)

# More functions needed for: betting logic, showdown, winner determination, etc.
