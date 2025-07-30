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

    dealer_pos = random.randint(0, NUM_PLAYERS - 1)  # Random starting dealer
    
    game_state = {
        "players": players,
        "deck": deck,
        "community": [],
        "pot": 0,
        "dealer_pos": dealer_pos,
        "current_player": dealer_pos,  # In heads-up, dealer (SB) acts first preflop
        "betting_round": "preflop",
        "current_bet": 0,
        "last_bet_amount": 0,  # Track the last bet/raise amount for minimum raise calculation
        "action_history": [],
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
    print(f"DEBUG: next_player called, current: {i}")
    for _ in range(num_players):
        i = (i + 1) % num_players
        print(f"DEBUG: checking player {i}, status: {game_state['players'][i]['status']}")
        if game_state['players'][i]['status'] == "active":
            game_state['current_player'] = i
            print(f"DEBUG: next_player set current_player to {i}")
            return
    print(f"DEBUG: next_player found no active players!")

def apply_action(game_state, action, amount=0):
    """
    action: 'fold', 'call', 'raise', 'check'
    amount: only used for 'raise'
    """
    player = game_state['players'][game_state['current_player']]
    to_call = game_state.get('current_bet', 0) - player['current_bet']

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
        # amount should be the total bet amount, not just the raise
        total_bet = amount
        additional_bet = total_bet - player['current_bet']
        
        # Calculate minimum raise based on last bet amount
        current_bet = game_state.get('current_bet', 0)
        last_bet_amount = game_state.get('last_bet_amount', 0)
        
        if current_bet == 0:
            # First bet of the round - minimum is big blind
            min_raise_total = BIG_BLIND
        else:
            # Must raise by at least the size of the last bet/raise
            min_raise_total = current_bet + max(last_bet_amount, BIG_BLIND)
        
        if total_bet < min_raise_total:
            total_bet = min_raise_total
            additional_bet = total_bet - player['current_bet']
        
        # Can't bet more than stack
        additional_bet = min(additional_bet, player['stack'])
        
        player['stack'] -= additional_bet
        player['current_bet'] += additional_bet
        game_state['pot'] += additional_bet
        
        # Update last bet amount (the size of this raise)
        previous_bet = game_state.get('current_bet', 0)
        game_state['current_bet'] = player['current_bet']
        game_state['last_bet_amount'] = player['current_bet'] - previous_bet
        
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
    - All remaining players are all-in (no one can act)
    - No more betting actions are possible (e.g., one player all-in, other called)
    - AND the player who needs to act next has already had their turn this round
    """
    # Include both active and all-in players in the count
    players_in_hand = [p for p in game_state['players'] if p['status'] in ['active', 'all-in']]
    active_players = [p for p in game_state['players'] if p['status'] == 'active']
    
    # If only one player total is left in the hand, round is over
    if len(players_in_hand) <= 1:
        return True
    
    # If all remaining players are all-in, no more betting can occur
    if len(active_players) == 0:
        return True

    # Check if no more betting actions are possible
    # This happens when at least one player is all-in and all others have called
    all_in_players = [p for p in game_state['players'] if p['status'] == 'all-in']
    if len(all_in_players) > 0:
        # If someone is all-in, check if all other players have matched the current bet
        current_bet = game_state.get('current_bet', 0)
        all_matched = True
        for player in players_in_hand:
            if player['status'] == 'active' and player['current_bet'] != current_bet:
                all_matched = False
                break
        if all_matched:
            return True

    # All active players must have matched the current bet
    current_bet = game_state.get('current_bet', 0)
    
    # Check if anyone still needs to call (only active players can act)
    for player in active_players:
        if player['stack'] > 0 and player['current_bet'] != current_bet:
            return False
    
    # Now check if betting action is complete
    action_history = game_state.get('action_history', [])
    betting_round = game_state.get('betting_round', 'preflop')
    round_actions = [a for a in action_history if a.get('round') == betting_round]
    
    # If there are no actions this round, betting isn't over
    if len(round_actions) == 0:
        return False
    
    # For heads-up poker, we need special logic
    if len(game_state['players']) == 2:
        # Get the current player index and the other player
        current_player_idx = game_state.get('current_player', 0)
        other_player_idx = 1 - current_player_idx
        
        current_player = game_state['players'][current_player_idx]
        other_player = game_state['players'][other_player_idx]
        
        # If current player has already acted this round, and all bets are matched, round is over
        # Exception: if other player just raised and current player hasn't responded
        
        current_player_actions = [a for a in round_actions if a.get('player') == current_player['name']]
        other_player_actions = [a for a in round_actions if a.get('player') == other_player['name']]
        
        # Both players must have acted at least once (unless one folded/all-in)
        if current_player['status'] == 'active' and len(current_player_actions) == 0:
            return False
        if other_player['status'] == 'active' and len(other_player_actions) == 0:
            return False
        
        # Check if the last action was a raise/bet and the other player needs to respond
        if len(round_actions) > 0:
            last_action = round_actions[-1]
            last_actor_name = last_action.get('player', '')
            
            # If last action was a raise/bet and the other player hasn't responded yet
            if last_action['action'] in ['raise', 'bet']:
                # Find who needs to respond
                responder = None
                for p in [current_player, other_player]:
                    if p['name'] != last_actor_name and p['status'] == 'active':
                        responder = p
                        break
                
                # If there's someone who needs to respond and they haven't acted after the raise
                if responder:
                    # Check if responder acted after this raise by looking at subsequent actions
                    last_raise_index = -1
                    for i in range(len(round_actions) - 1, -1, -1):
                        if (round_actions[i].get('player') == last_actor_name and 
                            round_actions[i]['action'] in ['raise', 'bet']):
                            last_raise_index = i
                            break
                    
                    # If we found the raise, check if responder acted after it
                    if last_raise_index >= 0:
                        responder_acted_after = False
                        for i in range(last_raise_index + 1, len(round_actions)):
                            if round_actions[i].get('player') == responder['name']:
                                responder_acted_after = True
                                break
                        
                        if not responder_acted_after:
                            return False
    
    return True

def run_betting_round(game_state, action_sequence):
    """
    action_sequence: list of tuples (action, amount)
    For actual play, you'll step this as each player acts.
    """
    for action, amount in action_sequence:
        apply_action(game_state, action, amount)
        if betting_round_over(game_state):
            break
        next_player(game_state)
    reset_bets(game_state)  # When moving to next street


# Note: determine_winner function removed as it's redundant with showdown()

def reset_bets(game_state):
    for player in game_state['players']:
        player['current_bet'] = 0
        # Reset player status to active if they have chips and aren't folded
        if player['stack'] > 0 and player['status'] not in ['folded']:
            player['status'] = 'active'
    game_state['current_bet'] = 0
    game_state['last_bet_amount'] = 0  # Reset last bet amount for new round
    # Keep action_history but ensure it's initialized
    if 'action_history' not in game_state:
        game_state['action_history'] = []

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

def deal_remaining_cards(game_state):
    """
    Deal all remaining community cards when all players are all-in.
    This skips betting rounds and goes straight to showdown.
    """
    round = game_state['betting_round']
    
    if round == 'preflop':
        # Deal flop (3 cards)
        game_state['community'].extend([game_state['deck'].pop() for _ in range(3)])
        # Deal turn (1 card)
        game_state['community'].append(game_state['deck'].pop())
        # Deal river (1 card)
        game_state['community'].append(game_state['deck'].pop())
    elif round == 'flop':
        # Deal turn and river
        game_state['community'].append(game_state['deck'].pop())
        game_state['community'].append(game_state['deck'].pop())
    elif round == 'turn':
        # Deal river only
        game_state['community'].append(game_state['deck'].pop())
    
    # Set to showdown
    game_state['betting_round'] = 'showdown'
    # DON'T reset bets here - we need current_bet values for side pot calculation
    # reset_bets(game_state)  # REMOVED: This was wiping out investment info needed for showdown

from .hand_eval_lib import evaluate_hand

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
    game_state['last_bet_amount'] = 0
    game_state['action_history'] = []
    
    # In heads-up, dealer (SB) acts first preflop
    game_state['current_player'] = game_state['dealer_pos']
    
    # Post antes and blinds at the start of each new hand
    apply_antes(game_state)
    post_blinds(game_state)



def showdown(game_state):
    """
    Evaluates all active players' hands, determines the winner(s), and awards the pot with proper side pot logic.
    When a player goes all-in with fewer chips, they can only win as much as they contributed from each opponent.
    Returns a list of winner info and their hand classes.
    """
    community = game_state['community']
    # Include both active and all-in players in showdown
    players_in_hand = [p for p in game_state['players'] if p['status'] in ['active', 'all-in']]

    # If only one player is left (everyone else folded)
    if len(players_in_hand) == 1:
        players_in_hand[0]['stack'] += game_state['pot']
        # Clear the pot and reset bets since we awarded it
        game_state['pot'] = 0
        # Reset current_bet values
        for player in game_state['players']:
            player['current_bet'] = 0
        game_state['current_bet'] = 0
        return [{
            'name': players_in_hand[0]['name'],
            'hand': players_in_hand[0]['hand'],
            'hand_class': 'No Showdown (everyone else folded)'
        }]

    # Evaluate hands
    player_scores = {}
    for player in players_in_hand:
        score, hand_class = evaluate_hand(player['hand'], community)
        player_scores[player['name']] = (score, hand_class, player)

    # Sort by hand strength (lowest score wins with treys)
    sorted_hands = sorted(player_scores.values(), key=lambda x: x[0])
    best_score = sorted_hands[0][0]
    
    # For heads-up poker, implement proper all-in side pot logic
    if len(players_in_hand) == 2:
        player1, player2 = players_in_hand[0], players_in_hand[1]
        
        # Find who has the better hand
        p1_score = player_scores[player1['name']][0]
        p2_score = player_scores[player2['name']][0]
        
        # Get actual investments (current_bet represents total investment this hand)
        p1_investment = player1['current_bet']
        p2_investment = player2['current_bet']
        
        # Store the total pot before we clear it
        total_pot = game_state['pot']
        
        # Determine winner(s)
        if p1_score < p2_score:
            winner, loser = player1, player2
            winner_investment, loser_investment = p1_investment, p2_investment
        elif p2_score < p1_score:
            winner, loser = player2, player1
            winner_investment, loser_investment = p2_investment, p1_investment
        else:
            # Tie - split the actual pot based on investments
            smaller_investment = min(p1_investment, p2_investment)
            larger_investment = max(p1_investment, p2_investment)
            
            # Calculate main pot and side pot from actual investments
            if smaller_investment == larger_investment:
                # Equal investments - split the entire pot
                each_gets = total_pot // 2
                player1['stack'] += each_gets
                player2['stack'] += each_gets
                # Handle odd chip
                if total_pot % 2 == 1:
                    player1['stack'] += 1  # Give odd chip to first player
            else:
                # Unequal investments - proper side pot calculation
                # Main pot is contested by both players
                main_pot_size = smaller_investment * 2
                side_pot_size = total_pot - main_pot_size
                
                # Split main pot equally
                each_gets_from_main = main_pot_size // 2
                player1['stack'] += each_gets_from_main
                player2['stack'] += each_gets_from_main
                
                # Give side pot to whoever invested more
                if p1_investment > p2_investment:
                    player1['stack'] += side_pot_size
                else:
                    player2['stack'] += side_pot_size
            
            # Clear the pot and reset bets
            game_state['pot'] = 0
            for player in game_state['players']:
                player['current_bet'] = 0
            game_state['current_bet'] = 0
            
            return [
                {
                    'name': player1['name'],
                    'hand': player1['hand'],
                    'hand_class': player_scores[player1['name']][1]
                },
                {
                    'name': player2['name'],
                    'hand': player2['hand'],
                    'hand_class': player_scores[player2['name']][1]
                }
            ]
        
        # Winner takes contested portion, excess goes back to whoever invested it
        smaller_investment = min(winner_investment, loser_investment)
        larger_investment = max(winner_investment, loser_investment)
        
        if smaller_investment == larger_investment:
            # Equal investments - winner gets entire pot
            winner['stack'] += total_pot
        else:
            # Unequal investments - calculate main pot and side pot
            main_pot_size = smaller_investment * 2
            side_pot_size = total_pot - main_pot_size
            
            # Winner gets the main pot (contested portion)
            winner['stack'] += main_pot_size
            
            # Side pot goes to whoever invested more
            if winner_investment > loser_investment:
                # Winner invested more, gets side pot too
                winner['stack'] += side_pot_size
            else:
                # Loser invested more, gets side pot back
                loser['stack'] += side_pot_size
        
        # Clear the pot and reset bets
        game_state['pot'] = 0
        for player in game_state['players']:
            player['current_bet'] = 0
        game_state['current_bet'] = 0
        
        return [{
            'name': winner['name'],
            'hand': winner['hand'],
            'hand_class': player_scores[winner['name']][1]
        }]
    
    else:
        # Multi-player: enhanced logic for side pots
        # For now, use simplified approach but fix chopped pot
        winners = [info[2] for info in sorted_hands if info[0] == best_score]
        
        total_pot = game_state['pot']
        
        if len(winners) == 1:
            # Single winner gets everything
            winners[0]['stack'] += total_pot
        else:
            # Multiple winners - split pot
            pot_share = total_pot // len(winners)
            remainder = total_pot % len(winners)
            
            for i, winner in enumerate(winners):
                winner['stack'] += pot_share
                # Give remainder to first winner(s)
                if i < remainder:
                    winner['stack'] += 1
        
        # Clear the pot and reset bets
        game_state['pot'] = 0
        for player in game_state['players']:
            player['current_bet'] = 0
        game_state['current_bet'] = 0
        
        winner_info = [{
            'name': p['name'],
            'hand': p['hand'],
            'hand_class': player_scores[p['name']][1]
        } for p in winners]
        
        return winner_info

def post_blinds(game_state, small_blind=SMALL_BLIND, big_blind=BIG_BLIND):
    num_players = len(game_state['players'])
    
    if num_players == 2:  # Heads-up poker rules
        # In heads-up, dealer posts small blind and acts first preflop
        sb_pos = game_state['dealer_pos']  # Dealer posts small blind
        bb_pos = (game_state['dealer_pos'] + 1) % 2  # Other player posts big blind
        first_to_act = sb_pos  # Small blind acts first in heads-up preflop
    else:
        # Standard multi-player rules
        sb_pos = (game_state['dealer_pos'] + 1) % num_players
        bb_pos = (game_state['dealer_pos'] + 2) % num_players
        first_to_act = (bb_pos + 1) % num_players

    for pos, blind, name in [(sb_pos, small_blind, 'small_blind'), (bb_pos, big_blind, 'big_blind')]:
        player = game_state['players'][pos]
        amount = min(player['stack'], blind)
        player['stack'] -= amount
        player['current_bet'] += amount
        game_state['pot'] += amount
        player['status'] = 'active' if player['stack'] > 0 else 'out'
        # Optionally log: (player['name'], name, amount)
    
    game_state['current_bet'] = big_blind
    game_state['last_bet_amount'] = big_blind  # Big blind is the last bet amount
    game_state['current_player'] = first_to_act  # Set correct first player


# More functions needed for: betting logic, showdown, winner determination, etc.
