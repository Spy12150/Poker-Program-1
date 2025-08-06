"""
Postflop strategy module to support the hard_coded bots

This file includes the monte carlo simulation with account for opponent range

also checks for draw analysis and blockers
"""

import random
import itertools
try:
    from ..hand_eval_lib import evaluate_hand
except ImportError:
    try:
        from hand_eval_lib import evaluate_hand
    except ImportError:
        # Fallback if hand_eval_lib is not available
        def evaluate_hand(hand, board):
            # Simple fallback evaluation
            return 5000, "Unknown"

class PostflopStrategy:
    def __init__(self):
        self.card_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, 
                           '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        self.inv_card_values = {v: k for k, v in self.card_values.items()}
        
    def calculate_hand_equity(self, hero_hand, board, villain_range=None, num_simulations=1000):
        """
        Calculate hand equity using Monte Carlo simulation against a specified villain range.
        """
        if len(board) == 5:
            return self.calculate_showdown_equity(hero_hand, board, villain_range)
        
        deck = self.create_deck()
        used_cards = set(hero_hand + board)
        
        wins = 0
        total_sims = 0

        # Filter villain_range to only include hands not conflicting with known cards
        valid_villain_hands = []
        if villain_range:
            for hand in villain_range:
                if not any(card in used_cards for card in hand):
                    valid_villain_hands.append(hand)
        
        if not valid_villain_hands:
            # Fallback: if range is empty or all hands conflict, simulate against any two unknown cards
            available_cards = [card for card in deck if card not in used_cards]
            if len(available_cards) < 2: return 0.5
            valid_villain_hands = list(itertools.combinations(available_cards, 2))


        for i in range(num_simulations):
            
            # 1. Sample a random board completion
            deck_after_hero = [card for card in deck if card not in used_cards]
            
            cards_to_deal = 5 - len(board)
            if len(deck_after_hero) < cards_to_deal: continue

            board_completion = random.sample(deck_after_hero, cards_to_deal)
            full_board = board + board_completion
            
            # 2. Sample a villain hand from their valid range
            current_used_cards = used_cards.union(board_completion)
            
            runout_valid_villain_hands = [h for h in valid_villain_hands if not any(c in current_used_cards for c in h)]
            if not runout_valid_villain_hands:
                continue # No valid opponent hands for this runout

            villain_hand = random.choice(runout_valid_villain_hands)

            # 3. Evaluate hands
            try:
                hero_score, _ = evaluate_hand(hero_hand, full_board)
                villain_score, _ = evaluate_hand(list(villain_hand), full_board)

                if hero_score < villain_score:
                    wins += 1
                elif hero_score == villain_score:
                    wins += 0.5
                
                total_sims += 1
            except Exception as e:
                # print(f"DEBUG: Error during equity simulation: {e}")
                continue

        return wins / total_sims if total_sims > 0 else 0.5
    
    def calculate_showdown_equity(self, hero_hand, board, villain_range=None):
        """
        Calculate equity at showdown (when all 5 board cards are dealt)
        
        Args:
            hero_hand: Hero's hole cards
            board: Complete 5-card board
            villain_range: Estimated villain hand range (if None, assumes random hand)
        """
        if len(board) != 5:
            raise ValueError("Board must have exactly 5 cards for showdown equity")
        
        # Create deck without known cards
        deck = self.create_deck()
        used_cards = set(hero_hand + board)
        
        wins = 0
        total_hands = 0
        
        # If villain range is specified, use it; otherwise sample random hands
        if villain_range:
            villain_hands = [h for h in villain_range if not any(c in used_cards for c in h)]
        else:
            # Generate all possible villain hands from remaining cards
            available_cards = [card for card in deck if card not in used_cards]
            if len(available_cards) < 2: return 0.5
            villain_hands = list(itertools.combinations(available_cards, 2))
        
        if not villain_hands:
            return 0.5 # No possible hands for villain

        for villain_hand in villain_hands:
            try:
                hero_score, _ = evaluate_hand(hero_hand, board)
                villain_score, _ = evaluate_hand(list(villain_hand), board)
                
                if hero_score < villain_score:  # Lower score wins in treys
                    wins += 1
                elif hero_score == villain_score:
                    wins += 0.5  # Split pot
                
                total_hands += 1
            except:
                continue
        
        return wins / total_hands if total_hands > 0 else 0.5
    
    def analyze_draws(self, hero_hand, board):
        """
        Analyze drawing potential of hero's hand
        """
        if len(board) < 3:
            return {'flush_draw': False, 'straight_draw': False, 'outs': 0}
        
        full_hand = hero_hand + board
        suits = [card[1] for card in full_hand]
        ranks = [self.card_values[card[0]] for card in full_hand]
        
        # Flush draw analysis
        suit_counts = {}
        for suit in suits:
            suit_counts[suit] = suit_counts.get(suit, 0) + 1
        
        max_suit_count = max(suit_counts.values()) if suit_counts else 0
        flush_draw = max_suit_count == 4
        
        # Straight draw analysis
        unique_ranks = sorted(list(set(ranks)))
        straight_draw = False
        straight_outs = 0
        
        # Check for open-ended straight draws
        if len(unique_ranks) >= 4:
            for i in range(len(unique_ranks) - 3):
                sequence = unique_ranks[i:i+4]
                if sequence[-1] - sequence[0] == 3:  # 4 cards in sequence
                    straight_draw = True
                    straight_outs = 8  # Open-ended
                    break
            
            # Check for gutshot straight draws
            if not straight_draw:
                for i in range(len(unique_ranks) - 2):
                    if unique_ranks[i+2] - unique_ranks[i] == 4 and len(set(unique_ranks[i:i+3])) == 3:  # Gap in middle
                        straight_draw = True
                        straight_outs = 4  # Gutshot
                        break
        
        # Count total outs
        outs = 0
        if flush_draw:
            outs += 9  # 9 flush cards remaining
        if straight_draw:
            outs += straight_outs
        
        # Adjust for potential overlaps (flush + straight)
        if flush_draw and straight_draw:
            # A simple approximation
            outs = 15
        
        return {
            'flush_draw': flush_draw,
            'straight_draw': straight_draw,
            'outs': outs,
            'equity_with_draws': self.outs_to_equity(outs, 5 - len(board))
        }
    
    def outs_to_equity(self, outs, cards_to_come):
        """Convert outs to equity percentage"""
        if cards_to_come == 2:  # Flop to river
            return min(1.0, (outs * 4) / 100)  # Rule of 4
        elif cards_to_come == 1:  # Turn to river
            return min(1.0, (outs * 2) / 100)  # Rule of 2
        else:
            return 0
    
    def calculate_pot_odds(self, bet_to_call, pot_size):
        """Calculate pot odds"""
        if bet_to_call <= 0:
            return float('inf')
        return pot_size / bet_to_call
    
    def calculate_minimum_defense_frequency(self, bet_size, pot_size):
        """Calculate minimum frequency to defend vs bet to prevent bluffs from being profitable"""
        total_pot_after_bet = pot_size + bet_size
        return pot_size / total_pot_after_bet
    
    def select_bluff_hands(self, hand, board, position='ip'):
        """
        Select appropriate bluff hands based on blockers and equity
        """
        # Blocker analysis
        blockers = self.analyze_blockers(hand, board)
        
        # Prefer hands with good blockers or some equity
        bluff_suitability = 0
        
        # Ace blockers are valuable
        if any(card[0] == 'A' for card in hand):
            bluff_suitability += 0.3
        
        # King blockers on ace-high boards
        if any(card[0] == 'A' for card in board) and any(card[0] == 'K' for card in hand):
            bluff_suitability += 0.2
        
        # Backdoor draw potential
        if len(board) == 3:  # Flop
            if self.has_backdoor_potential(hand, board):
                bluff_suitability += 0.2
        
        return bluff_suitability > 0.3
    
    def analyze_blockers(self, hand, board):
        """Analyze blocker effects of hero's cards"""
        blockers = {
            'ace_blocker': any(card[0] == 'A' for card in hand),
            'king_blocker': any(card[0] == 'K' for card in hand),
            'flush_blockers': 0,
            'straight_blockers': 0
        }
        
        # Count flush blockers
        board_suits = [card[1] for card in board]
        for suit in set(board_suits):
            if board_suits.count(suit) >= 2:  # Potential flush draw on board
                hand_blockers = sum(1 for card in hand if card[1] == suit)
                blockers['flush_blockers'] += hand_blockers
        
        return blockers
    
    def has_backdoor_potential(self, hand, board):
        """Check for backdoor flush or straight potential"""
        full_hand = hand + board
        suits = [card[1] for card in full_hand]
        ranks = [self.card_values[card[0]] for card in full_hand]
        
        # Backdoor flush (need 2 more of same suit)
        suit_counts = {}
        for suit in suits:
            suit_counts[suit] = suit_counts.get(suit, 0) + 1
        
        if max(suit_counts.values()) >= 3:
            return True
        
        # Backdoor straight potential (simplified check)
        unique_ranks = sorted(set(ranks))
        if len(unique_ranks) >= 3:
            for i in range(len(unique_ranks) - 2):
                if unique_ranks[i+2] - unique_ranks[i] <= 6:  # Within range for backdoor
                    return True
        
        return False
    
    def create_deck(self):
        """Create standard 52-card deck"""
        suits = ['s', 'h', 'd', 'c']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        return [r + s for r in ranks for s in suits]

    def convert_range_tuples_to_hands(self, range_tuples):
        """
        Converts a list of hand tuples into a list of all possible specific card combinations.
        e.g., [(7, 7)] -> [['7s', '7h'], ['7s', '7d'], ...]
        """
        all_hands = []
        suits = ['s', 'h', 'd', 'c']

        for hand_tuple in range_tuples:
            if len(hand_tuple) == 2:  # Pair
                rank = self.inv_card_values[hand_tuple[0]]
                all_hands.extend([list(pair) for pair in itertools.combinations([rank + s for s in suits], 2)])
            else:
                high_rank_val, low_rank_val, is_suited = hand_tuple
                high_rank = self.inv_card_values[high_rank_val]
                low_rank = self.inv_card_values[low_rank_val]
                
                if is_suited:
                    for s in suits:
                        all_hands.append([high_rank + s, low_rank + s])
                else: # Offsuit
                    for s1 in suits:
                        for s2 in suits:
                            if s1 != s2:
                                all_hands.append([high_rank + s1, low_rank + s2])
        return all_hands
    
    def get_optimal_bet_size(self, hand_strength, board_texture, pot_size, stack_size, street):
        """
        Calculate optimal bet size based on hand strength and board texture
        """
        base_bet = pot_size * 0.67  # Standard 2/3 pot bet
        
        if hand_strength >= 0.85:
            return min(stack_size, pot_size * 0.75 if street != 'river' else pot_size * 1.0)
        elif hand_strength >= 0.65:
            return min(stack_size, base_bet)
        elif hand_strength >= 0.35:
            return min(stack_size, pot_size * 0.5)
        else:  # Bluffs
            return min(stack_size, pot_size * 0.75 if board_texture.get('wet') else pot_size * 0.5)
    
    def should_bluff(self, hand, board, opponent_stats, pot_size, bet_size, street):
        """
        Determine if this is a good spot to bluff
        """
        base_bluff_freq = {'flop': 0.25, 'turn': 0.20, 'river': 0.15}
        bluff_freq = base_bluff_freq.get(street, 0.15)
        
        if len(board) >= 3:
            board_texture = self.analyze_draws(hand, board) # Simplified texture
            if board_texture['flush_draw'] or board_texture['straight_draw']:
                bluff_freq *= 1.2
        
        fold_to_bet = opponent_stats.get('fold_to_cbet', 0.5)
        bluff_freq *= (fold_to_bet / 0.5)
        
        if self.select_bluff_hands(hand, board):
            bluff_freq *= 1.3
        
        return random.random() < bluff_freq

# Example usage functions
def calculate_equity_simple(hero_hand, board, num_sims=500):
    """Simplified equity calculation for integration"""
    strategy = PostflopStrategy()
    return strategy.calculate_hand_equity(hero_hand, board, num_simulations=num_sims)

def get_betting_action(hand_strength, equity, pot_odds, board_texture, street):
    """Simplified betting decision"""
    if hand_strength >= 0.7 or equity >= 0.6:
        return 'bet'
    elif equity >= 0.35 and pot_odds >= 2.5:
        return 'call'
    elif hand_strength >= 0.4:
        return 'check'
    else:
        return 'check'
