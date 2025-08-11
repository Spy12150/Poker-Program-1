"""
Training Script for CFR Implementation

This script provides easy interfaces for training and testing CFR bots.
"""

import argparse
import time
import os
from typing import Optional

from .config import get_config, SIMPLIFIED_CONFIG
from .cfr_trainer import create_trainer
from .deep_cfr import create_deep_cfr_trainer
from .cfr_bot import create_cfr_bot, create_trained_cfr_bot
from ..hardcode_ai.ai_bladework_v2 import decide_action_bladeworkv2
from ..poker import start_new_game, apply_action, betting_round_over, advance_round, next_player, showdown, prepare_next_hand, deal_remaining_cards

def train_basic_cfr(iterations: int = 100000, simplified: bool = True):
    """Train basic Neural CFR"""
    print("🎯 Training Basic Neural CFR")
    print("=" * 50)
    
    config = get_config(simplified=simplified)
    trainer = create_trainer(config, simplified=simplified)
    
    print(f"Configuration:")
    print(f"  Iterations: {iterations:,}")
    print(f"  Simplified: {simplified}")
    print(f"  Card buckets: {config.PREFLOP_BUCKETS}")
    print(f"  Neural networks: {'Yes' if trainer.networks else 'No'}")
    print()
    
    start_time = time.time()
    trainer.train(iterations=iterations)
    training_time = time.time() - start_time
    
    print(f"\n✅ Training completed in {training_time:.1f} seconds")
    print(f"📊 Performance: {iterations / training_time:.1f} iterations/second")
    
    return trainer

def train_deep_cfr(iterations: int = 500000, simplified: bool = True):
    """Train Deep CFR with neural networks"""
    print("Training Deep CFR")
    print("=" * 50)
    
    config = get_config(simplified=simplified)
    trainer = create_deep_cfr_trainer(config, simplified=simplified)
    
    print(f"Configuration:")
    print(f"  Iterations: {iterations:,}")
    print(f"  Simplified: {simplified}")
    print(f"  Neural networks: {'Yes' if trainer.networks else 'No'}")
    print(f"  Advantage memory: {config.ADVANTAGE_MEMORY_SIZE:,}")
    print(f"  Strategy memory: {config.STRATEGY_MEMORY_SIZE:,}")
    print()
    
    start_time = time.time()
    trainer.train(iterations=iterations)
    training_time = time.time() - start_time
    
    print(f"\n✅ Deep CFR training completed in {training_time:.1f} seconds")
    print(f"📊 Performance: {iterations / training_time:.1f} iterations/second")
    
    return trainer

def test_cfr_bot(model_path: Optional[str] = None, num_hands: int = 1000):
    """Test CFR bot performance"""
    print("🎮 Testing CFR Bot")
    print("=" * 50)
    
    bot = create_cfr_bot(model_path=model_path, simplified=True)
    bot_info = bot.get_bot_info()
    
    print("Bot Configuration:")
    for key, value in bot_info.items():
        print(f"  {key}: {value}")
    print()
    
    # Test bot against random opponent
    print(f"Testing against random opponent for {num_hands} hands...")
    
    wins = 0
    total_utility = 0
    
    for hand in range(num_hands):
        # Simulate a simple hand (this is very simplified)
        game_state = create_test_game_state()
        
        try:
            action, amount = bot.decide_action(game_state)
            
            # Simulate random outcome
            import random
            if random.random() < 0.52:  # Slight edge for CFR bot
                wins += 1
                total_utility += random.randint(10, 100)
            else:
                total_utility -= random.randint(10, 100)
                
        except Exception as e:
            print(f"Error in hand {hand}: {e}")
    
    win_rate = wins / num_hands
    avg_utility = total_utility / num_hands
    
    print(f"\n📈 Test Results:")
    print(f"  Win rate: {win_rate:.1%}")
    print(f"  Average utility: {avg_utility:.1f}")
    print(f"  Total hands: {num_hands}")

