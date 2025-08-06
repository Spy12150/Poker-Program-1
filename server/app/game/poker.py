import random
from .hand_eval_lib import evaluate_hand
from .config import NUM_PLAYERS, STARTING_STACK, SMALL_BLIND, BIG_BLIND, ANTE

"""
Main file for core poker game engine and logic

Standard poker game flow from preflop, flop, turn, river, to showdown
Handles all-in and side pot disribution

Only suitable for heads up for now, will improve for 6 handed

Logs hands to the hand_history folder if cloned on local machine
hand logging format is very similra to the variant used on pokerstars
Might work if you plug it into gtowizard for analysis, not 100% sure
Does nt log when hosted on railway

Supports ante if added in ./config.py

Built for real-time multiplayer poker games with WebSocketcommunication
"""


def create_deck():
    """Creates a standard 52-card deck with suits (s,h,d,c) and ranks (2-A)."""
    suits = ['s', 'h', 'd', 'c']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
    return [r + s for r in ranks for s in suits]

def deal_cards(deck, num_players=NUM_PLAYERS):
    """Deals 2 hole cards to each player from the deck."""
    return [[deck.pop(), deck.pop()] for _ in range(num_players)]

def init_players(num_players=NUM_PLAYERS, stack=STARTING_STACK):
    """Initializes player objects with starting stacks and active status."""
    return [
        {"name": f"Player {i+1}", "hand": [], "stack": stack, "current_bet": 0, "status": "active"}
        for i in range(num_players)
    ]

