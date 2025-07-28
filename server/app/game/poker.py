import random
from .hand_eval_lib import evaluate_hand
from .config import NUM_PLAYERS, STARTING_STACK, SMALL_BLIND, BIG_BLIND, ANTE

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

def deal_cards(deck, num_players=NUM_PLAYERS):
    return [[deck.pop(), deck.pop()] for _ in range(num_players)]

def init_players(num_players=NUM_PLAYERS, stack=STARTING_STACK):
    return [
        {"name": f"Player {i+1}", "hand": [], "stack": stack, "current_bet": 0, "status": "active"}
        for i in range(num_players)
    ]

def start_new_game():
    deck = create_deck()
    random.shuffle(deck)
    players = init_players()
    hands = deal_cards(deck, NUM_PLAYERS)
    for i, hand in enumerate(hands):
        players[i]['hand'] = hand

    game_state = {
        "players": players,
        "deck": deck,
        "community": [],
        "pot": 0,
        "dealer_pos": 0,
        "current_player": (0 + 1) % NUM_PLAYERS,
        "betting_round": "preflop",
        "current_bet": 0,
    }

    apply_antes(game_state)
    post_blinds(game_state)
    return game_state

def apply_antes(game_state):
    if ANTE > 0:
        for player in game_state['players']:
            if player['status'] == "active" and player['stack'] >= ANTE:
                player['stack'] -= ANTE
                game_state['pot'] += ANTE
            if player['stack'] == 0:
                player['status'] = 'out'

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

# Duplicate functions removed - using the first definitions above

def reset_bets(game_state):
    for player in game_state['players']:
        player['current_bet'] = 0
    game_state['current_bet'] = 0

def advance_round(game_state):
    """
    Progresses to next street: flop, turn, river, or showdown.
    """
    round = game_state['betting_round']
    if round == 'preflop':
        game_state['community'].extend([game_state['deck'].pop() for _ in range(3)])
        game_state['betting_round'] = 'flop'
    elif round == 'flop':
        game_state['community'].append(game_state['deck'].pop())
        game_state['betting_round'] = 'turn'
    elif round == 'turn':
        game_state['community'].append(game_state['deck'].pop())
        game_state['betting_round'] = 'river'
    elif round == 'river':
        game_state['betting_round'] = 'showdown'
    reset_bets(game_state)

from .hand_eval_lib import evaluate_hand

def award_pot(game_state):
    """
    At showdown or if only one remains, determine winner(s) and award pot.
    """
    community = game_state['community']
    active_players = [p for p in game_state['players'] if p['status'] == 'active']
    if len(active_players) == 1:
        # Only one player left, auto-win
        active_players[0]['stack'] += game_state['pot']
        return [active_players[0]['name']]
    else:
        # Showdown: use treys to find the best hand(s)
        scores = []
        for player in active_players:
            score, hand_class = evaluate_hand(player['hand'], community)
            scores.append((score, player['name'], hand_class))
        scores.sort()  # Lower is better
        best_score = scores[0][0]
        winners = [tup[1] for tup in scores if tup[0] == best_score]
        pot_share = game_state['pot'] // len(winners)
        for player in game_state['players']:
            if player['name'] in winners:
                player['stack'] += pot_share
        return winners

def prepare_next_hand(game_state):
    num_players = len(game_state['players'])
    game_state['dealer_pos'] = (game_state['dealer_pos'] + 1) % num_players
    deck = create_deck()
    random.shuffle(deck)
    hands = deal_cards(deck, num_players)
    for i, player in enumerate(game_state['players']):
        player['hand'] = hands[i]
        player['current_bet'] = 0
        if player['stack'] > 0:
            player['status'] = "active"
        else:
            player['status'] = "out"
    game_state['deck'] = deck
    game_state['community'] = []
    game_state['pot'] = 0
    game_state['betting_round'] = 'preflop'
    game_state['current_bet'] = 0
    # Post antes and blinds at the start of each new hand
    apply_antes(game_state)
    post_blinds(game_state)



def showdown(game_state):
    """
    Evaluates all active players' hands, determines the winner(s), and awards the pot.
    Returns a list of winner info and their hand classes.
    """
    community = game_state['community']
    active_players = [p for p in game_state['players'] if p['status'] == 'active']

    # If only one player is left (everyone else folded)
    if len(active_players) == 1:
        active_players[0]['stack'] += game_state['pot']
        return [{
            'name': active_players[0]['name'],
            'hand': active_players[0]['hand'],
            'hand_class': 'No Showdown (everyone else folded)'
        }]

    # Otherwise: classic showdown
    scores = []
    for player in active_players:
        score, hand_class = evaluate_hand(player['hand'], community)
        scores.append((score, player))

    scores.sort(key=lambda tup: tup[0])  # Lowest score wins (treys logic)
    best_score = scores[0][0]
    winners = [player for (score, player) in scores if score == best_score]

    # Split the pot among winners
    pot_share = game_state['pot'] // len(winners)
    for player in winners:
        player['stack'] += pot_share

    # Build info for frontend/UI/logging
    winner_info = [{
        'name': p['name'],
        'hand': p['hand'],
        'hand_class': evaluate_hand(p['hand'], community)[1]
    } for p in winners]

    return winner_info

def post_blinds(game_state, small_blind=SMALL_BLIND, big_blind=BIG_BLIND):
    num_players = len(game_state['players'])
    sb_pos = (game_state['dealer_pos'] + 1) % num_players
    bb_pos = (game_state['dealer_pos'] + 2) % num_players

    for pos, blind, name in [(sb_pos, small_blind, 'small_blind'), (bb_pos, big_blind, 'big_blind')]:
        player = game_state['players'][pos]
        amount = min(player['stack'], blind)
        player['stack'] -= amount
        player['current_bet'] += amount
        game_state['pot'] += amount
        player['status'] = 'active' if player['stack'] > 0 else 'out'
        # Optionally log: (player['name'], name, amount)
    game_state['current_bet'] = big_blind
    game_state['current_player'] = (bb_pos + 1) % num_players  # First to act after blinds


# More functions needed for: betting logic, showdown, winner determination, etc.