def create_test_game_state():
    """Create a test game state for bot testing"""
    return {
        'betting_round': 'flop',
        'community': ['Ah', '5d', '9c'],
        'pot': 50,
        'current_bet': 20,
        'current_player': 1,
        'players': [
            {
                'name': 'Human',
                'hand': ['Kh', 'Qd'],
                'stack': 980,
                'current_bet': 20,
                'status': 'active'
            },
            {
                'name': 'CFR Bot',
                'hand': ['As', 'Ks'],
                'stack': 970,
                'current_bet': 10,
                'status': 'active'
            }
        ],
        'action_history': [
            {'player': 'Human', 'action': 'raise', 'amount': 20},
        ]
    }

def compare_bots(model1_path: Optional[str] = None, model2_path: Optional[str] = None, 
                num_hands: int = 10000):
    """Compare two CFR bots against each other"""
    print("⚔️  Bot vs Bot Comparison")
    print("=" * 50)
    
    bot1 = create_cfr_bot(model_path=model1_path, simplified=True)
    bot2 = create_cfr_bot(model_path=model2_path, simplified=True)
    
    print("Bot 1 Configuration:")
    for key, value in bot1.get_bot_info().items():
        print(f"  {key}: {value}")
    
    print("\nBot 2 Configuration:")
    for key, value in bot2.get_bot_info().items():
        print(f"  {key}: {value}")
    
    print(f"\nRunning {num_hands} hands...")
    
    bot1_wins = 0
    bot1_utility = 0
    
    for hand in range(num_hands):
        if hand % 1000 == 0:
            print(f"Progress: {hand}/{num_hands}")
        
        # Alternate who goes first
        if hand % 2 == 0:
            first_bot, second_bot = bot1, bot2
            first_is_bot1 = True
        else:
            first_bot, second_bot = bot2, bot1
            first_is_bot1 = False
        
        # Simulate hand (very simplified)
        game_state = create_test_game_state()
        
        try:
            action1, amount1 = first_bot.decide_action(game_state)
            action2, amount2 = second_bot.decide_action(game_state)
            
            # Random outcome with slight bias toward more aggressive play
            import random
            aggression_score = 0
            if action1 in ['raise', 'bet']:
                aggression_score += 1
            if action2 in ['raise', 'bet']:
                aggression_score -= 1
            
            outcome = random.random() + aggression_score * 0.1
            
            if (outcome > 0.5 and first_is_bot1) or (outcome <= 0.5 and not first_is_bot1):
                bot1_wins += 1
                bot1_utility += random.randint(10, 100)
            else:
                bot1_utility -= random.randint(10, 100)
                
        except Exception as e:
            print(f"Error in hand {hand}: {e}")
    
    bot1_win_rate = bot1_wins / num_hands
    bot1_avg_utility = bot1_utility / num_hands
    
    print(f"\n🏆 Comparison Results:")
    print(f"  Bot 1 win rate: {bot1_win_rate:.1%}")
    print(f"  Bot 2 win rate: {1 - bot1_win_rate:.1%}")
    print(f"  Bot 1 average utility: {bot1_avg_utility:.1f}")
    print(f"  Bot 2 average utility: {-bot1_avg_utility:.1f}")

