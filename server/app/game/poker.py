import random

def create_deck():
    suits = ['s', 'h', 'd', 'c']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
    return [r + s for r in ranks for s in suits]

def deal_cards(deck, count):
    return [deck.pop() for _ in range(count)]

def start_new_game():
    deck = create_deck()
    random.shuffle(deck)

    player_hand = deal_cards(deck, 2)
    ai_hand = deal_cards(deck, 2)

    return {
        "deck": deck,
        "player_hand": player_hand,
        "ai_hand": ai_hand,
        "community": [],
        "player_stack": 1000,
        "ai_stack": 1000,
        "pot": 0,
        "round": "preflop",
        "last_player_action": None,
        "ai_decision": None
    }

