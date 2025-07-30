"""
Advanced Postflop Strategy Module

Implements sophisticated postflop play including:
- Hand equity calculations
- Draw analysis
- Opponent range estimation
- Optimal betting strategies
- Bluff selection
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
        
    def calculate_hand_equity(self, hero_hand, board, villain_range=None, num_simulations=1000):
        """
        Calculate hand equity using Monte Carlo simulation
        
        Args:
            hero_hand: Hero's hole cards
            board: Community cards dealt so far
            villain_range: Estimated villain hand range (list of possible hands)
            num_simulations: Number of Monte Carlo simulations
        """
        if len(board) == 5:  # River - no more cards to come
            return self.calculate_showdown_equity(hero_hand, board, villain_range)
        
        # Create deck without known cards
        deck = self.create_deck()
        used_cards = set(hero_hand + board)
        available_cards = [card for card in deck if card not in used_cards]
        
        wins = 0
        total_hands = 0
        
        for _ in range(num_simulations):
            # Deal remaining board cards
            remaining_board_cards = 5 - len(board)
            if remaining_board_cards > 0:
                board_completion = random.sample(available_cards, remaining_board_cards)
                full_board = board + board_completion
                remaining_deck = [card for card in available_cards if card not in board_completion]
            else:
                full_board = board
                remaining_deck = available_cards
            
            # Sample villain hand
            if len(remaining_deck) >= 2:
                villain_hand = random.sample(remaining_deck, 2)
                
                # Evaluate both hands
                try:
                    hero_score, _ = evaluate_hand(hero_hand, full_board)
                    villain_score, _ = evaluate_hand(villain_hand, full_board)
                    
                    if hero_score < villain_score:  # Lower score wins in treys
                        wins += 1
                    elif hero_score == villain_score:
                        wins += 0.5  # Split pot
                    
                    total_hands += 1
                except:
                    continue
        
        return wins / total_hands if total_hands > 0 else 0.5
    
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
        available_cards = [card for card in deck if card not in used_cards]
        
        if len(available_cards) < 2:
            return 0.5  # Not enough cards for opponent
        
        wins = 0
        total_hands = 0
        
        # If villain range is specified, use it; otherwise sample random hands
        if villain_range:
            villain_hands = villain_range
        else:
            # Generate all possible villain hands from remaining cards
            villain_hands = list(itertools.combinations(available_cards, 2))
        
        for villain_hand in villain_hands:
            # Skip if villain hand uses cards we know
            if any(card in used_cards for card in villain_hand):
                continue
                
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
        
        max_suit_count = max(suit_counts.values())
        flush_draw = max_suit_count == 4
        
        # Straight draw analysis
        unique_ranks = sorted(set(ranks))
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
                    if unique_ranks[i+2] - unique_ranks[i] == 4:  # Gap in middle
                        straight_draw = True
                        straight_outs = 4  # Gutshot
                        break
        
        # Count total outs
        outs = 0
        if flush_draw:
            outs += 9  # 9 flush cards remaining
        outs += straight_outs
        
        # Adjust for potential overlaps (flush + straight)
        if flush_draw and straight_draw:
            outs = min(outs, 15)  # Maximum realistic outs
        
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
            if board_suits.count(suit) >= 3:  # Possible flush
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
    
    def get_optimal_bet_size(self, hand_strength, board_texture, pot_size, stack_size, street):
        """
        Calculate optimal bet size based on hand strength and board texture
        
        Args:
            hand_strength: 0-1 scale of hand strength
            board_texture: dict with board analysis
            pot_size: Current pot size
            stack_size: Effective stack size
            street: 'flop', 'turn', or 'river'
        """
        base_bet = pot_size * 0.67  # Standard 2/3 pot bet
        
        # Adjust based on hand strength
        if hand_strength >= 0.85:  # Nuts/near-nuts
            if street == 'river':
                return min(stack_size, pot_size * 1.0)  # Large value bet
            else:
                return min(stack_size, pot_size * 0.75)  # Build pot for later streets
        
        elif hand_strength >= 0.65:  # Strong hands
            return min(stack_size, base_bet)
        
        elif hand_strength >= 0.35:  # Medium hands
            return min(stack_size, pot_size * 0.5)  # Smaller value bet/protection
        
        else:  # Bluffs
            if board_texture.get('wet', False):
                return min(stack_size, pot_size * 0.75)  # Larger bluff on wet boards
            else:
                return min(stack_size, pot_size * 0.5)   # Smaller bluff on dry boards
    
    def should_bluff(self, hand, board, opponent_stats, pot_size, bet_size, street):
        """
        Determine if this is a good spot to bluff
        """
        # Basic bluff frequency based on street
        base_bluff_freq = {'flop': 0.25, 'turn': 0.20, 'river': 0.15}
        bluff_freq = base_bluff_freq.get(street, 0.15)
        
        # Adjust based on board texture
        if len(board) >= 3:
            board_suits = [card[1] for card in board]
            board_ranks = [card[0] for card in board]
            
            # More bluffing on wet boards
            if len(set(board_suits)) <= 2:  # Flush possible
                bluff_freq *= 1.2
            
            # Less bluffing on paired boards
            if len(set(board_ranks)) < len(board_ranks):
                bluff_freq *= 0.8
        
        # Adjust based on opponent tendencies
        fold_to_bet = opponent_stats.get('fold_to_bet', 0.5)
        bluff_freq *= (fold_to_bet / 0.5)  # Scale based on opponent's folding frequency
        
        # Blocker considerations
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
    strategy = PostflopStrategy()
    
    # Strong hands - bet for value
    if hand_strength >= 0.7 or equity >= 0.6:
        return 'bet'
    
    # Drawing hands with good odds
    elif equity >= 0.35 and pot_odds >= 2.5:
        return 'call'
    
    # Medium hands - check or small bet
    elif hand_strength >= 0.4:
        return 'check'
    
    # Weak hands - check or fold
    else:
        return 'check'