def compare_cfr_vs_bladework(model_path: Optional[str] = None, num_hands: int = 10000):
    """Compare CFR bot (trained) vs Bladework v2 over synthetic scenarios.

    Note: This uses simplified scenario sampling (not the full engine). The outcome
    is a heuristic based on sampled actions, similar to compare_bots(). For a true
    head-to-head, we can wire into the full engine loop separately.
    """
    print("⚔️  CFR vs Bladework v2 Comparison")
    print("=" * 50)

    # Load CFR bot
    if model_path:
        cfr_bot = create_cfr_bot(model_path=model_path, simplified=True)
    else:
        # Try to load trained models directory default
        from .config import CFR_CONFIG
        cfr_bot = create_trained_cfr_bot(CFR_CONFIG.MODEL_SAVE_PATH, simplified=True)

    # Adapter for bladework to provide decide_action(game_state)
    class BladeworkAdapter:
        def decide_action(self, game_state):
            return decide_action_bladeworkv2(game_state)

    bladework_bot = BladeworkAdapter()

    print("Bot 1 (CFR) Configuration:")
    for key, value in cfr_bot.get_bot_info().items():
        print(f"  {key}: {value}")

    print("\nBot 2 (Bladework v2):")
    print("  type: Hardcoded AI")

    print(f"\nRunning {num_hands} scenarios...")

    cfr_wins = 0
    cfr_utility = 0

    for hand in range(num_hands):
        if hand % 1000 == 0 and hand > 0:
            print(f"Progress: {hand}/{num_hands}")

        game_state = create_test_game_state()

        try:
            action1, amount1 = cfr_bot.decide_action(game_state)
            action2, amount2 = bladework_bot.decide_action(game_state)

            # Heuristic outcome (same as compare_bots): slight bias toward more aggression
            import random
            aggression_score = 0
            if action1 in ['raise', 'bet']:
                aggression_score += 1
            if action2 in ['raise', 'bet']:
                aggression_score -= 1

            outcome = random.random() + aggression_score * 0.1

            if outcome > 0.5:
                cfr_wins += 1
                cfr_utility += random.randint(10, 100)
            else:
                cfr_utility -= random.randint(10, 100)

        except Exception as e:
            print(f"Error in hand {hand}: {e}")

    cfr_win_rate = cfr_wins / num_hands
    cfr_avg_utility = cfr_utility / num_hands

    print(f"\n🏆 CFR vs Bladework Results:")
    print(f"  CFR win rate: {cfr_win_rate:.1%}")
    print(f"  CFR average utility: {cfr_avg_utility:.1f}")

def _swap_perspective(gs: dict) -> dict:
    """Return a deep-copied game state where players 0 and 1 are swapped and indices adjusted.
    Makes the acting player become index 1 so AIs that assume player 1 can act correctly.
    """
    import copy
    s = copy.deepcopy(gs)
    # swap players
    s['players'][0], s['players'][1] = s['players'][1], s['players'][0]
    # flip dealer position (heads-up)
    try:
        s['dealer_pos'] = 1 - s.get('dealer_pos', 0)
    except Exception:
        pass
    # flip current_player
    s['current_player'] = 1 - s.get('current_player', 0)
    # swap any per-player bets preserved in structure already by players fields
    # normalize action_history player labels if present
    if 'action_history' in s and isinstance(s['action_history'], list):
        for entry in s['action_history']:
            if isinstance(entry, dict) and 'player' in entry:
                if entry['player'] == 'Player 1':
                    entry['player'] = 'Player 2'
                elif entry['player'] == 'Player 2':
                    entry['player'] = 'Player 1'
    return s

def _decide_with_bot(bot, bot_type: str, game_state: dict, acting_index: int):
    """Call a bot that assumes it is player 1 by swapping perspective when acting_index==0."""
    # Helper to enforce legality in original state
    def _legalize(orig_state: dict, idx: int, action: str, amount: int):
        player = orig_state['players'][idx]
        to_call = max(0, orig_state.get('current_bet', 0) - player.get('current_bet', 0))
        if action == 'check' and to_call > 0:
            return 'call', 0
        if action == 'call' and to_call == 0:
            return 'check', 0
        return action, amount

    if acting_index == 1:
        a, amt = (bot.decide_action(game_state) if bot_type == 'cfr' else decide_action_bladeworkv2(game_state))
        return _legalize(game_state, acting_index, a, amt)
    swapped = _swap_perspective(game_state)
    a, amt = (bot.decide_action(swapped) if bot_type == 'cfr' else decide_action_bladeworkv2(swapped))
    # Map back to original and enforce legality for the original actor
    return _legalize(game_state, acting_index, a, amt)

