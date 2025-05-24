from treys import Card, Evaluator

evaluator = Evaluator()

def evaluate_hand(player_hand, community):
    """
    Evaluates a Texas Hold'em hand using treys.

    Args:
        player_hand (list): 2 hole cards, e.g., ['As', 'Kd']
        community (list): up to 5 community cards, e.g., ['2c', '5h', '9s', 'Jh', '7d']

    Returns:
        int: Treys score (lower is better; 1 is Royal Flush, ~7000 is worst high card)
        str: Human-readable hand class (e.g., "Pair", "Full House", etc.)
    """
    # Convert card strings to treys format (e.g., 'As' → 'As', 'Td' → 'Td')
    treys_hand = [Card.new(card) for card in player_hand]
    treys_board = [Card.new(card) for card in community]
    score = evaluator.evaluate(treys_hand, treys_board)
    hand_class = evaluator.class_to_string(evaluator.get_rank_class(score))
    return score, hand_class

# Example test (can delete later)
if __name__ == "__main__":
    hand = ['As', 'Kd']
    board = ['2c', '5h', '9s', 'Jh', '7d']
    score, hand_class = evaluate_hand(hand, board)
    print("Score:", score)
    print("Hand:", hand_class)