def start_new_game():
    """Initializes a complete new poker game with deck, players, blinds, and hand history."""
    import os
    from datetime import datetime
    deck = create_deck()
    random.shuffle(deck)
    players = init_players()
    hands = deal_cards(deck, NUM_PLAYERS)
    for i, hand in enumerate(hands):
        players[i]['hand'] = hand

    dealer_pos = random.randint(0, NUM_PLAYERS - 1)  # Random starting dealer

    # Create a unique hand history file for this game session
    # Try to create hand history directory and file (may fail in read-only environments)
    hand_history_path = None
    try:
        hand_history_dir = os.path.join(os.path.dirname(__file__), '../hand_history')
        os.makedirs(hand_history_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        hand_history_filename = f"game_session_{timestamp}.txt"
        hand_history_path = os.path.join(hand_history_dir, hand_history_filename)
        
        # Create the file (clears previous content if it exists)
        with open(hand_history_path, 'w') as f:
            pass  # Just to create the file
    except (OSError, PermissionError) as e:
        print(f"Warning: Could not create hand history file: {e}")
        hand_history_path = None

    game_state = {
        "players": players,
        "deck": deck,
        "community": [],
        "pot": 0,
        "dealer_pos": dealer_pos,
        "current_player": dealer_pos,
        "betting_round": "preflop",
        "current_bet": 0,
        "last_bet_amount": 0,
        "action_history": [],
        "hand_history_path": hand_history_path,
        "hand_count": 1,  # Start with hand #1
        "big_blind": BIG_BLIND,
        "opponent_model": {
            'hands_played': 0,
            'preflop_stats': {
                'vpip': 0, 'pfr': 0, 'three_bet': 0,
                'vpip_opportunities': 0, 'pfr_opportunities': 0, 'three_bet_opportunities': 0
            },
            'postflop_stats': {
                'cbet': 0, 'cbet_opportunities': 0,
                'fold_to_cbet': 0, 'fold_to_cbet_opportunities': 0
            }
        }
    }
    
    # Log the header for the first hand
    log_hand_start_header(game_state)
    
    apply_antes(game_state)
    post_blinds(game_state)
    return game_state

def apply_antes(game_state):
    """Collects ante from all active players before dealing cards."""
    if ANTE > 0:
        for player in game_state['players']:
            if player['status'] == "active" and player['stack'] >= ANTE:
                player['stack'] -= ANTE
                game_state['pot'] += ANTE
            if player['stack'] == 0:
                player['status'] = 'out'

def deal_community_cards(game_state):
    """Deals community cards for next street (flop: 3 cards, turn/river: 1 card each)."""
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
    """Advances to the next active player in turn order."""
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

def log_to_hand_history(game_state, message):
    """Appends a message to the hand history file for game analysis and replay."""
    if game_state.get('hand_history_path'):
        try:
            with open(game_state['hand_history_path'], 'a') as f:
                f.write(message + '\n')
        except (OSError, PermissionError):
            # Silently skip logging if file operations fail
            pass

def apply_action(game_state, action, amount=0):
    """Processes player actions (fold/call/raise/check/bet) and updates game state accordingly."""
    player = game_state['players'][game_state['current_player']]
    to_call = game_state.get('current_bet', 0) - player['current_bet']
    log_message = ""

    if action == 'fold':
        player['status'] = 'folded'
        log_message = f"{player['name']}: folds"
    elif action == 'call':
        call_amt = min(to_call, player['stack'])
        player['stack'] -= call_amt
        player['current_bet'] += call_amt
        game_state['pot'] += call_amt
        log_message = f"{player['name']}: calls ${call_amt:.0f}"
        if player['stack'] == 0:
            player['status'] = 'all-in'
            log_message += " and is all-in"
    elif action == 'raise':
        # amount is the total bet amount
        total_bet = amount
        raise_amount = total_bet - to_call - player['current_bet'] # The actual amount of the raise
        additional_bet = total_bet - player['current_bet']
        
        # Clamp to stack size
        additional_bet = min(additional_bet, player['stack'])
        total_bet = player['current_bet'] + additional_bet

        player['stack'] -= additional_bet
        player['current_bet'] += additional_bet
        game_state['pot'] += additional_bet
        
        log_message = f"{player['name']}: raises ${raise_amount:.0f} to ${total_bet:.0f}"
        
        # Update last bet amount
        previous_bet = game_state.get('current_bet', 0)
        game_state['current_bet'] = player['current_bet']
        game_state['last_bet_amount'] = player['current_bet'] - previous_bet
        
        if player['stack'] == 0:
            player['status'] = 'all-in'
            log_message += " and is all-in"
    elif action == 'check':
        if to_call != 0:
            raise ValueError("Cannot check when facing a bet")
        log_message = f"{player['name']}: checks"
    elif action == 'bet':
        # This action is for when the first action in a post-flop round is a bet
        bet_amount = min(amount, player['stack'])
        player['stack'] -= bet_amount
        player['current_bet'] += bet_amount
        game_state['pot'] += bet_amount
        game_state['current_bet'] = bet_amount
        game_state['last_bet_amount'] = bet_amount
        log_message = f"{player['name']}: bets ${bet_amount:.0f}"
        if player['stack'] == 0:
            player['status'] = 'all-in'
            log_message += " and is all-in"
    else:
        raise ValueError("Invalid action")

    if log_message:
        log_to_hand_history(game_state, log_message)

    # Move to next player (handled outside in your round controller)

def betting_round_over(game_state):
    """Determines if the current betting round is complete based on player actions and bet matching."""
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
    """Executes a sequence of betting actions for automated testing and simulation."""
    for action, amount in action_sequence:
        apply_action(game_state, action, amount)
        if betting_round_over(game_state):
            break
        next_player(game_state)
    reset_bets(game_state)  # When moving to next street


# Note: determine_winner function removed as it's redundant with showdown()

def reset_bets(game_state):
    """Resets all player bets and current_bet for the next betting round."""
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
    """Progresses to next street: flop, turn, river, or showdown with community cards."""
    round = game_state['betting_round']
    if round == 'preflop':
        flop = [game_state['deck'].pop() for _ in range(3)]
        game_state['community'].extend(flop)
        game_state['betting_round'] = 'flop'
        flop_str = " ".join(f"{c}" for c in flop)
        log_to_hand_history(game_state, f"\n*** FLOP *** [{flop_str}]")
    elif round == 'flop':
        turn = game_state['deck'].pop()
        game_state['community'].append(turn)
        game_state['betting_round'] = 'turn'
        turn_str = " ".join(f"{c}" for c in game_state['community'])
        log_to_hand_history(game_state, f"\n*** TURN *** [{turn_str}]")
    elif round == 'turn':
        river = game_state['deck'].pop()
        game_state['community'].append(river)
        game_state['betting_round'] = 'river'
        river_str = " ".join(f"{c}" for c in game_state['community'])
        log_to_hand_history(game_state, f"\n*** RIVER *** [{river_str}]")
    elif round == 'river':
        game_state['betting_round'] = 'showdown'
        log_to_hand_history(game_state, "\n*** SHOW DOWN ***")
    reset_bets(game_state)

def deal_remaining_cards(game_state):
    """Deals all remaining community cards when all players are all-in (run-out)."""
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

def log_hand_start_header(game_state):
    """Logs the PokerStars-style header with hand number, stakes, and player positions."""
    from datetime import datetime
    hand_history_path = game_state['hand_history_path']
    hand_count = game_state['hand_count']
    dealer_pos = game_state['dealer_pos']
    players = game_state['players']
    
    try:
        with open(hand_history_path, 'a') as f:
            if hand_count > 1:
                f.write("\n\n") # Add spacing for subsequent hands
                
            f.write(f"Riposte Hand #{hand_count:05d}:  Hold'em No Limit (${SMALL_BLIND}/${BIG_BLIND}) - {datetime.now().strftime('%Y/%m/%d %H:%M:%S ET')}\n")
            f.write(f"Table 'Heads-Up' 2-max Seat #{dealer_pos + 1} is the button\n")
            for i, p in enumerate(players):
                role = " (button)" if i == dealer_pos else ""
                f.write(f"Seat {i+1}: {p['name']}{role} (${p['stack']:.0f} in chips)\n")
    except Exception as e:
        print(f"Warning: Could not write hand history header: {e}")
        # Continue without hand history logging
        return


def prepare_next_hand(game_state):
    """Sets up the next hand with new cards, rotated dealer, and preserved opponent stats."""
    # Preserve opponent model across hands and increment hand counter
    opponent_model = game_state.get('opponent_model', {
        'hands_played': 0,
        'preflop_stats': {'vpip': 0, 'pfr': 0, 'three_bet': 0, 'vpip_opportunities': 0, 'pfr_opportunities': 0, 'three_bet_opportunities': 0},
        'postflop_stats': {'cbet': 0, 'cbet_opportunities': 0, 'fold_to_cbet': 0, 'fold_to_cbet_opportunities': 0}
    })
    opponent_model['hands_played'] += 1
    game_state['hand_count'] += 1

    num_players = len(game_state['players'])
    dealer_pos = (game_state['dealer_pos'] + 1) % num_players
    deck = create_deck()
    random.shuffle(deck)
    hands = deal_cards(deck, num_players)
    players = game_state['players']

    for i, player in enumerate(players):
        player['hand'] = hands[i]
        player['current_bet'] = 0
        if player['stack'] > 0:
            player['status'] = "active"
        else:
            player['status'] = "out"
            
    game_state.update({
        "deck": deck,
        "community": [],
        "pot": 0,
        "dealer_pos": dealer_pos,
        "betting_round": 'preflop',
        "current_bet": 0,
        "last_bet_amount": 0,
        "action_history": [],
        "opponent_model": opponent_model,
        "current_player": dealer_pos
    })
    
    # Log the header for the new hand
    log_hand_start_header(game_state)
    
    apply_antes(game_state)
    post_blinds(game_state)



def distribute_side_pots(players_in_hand, winner_data, game_state):
    """Calculates and distributes side pots for all-in scenarios with unequal investments."""
    winnings = {p['name']: 0 for p in game_state['players']}
    
    # Get investment amounts (current_bet) for each player in hand
    investments = {}
    for player in players_in_hand:
        investments[player['name']] = player['current_bet']
    
    print(f"DEBUG: Player investments: {investments}")
    print(f"DEBUG: Total pot: {game_state['pot']}")
    
    # Simple case: if all players invested the same amount, distribute normally
    investment_amounts = list(investments.values())
    if len(set(investment_amounts)) == 1:
        # All players invested the same - simple distribution
        total_pot = game_state['pot']
        winners = [w[2] for w in winner_data]  # Extract player objects
        pot_share = total_pot / len(winners)
        
        for winner_player in winners:
            winnings[winner_player['name']] = pot_share
            winner_player['stack'] += pot_share
        
        print(f"DEBUG: Equal investments - simple distribution: {winnings}")
        return winnings
    
    # Complex case: different investment amounts - create side pots
    # Sort by investment amount (lowest to highest)
    sorted_investments = sorted(investments.items(), key=lambda x: x[1])
    
    # Create side pots based on investment levels
    side_pots = []
    prev_level = 0
    
    for i, (current_player, investment) in enumerate(sorted_investments):
        if investment > prev_level:
            # Calculate how many players contributed to this level
            # Everyone who invested at least this much
            contributors = [name for name, amt in investments.items() if amt >= investment]
            num_contributors = len(contributors)
            
            # Size of this side pot: (level_difference) * (number_of_contributors)
            level_diff = investment - prev_level
            pot_size = level_diff * num_contributors
            
            # Players eligible for this side pot are those who invested at least this much
            eligible_players = contributors.copy()
            
            side_pots.append({
                'size': pot_size,
                'eligible_players': eligible_players,
                'level': investment,
                'prev_level': prev_level,
                'contributors': contributors
            })
            
            prev_level = investment
    
    print(f"DEBUG: Side pots created: {side_pots}")
    
    # Distribute each side pot to the best eligible hand(s)
    for pot in side_pots:
        print(f"DEBUG: Processing side pot of ${pot['size']:.0f} for players: {pot['eligible_players']}")
        
        # Find the best hand among eligible players
        eligible_winners = []
        best_score = float('inf')
        
        for score, hand_class, player in winner_data:
            if player['name'] in pot['eligible_players']:
                if score < best_score:
                    best_score = score
                    eligible_winners = [(score, hand_class, player)]
                elif score == best_score:
                    eligible_winners.append((score, hand_class, player))
        
        if eligible_winners:
            # Split this side pot among eligible winners with the best hand
            pot_share = pot['size'] / len(eligible_winners)
            for _, _, winner_player in eligible_winners:
                winnings[winner_player['name']] += pot_share
                winner_player['stack'] += pot_share
                print(f"DEBUG: Awarded ${pot_share:.0f} from side pot to {winner_player['name']}")
    
    print(f"DEBUG: Final winnings distribution: {winnings}")
    
    # Verify total distributed equals total pot
    total_distributed = sum(winnings.values())
    print(f"DEBUG: Total distributed: ${total_distributed:.0f}, Total pot: ${game_state['pot']:.0f}")
    
    return winnings

def showdown(game_state):
    """Evaluates all hands, determines winners, distributes pots, and logs complete results."""
    community = game_state['community']
    players_in_hand = [p for p in game_state['players'] if p['status'] in ['active', 'all-in']]
    all_players = game_state['players']
    winners = []
    player_scores = {}
    
    # Store initial state for summary
    initial_stacks = {p['name']: p['stack'] + p['current_bet'] for p in all_players}
    
    print(f"DEBUG SHOWDOWN: Initial state:")
    for p in all_players:
        print(f"  {p['name']}: stack={p['stack']}, current_bet={p['current_bet']}, total={p['stack'] + p['current_bet']}")
    print(f"DEBUG SHOWDOWN: Total pot = {game_state['pot']}")
    
    # --- Single Winner by Folds ---
    if len(players_in_hand) == 1:
        winner = players_in_hand[0]
        pot_won = game_state['pot']
        
        # Return uncalled bet
        uncalled_bet = pot_won - sum(p['current_bet'] for p in all_players if p != winner)
        if uncalled_bet > 0:
            winner['stack'] += uncalled_bet
            log_to_hand_history(game_state, f"Uncalled bet (${uncalled_bet:.0f}) returned to {winner['name']}")

        winnings = pot_won - uncalled_bet
        winner['stack'] += winnings
        log_to_hand_history(game_state, f"{winner['name']} collected ${winnings:.0f} from pot")
        log_to_hand_history(game_state, f"{winner['name']}: doesn't show hand")
        winners = [{'name': winner['name'], 'hand': winner['hand'], 'hand_class': 'Wins by Fold'}]
        
    # --- Showdown with 2+ Players ---
    else:
        for player in players_in_hand:
            score, hand_class = evaluate_hand(player['hand'], community)
            player_scores[player['name']] = (score, hand_class, player)
            log_to_hand_history(game_state, f"{player['name']}: shows [{player['hand'][0]} {player['hand'][1]}] ({hand_class})")

        sorted_hands = sorted(player_scores.values(), key=lambda x: x[0])
        best_score = sorted_hands[0][0]
        winner_data = [info for info in sorted_hands if info[0] == best_score]
        winners = [{'name': w[2]['name'], 'hand': w[2]['hand'], 'hand_class': w[1]} for w in winner_data]

        # Proper side pot calculation
        winnings_distributed = distribute_side_pots(players_in_hand, winner_data, game_state)
        
        print(f"DEBUG SHOWDOWN: After side pot distribution:")
        for p in all_players:
            print(f"  {p['name']}: stack={p['stack']}, current_bet={p['current_bet']}, total={p['stack'] + p['current_bet']}")
        
        # Log the winnings
        for player_name, amount_won in winnings_distributed.items():
            if amount_won > 0:
                log_to_hand_history(game_state, f"{player_name} collected ${amount_won:.0f} from pot")

    # --- Summary Section ---
    log_to_hand_history(game_state, "\n*** SUMMARY ***")
    total_pot_summary = game_state['pot']
    board_str = " ".join(f"[{c}]" for c in community)
    log_to_hand_history(game_state, f"Total pot ${total_pot_summary:.0f} | Rake $0.00")
    if board_str:
        log_to_hand_history(game_state, f"Board [{board_str}]")

    for i, p in enumerate(all_players):
        summary_line = f"Seat {i+1}: {p['name']}"
        if i == game_state['dealer_pos']:
            summary_line += " (button)"
        
        # Find player's result from the winners list
        player_result = next((w for w in winners if w['name'] == p['name']), None)

        if p['status'] == 'folded':
            # Find when they folded
            folded_round = 'before Flop'
            for action in reversed(game_state.get('action_history', [])):
                if action.get('player') == p['name'] and action.get('action') == 'fold':
                    folded_round = f"on the {action.get('round', 'round').capitalize()}"
                    break
            summary_line += f" folded {folded_round}"
            if p['current_bet'] == 0:
                 summary_line += " (didn't bet)"
        elif player_result:
             net_change = (p['stack'] + p['current_bet']) - initial_stacks[p['name']]
             summary_line += f" collected (${net_change:.0f}) with {player_result['hand_class']}"
        else: # Lost at showdown
            hand_class = player_scores.get(p['name'], ('', 'lost'))[1]
            summary_line += f" lost with {hand_class}"

        log_to_hand_history(game_state, summary_line)

    # Reset for next hand
    game_state['pot'] = 0
    for player in all_players:
        player['current_bet'] = 0
    game_state['current_bet'] = 0
    
    print(f"DEBUG SHOWDOWN: Final state after reset:")
    for p in all_players:
        print(f"  {p['name']}: stack={p['stack']}, current_bet={p['current_bet']}")
    
    return winners


def post_blinds(game_state, small_blind=SMALL_BLIND, big_blind=BIG_BLIND):
    """Posts small and big blinds with proper heads-up and multi-player positioning rules."""
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

    sb_player = game_state['players'][sb_pos]
    bb_player = game_state['players'][bb_pos]
    
    # Post SB
    sb_amount = min(sb_player['stack'], small_blind)
    sb_player['stack'] -= sb_amount
    sb_player['current_bet'] += sb_amount
    game_state['pot'] += sb_amount
    log_to_hand_history(game_state, f"{sb_player['name']}: posts small blind ${sb_amount:.0f}")

    # Post BB
    bb_amount = min(bb_player['stack'], big_blind)
    bb_player['stack'] -= bb_amount
    bb_player['current_bet'] += bb_amount
    game_state['pot'] += bb_amount
    log_to_hand_history(game_state, f"{bb_player['name']}: posts big blind ${bb_amount:.0f}")

    game_state['current_bet'] = big_blind
    game_state['last_bet_amount'] = big_blind  # Big blind is the last bet amount
    game_state['current_player'] = first_to_act  # Set correct first player
    log_to_hand_history(game_state, "\n*** PREFLOP ***")
    log_to_hand_history(game_state, "*** HOLE CARDS ***")
    # Log both players' hands
    hero = game_state['players'][0]
    villain = game_state['players'][1]
    log_to_hand_history(game_state, f"Dealt to {hero['name']} [{hero['hand'][0]} {hero['hand'][1]}]")
    log_to_hand_history(game_state, f"Dealt to {villain['name']} [{villain['hand'][0]} {villain['hand'][1]}]")