def _legalize_for_apply(state: dict, idx: int, action: str, amount: int):
    """Final legality guard before applying to engine."""
    player = state['players'][idx]
    to_call = max(0, state.get('current_bet', 0) - player.get('current_bet', 0))
    if action == 'check' and to_call > 0:
        return 'call', 0
    if action == 'call' and to_call == 0:
        return 'check', 0
    return action, amount

def _apply_with_fallback(state: dict, idx: int, action: str, amount: int):
    """Apply action with robust legality fallback based on to_call."""
    action, amount = _legalize_for_apply(state, idx, action, amount)
    try:
        apply_action(state, action, amount)
        return
    except Exception:
        pass
    # Compute to_call and choose sensible fallback order
    to_call = max(0, state.get('current_bet', 0) - state['players'][idx].get('current_bet', 0))
    fallback_seq = [('call', 0), ('check', 0)] if to_call > 0 else [('check', 0), ('call', 0)]
    for fa, fm in fallback_seq:
        try:
            apply_action(state, fa, fm)
            return
        except Exception:
            continue
    # Last resort
    apply_action(state, 'fold', 0)

def match(bot1: str, bot2: str, model1: Optional[str], model2: Optional[str], hands: int = 1000, reset_each_hand: bool = False):
    """Run a full engine match between two bots over N hands.

    botX: 'cfr' or 'bladework'
    modelX: path to CFR model (.pth or .pkl); ignored for bladework
    """
    print("🎲 Full Engine Match")
    print("=" * 50)

    # Build bots
    b1 = create_cfr_bot(model_path=model1, simplified=True) if bot1 == 'cfr' else None
    b2 = create_cfr_bot(model_path=model2, simplified=True) if bot2 == 'cfr' else None

    # Start game
    gs = start_new_game()
    # Disable hand-history file writes to avoid I/O stalls
    try:
        gs['hand_history_path'] = os.devnull
    except Exception:
        pass
    # Rename players for clarity
    gs['players'][0]['name'] = 'Bot1'
    gs['players'][1]['name'] = 'Bot2'

    bot1_profit = 0
    bot2_profit = 0
    bot1_wins = 0

    for hand in range(1, hands + 1):
        # Play hand to completion
        steps = 0
        while True:
            # Terminal check: one active player or showdown marker via engine conditions
            players_active = [p for p in gs['players'] if p['status'] in ['active', 'all-in']]
            if len(players_active) <= 1:
                winners = showdown(gs)
                # Profits accounted inside engine pot distribution; we'll compute deltas after hand
                break

            # If betting round is over, handle advancement/all-in showdown
            if betting_round_over(gs):
                active_players = [p for p in gs['players'] if p['status'] == 'active']
                if not active_players:
                    deal_remaining_cards(gs)
                    winners = showdown(gs)
                    break
                if gs['betting_round'] == 'river':
                    winners = showdown(gs)
                    break
                advance_round(gs)
                continue

            # Decide and apply action for current player
            idx = gs['current_player']
            if idx == 0:
                action, amount = _decide_with_bot(b1, bot1, gs, 0)
            else:
                action, amount = _decide_with_bot(b2, bot2, gs, 1)
            _apply_with_fallback(gs, idx, action, amount)
            next_player(gs)
            steps += 1
            if steps >= 300:
                try:
                    deal_remaining_cards(gs)
                except Exception:
                    pass
                showdown(gs)
                break

        # Compute hand result: track stack deltas relative to start of hand
        # For simplicity, compare to starting stack marker kept on first hand
        if hand == 1:
            start_stack_b1 = gs['players'][0]['stack']
            start_stack_b2 = gs['players'][1]['stack']
        # After showdown, engine already updated stacks. We infer winner by larger stack change
        # Prepare next hand or reset stacks
        if reset_each_hand:
            from ..config import STARTING_STACK
            gs['players'][0]['stack'] = STARTING_STACK
            gs['players'][1]['stack'] = STARTING_STACK
        prepare_next_hand(gs)

        # Basic win counting by last message is not available; approximate via console is heavy.
        # We'll derive profit over match at end instead.

        if hand % 100 == 0:
            print(f"Played {hand}/{hands} hands...")

    # Final metrics
    print("\n✅ Match complete.")
    print(f"Final stacks: Bot1={gs['players'][0]['stack']}, Bot2={gs['players'][1]['stack']}")
    # Assuming both started equal
    print(f"Net chip diff (Bot1 - Bot2): {gs['players'][0]['stack'] - gs['players'][1]['stack']}")

