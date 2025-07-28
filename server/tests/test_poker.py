"""
Comprehensive test suite for poker game logic
Run with: python -m pytest tests/test_poker.py -v
"""

import pytest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.game.poker import (
    create_deck, deal_cards, init_players, start_new_game,
    apply_action, betting_round_over, advance_round, showdown,
    post_blinds, prepare_next_hand
)
from app.game.hand_eval_lib import evaluate_hand

class TestPokerBasics:
    
    def test_create_deck(self):
        """Test deck creation"""
        deck = create_deck()
        assert len(deck) == 52
        assert 'As' in deck
        assert 'Kh' in deck
        assert '2c' in deck
        
    def test_deal_cards(self):
        """Test card dealing"""
        deck = create_deck()
        hands = deal_cards(deck, 2)
        assert len(hands) == 2
        assert len(hands[0]) == 2
        assert len(hands[1]) == 2
        assert len(deck) == 48  # 52 - 4 dealt cards
        
    def test_init_players(self):
        """Test player initialization"""
        players = init_players(2, 1000)
        assert len(players) == 2
        assert players[0]['stack'] == 1000
        assert players[0]['status'] == 'active'
        assert players[0]['current_bet'] == 0

class TestGameFlow:
    
    def test_start_new_game(self):
        """Test game initialization"""
        game = start_new_game()
        assert len(game['players']) == 2
        assert len(game['deck']) == 48  # 52 - 4 dealt
        assert game['pot'] > 0  # Should have blinds
        assert game['betting_round'] == 'preflop'
        
    def test_post_blinds(self):
        """Test blind posting"""
        game = start_new_game()
        # Check that blinds were posted
        sb_player = game['players'][(game['dealer_pos'] + 1) % 2]
        bb_player = game['players'][(game['dealer_pos'] + 2) % 2]
        
        # One should have small blind, other big blind
        bets = [p['current_bet'] for p in game['players']]
        assert 10 in bets  # Small blind
        assert 20 in bets  # Big blind
        assert game['pot'] == 30  # Total blinds
        
    def test_apply_action_fold(self):
        """Test folding action"""
        game = start_new_game()
        current_player = game['current_player']
        
        apply_action(game, 'fold')
        assert game['players'][current_player]['status'] == 'folded'
        
    def test_apply_action_call(self):
        """Test calling action"""
        game = start_new_game()
        current_player = game['current_player']
        initial_stack = game['players'][current_player]['stack']
        to_call = game['current_bet'] - game['players'][current_player]['current_bet']
        
        apply_action(game, 'call')
        
        expected_stack = initial_stack - to_call
        assert game['players'][current_player]['stack'] == expected_stack
        assert game['players'][current_player]['current_bet'] == game['current_bet']
        
    def test_apply_action_raise(self):
        """Test raising action"""
        game = start_new_game()
        current_player = game['current_player']
        initial_stack = game['players'][current_player]['stack']
        
        raise_amount = 100
        apply_action(game, 'raise', raise_amount)
        
        assert game['players'][current_player]['current_bet'] == raise_amount
        assert game['current_bet'] == raise_amount
        
    def test_betting_round_over(self):
        """Test betting round completion detection"""
        game = start_new_game()
        
        # Not over initially
        assert not betting_round_over(game)
        
        # Fold one player
        apply_action(game, 'fold')
        assert betting_round_over(game)  # Only one active player left
        
    def test_advance_round(self):
        """Test round advancement"""
        game = start_new_game()
        assert game['betting_round'] == 'preflop'
        assert len(game['community']) == 0
        
        advance_round(game)
        assert game['betting_round'] == 'flop'
        assert len(game['community']) == 3
        
        advance_round(game)
        assert game['betting_round'] == 'turn'
        assert len(game['community']) == 4
        
        advance_round(game)
        assert game['betting_round'] == 'river'
        assert len(game['community']) == 5

class TestHandEvaluation:
    
    def test_evaluate_royal_flush(self):
        """Test royal flush evaluation"""
        hand = ['As', 'Ks']
        board = ['Qs', 'Js', 'Ts', '2h', '3c']
        score, hand_class = evaluate_hand(hand, board)
        assert hand_class == 'Straight Flush'
        assert score == 1  # Royal flush should be score 1
        
    def test_evaluate_high_card(self):
        """Test high card evaluation"""
        hand = ['2s', '7h']
        board = ['9d', 'Jc', 'Ac', '4h', '6s']
        score, hand_class = evaluate_hand(hand, board)
        assert hand_class == 'High Card'
        assert score > 7000  # High card should have high score
        
    def test_evaluate_pair(self):
        """Test pair evaluation"""
        hand = ['As', 'Ah']
        board = ['2d', '7c', '9s', 'Jh', 'Kc']
        score, hand_class = evaluate_hand(hand, board)
        assert hand_class == 'Pair'

class TestShowdown:
    
    def test_showdown_one_player(self):
        """Test showdown with one player remaining"""
        game = start_new_game()
        initial_pot = game['pot']
        
        # Fold player 0
        game['current_player'] = 0
        apply_action(game, 'fold')
        
        winners = showdown(game)
        assert len(winners) == 1
        assert winners[0]['name'] == 'Player 2'
        
    def test_showdown_two_players(self):
        """Test showdown with two players"""
        game = start_new_game()
        
        # Set up known hands for testing
        game['players'][0]['hand'] = ['As', 'Ah']  # Pair of aces
        game['players'][1]['hand'] = ['Ks', 'Kh']  # Pair of kings
        game['community'] = ['2d', '7c', '9s', 'Jh', 'Qc']
        
        winners = showdown(game)
        assert len(winners) == 1
        assert winners[0]['name'] == 'Player 1'  # Aces should beat kings

class TestEdgeCases:
    
    def test_all_in_scenarios(self):
        """Test all-in scenarios"""
        game = start_new_game()
        current_player = game['current_player']
        
        # Make player go all-in
        stack = game['players'][current_player]['stack']
        apply_action(game, 'raise', stack + game['players'][current_player]['current_bet'])
        
        assert game['players'][current_player]['stack'] == 0
        assert game['players'][current_player]['status'] == 'all-in'
        
    def test_minimum_raise_enforcement(self):
        """Test minimum raise enforcement"""
        game = start_new_game()
        current_player = game['current_player']
        
        # Try to make a tiny raise
        small_raise = game['current_bet'] + 1
        apply_action(game, 'raise', small_raise)
        
        # Should be raised to minimum
        assert game['players'][current_player]['current_bet'] >= 40  # 2x big blind
        
    def test_prepare_next_hand(self):
        """Test preparing for next hand"""
        game = start_new_game()
        original_dealer = game['dealer_pos']
        
        prepare_next_hand(game)
        
        # Dealer should advance
        assert game['dealer_pos'] == (original_dealer + 1) % 2
        
        # Game state should reset
        assert len(game['community']) == 0
        assert game['betting_round'] == 'preflop'
        assert game['pot'] == 30  # Just blinds
        
        # Players should have new hands
        for player in game['players']:
            assert len(player['hand']) == 2
            assert player['status'] == 'active'

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
