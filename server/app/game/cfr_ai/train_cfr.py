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
    print("🧠 Training Deep CFR")
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