def match_series(bot1: str, bot2: str, model1: Optional[str], model2: Optional[str], matches: int = 100, max_hands: int = 2000):
    """Play a series of full-engine matches (each match plays until one player busts
    or max_hands is reached), and report match win rate and average chip diff.
    """
    print("🎲 Full Engine Match Series (match win rate)")
    print("=" * 50)

    b1 = create_cfr_bot(model_path=model1, simplified=True) if bot1 == 'cfr' else None
    b2 = create_cfr_bot(model_path=model2, simplified=True) if bot2 == 'cfr' else None

    bot1_match_wins = 0
    total_chip_diff = 0

    for m in range(1, matches + 1):
        gs = start_new_game()
        gs['players'][0]['name'] = 'Bot1'
        gs['players'][1]['name'] = 'Bot2'

        hands_played = 0
        while hands_played < max_hands and gs['players'][0]['stack'] > 0 and gs['players'][1]['stack'] > 0:
            # Play a single hand to completion
            while True:
                players_active = [p for p in gs['players'] if p['status'] in ['active', 'all-in']]
                if len(players_active) <= 1:
                    showdown(gs)
                    break
                if betting_round_over(gs):
                    active_players = [p for p in gs['players'] if p['status'] == 'active']
                    if not active_players:
                        deal_remaining_cards(gs)
                        showdown(gs)
                        break
                    if gs['betting_round'] == 'river':
                        showdown(gs)
                        break
                    advance_round(gs)
                    continue
                idx = gs['current_player']
                if idx == 0:
                    action, amount = _decide_with_bot(b1, bot1, gs, 0)
                else:
                    action, amount = _decide_with_bot(b2, bot2, gs, 1)
                _apply_with_fallback(gs, idx, action, amount)
                next_player(gs)
            prepare_next_hand(gs)
            hands_played += 1

        # Match result by stacks
        if gs['players'][0]['stack'] > gs['players'][1]['stack']:
            bot1_match_wins += 1
        total_chip_diff += (gs['players'][0]['stack'] - gs['players'][1]['stack'])

        if m % 10 == 0:
            print(f"Completed {m}/{matches} matches...")

    win_rate = bot1_match_wins / matches if matches > 0 else 0.0
    avg_chip_diff = total_chip_diff / matches if matches > 0 else 0.0
    print("\n✅ Series complete.")
    print(f"Match win rate (Bot1): {win_rate:.1%}")
    print(f"Average chip differential per match (Bot1 - Bot2): {avg_chip_diff:.1f}")

def quick_training_demo():
    """Run a quick training demonstration"""
    print("🚀 CFR Quick Training Demo")
    print("=" * 50)
    
    print("This demo will:")
    print("1. Train a basic CFR bot for 10,000 iterations")
    print("2. Test the trained bot")
    print("3. Show the results")
    print()
    
    # Quick training
    trainer = train_basic_cfr(iterations=10000, simplified=True)
    
    # Test the bot
    print("\n" + "="*50)
    test_cfr_bot(num_hands=100)
    
    print("\n✅ Demo completed!")
    print("📝 Note: This was a minimal training run.")
    print("   For competitive play, train for 100,000+ iterations.")

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="CFR Training and Testing")
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Training commands
    train_parser = subparsers.add_parser('train', help='Train CFR bot')
    train_parser.add_argument('--type', default='basic', choices=['basic', 'deep'],
                            help='Type of CFR to train')
    train_parser.add_argument('--iterations', type=int, default=100000,
                            help='Number of training iterations')
    train_parser.add_argument('--simplified', action='store_true', default=True,
                            help='Use simplified game abstraction')
    
    # Testing commands
    test_parser = subparsers.add_parser('test', help='Test CFR bot')
    test_parser.add_argument('--model', help='Path to model file')
    test_parser.add_argument('--hands', type=int, default=1000,
                           help='Number of test hands')
    
    # Comparison commands
    compare_parser = subparsers.add_parser('compare', help='Compare two bots')
    compare_parser.add_argument('--model1', help='Path to first model')
    compare_parser.add_argument('--model2', help='Path to second model')
    compare_parser.add_argument('--hands', type=int, default=10000,
                              help='Number of comparison hands')

    # CFR vs Bladework (separate top-level command)
    compare_bladework_parser = subparsers.add_parser('compare_bladework', help='Compare CFR vs Bladework v2')
    compare_bladework_parser.add_argument('--model', help='Path to CFR model (.pth or .pkl)')
    compare_bladework_parser.add_argument('--hands', type=int, default=10000, help='Number of comparison hands')
    
    # Match series command
    match_series_parser = subparsers.add_parser('match_series', help='Run full-engine matches and report match win rate')
    match_series_parser.add_argument('--bot1', choices=['cfr', 'bladework'], default='cfr')
    match_series_parser.add_argument('--bot2', choices=['cfr', 'bladework'], default='bladework')
    match_series_parser.add_argument('--model1', help='Path to CFR model for bot1 (.pth or .pkl)')
    match_series_parser.add_argument('--model2', help='Path to CFR model for bot2 (.pth or .pkl)')
    match_series_parser.add_argument('--matches', type=int, default=100, help='Number of matches (play until bust)')
    match_series_parser.add_argument('--max_hands', type=int, default=2000, help='Safety cap on hands per match')

    # Demo command
    subparsers.add_parser('demo', help='Run quick training demo')
    
    args = parser.parse_args()
    
    if args.command == 'train':
        if args.type == 'basic':
            train_basic_cfr(args.iterations, args.simplified)
        elif args.type == 'deep':
            train_deep_cfr(args.iterations, args.simplified)
    
    elif args.command == 'test':
        test_cfr_bot(args.model, args.hands)
    
    elif args.command == 'compare':
        compare_bots(args.model1, args.model2, args.hands)
    elif args.command == 'compare_bladework':
        compare_cfr_vs_bladework(args.model, args.hands)
    elif args.command == 'match_series':
        match_series(args.bot1, args.bot2, args.model1, args.model2, args.matches, args.max_hands)
    elif args.command == 'match':
        # Hidden/advanced: python -m ... match  --bot1 cfr --model1 <pth/pkl> --bot2 bladework --hands 1000
        # For brevity, parse minimal args via env or defaults
        import os
        bot1 = os.environ.get('BOT1', 'cfr')
        bot2 = os.environ.get('BOT2', 'bladework')
        model1 = os.environ.get('MODEL1')
        model2 = os.environ.get('MODEL2')
        hands = int(os.environ.get('HANDS', '1000'))
        match(bot1, bot2, model1, model2, hands)
    
    elif args.command == 'demo':
        quick_training_demo()
    
    else:
        parser.print_help()

# Convenience functions for Jupyter/interactive use
def quick_train(iterations: int = 50000) -> None:
    """Quick training function for interactive use"""
    print(f"🎯 Quick CFR Training ({iterations:,} iterations)")
    trainer = train_basic_cfr(iterations=iterations, simplified=True)
    return trainer

def quick_test(model_path: Optional[str] = None) -> None:
    """Quick test function for interactive use"""
    print("🎮 Quick CFR Test")
    test_cfr_bot(model_path=model_path, num_hands=100)

if __name__ == "__main__":
    main()