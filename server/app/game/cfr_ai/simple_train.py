#!/usr/bin/env python3
"""
Simple CFR Training Script
Works with absolute imports and provides easy interface for training
"""

import random
import time
import numpy as np

def quick_demo():
    """Run a quick CFR training demo"""
    print("🚀 CFR Quick Training Demo")
    print("=" * 50)
    
    # Import with error handling
    try:
        from config import get_config
        from game_abstraction import create_game_abstraction
        from information_set import create_information_set_manager, GameState
        from neural_networks import create_networks
        import torch
        
        # Setup
        config = get_config(simplified=True)
        abstraction = create_game_abstraction(config)
        info_manager = create_information_set_manager(abstraction)
        networks = create_networks(config, 'cpu')
        
        print(f"✅ Setup complete")
        print(f"  • Card buckets: {abstraction.get_bucket_info()['total_card_buckets']}")
        print(f"  • Network parameters: {networks.get_model_info()['total_params']:,}")
        
        # Run simple CFR iterations
        print(f"\n🎯 Running simplified CFR training...")
        
        start_time = time.time()
        num_iterations = 1000
        
        for iteration in range(num_iterations):
            # Create random game situation
            game_state = create_random_game_state()
            
            # Get information sets for both players
            for player in [0, 1]:
                info_set = info_manager.get_information_set(game_state, player)
                
                # Simple regret update (simplified CFR)
                utilities = simulate_action_utilities(info_set.legal_actions)
                info_set.update_regrets(utilities, 1.0)  # Simplified reach probability
                info_set.update_strategy_sum(1.0)
            
            if (iteration + 1) % 200 == 0:
                elapsed = time.time() - start_time
                rate = (iteration + 1) / elapsed
                print(f"  Iteration {iteration + 1:,} ({rate:.0f} it/s)")
        
        elapsed = time.time() - start_time
        print(f"\n✅ Training completed in {elapsed:.1f} seconds")
        print(f"📊 Final stats:")
        print(f"  • Information sets created: {len(info_manager.information_sets):,}")
        print(f"  • Training rate: {num_iterations / elapsed:.0f} iterations/second")
        
        # Test the learned strategy
        print(f"\n🎮 Testing learned strategies...")
        test_strategy_quality(info_manager)
        
        return info_manager
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Try running: source cfr_venv/bin/activate")
        return None
    except Exception as e:
        print(f"❌ Training error: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_random_game_state():
    """Create a random game state for training"""
    streets = ['preflop', 'flop', 'turn', 'river']
    street = random.choice(streets)
    
    # Generate random cards
    suits = ['s', 'h', 'd', 'c']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
    deck = [r + s for r in ranks for s in suits]
    random.shuffle(deck)
    
    # Deal cards
    player_hands = [[deck.pop(), deck.pop()] for _ in range(2)]
    
    # Community cards based on street
    board = []
    if street in ['flop', 'turn', 'river']:
        board.extend([deck.pop(), deck.pop(), deck.pop()])
    if street in ['turn', 'river']:
        board.append(deck.pop())
    if street == 'river':
        board.append(deck.pop())
    
    # Create players
    players = [
        {
            'name': f'Player {i}',
            'hand': player_hands[i],
            'stack': random.randint(500, 2000),
            'current_bet': random.randint(0, 50),
            'status': 'active'
        }
        for i in range(2)
    ]
    
    # Random betting history
    actions = ['check', 'call', 'bet_0.5', 'bet_1.0', 'raise_2.5']
    history_length = random.randint(0, 3)
    betting_history = [random.choice(actions) for _ in range(history_length)]
    
    from information_set import GameState
    return GameState(
        street=street,
        board=board,
        pot=random.randint(20, 200),
        current_bet=random.randint(0, 50),
        players=players,
        current_player=random.randint(0, 1),
        betting_history=betting_history,
        hand_history=[]
    )

def simulate_action_utilities(legal_actions):
    """Simulate utilities for actions (simplified)"""
    utilities = {}
    for action in legal_actions:
        # Random utilities with some bias based on action type
        if action == 'fold':
            utilities[action] = random.uniform(-50, 0)
        elif action == 'call':
            utilities[action] = random.uniform(-20, 30)
        elif 'bet' in action or 'raise' in action:
            utilities[action] = random.uniform(-30, 50)
        else:
            utilities[action] = random.uniform(-10, 10)
    
    return utilities

def test_strategy_quality(info_manager):
    """Test quality of learned strategies"""
    if not info_manager.information_sets:
        print("  ❌ No strategies learned")
        return
    
    # Sample some information sets
    sample_size = min(5, len(info_manager.information_sets))
    sample_keys = random.sample(list(info_manager.information_sets.keys()), sample_size)
    
    print(f"  📊 Sample strategies from {sample_size} information sets:")
    
    for i, key in enumerate(sample_keys):
        info_set = info_manager.information_sets[key]
        strategy = info_set.get_average_strategy()
        
        if strategy:
            # Find most probable action
            best_action = max(strategy, key=strategy.get)
            best_prob = strategy[best_action]
            
            print(f"    {i+1}. {best_action}: {best_prob:.1%} (vs {len(info_set.legal_actions)} actions)")
        else:
            print(f"    {i+1}. No strategy learned")

def neural_training_demo():
    """Demo with neural network training"""
    print("🧠 Neural CFR Training Demo")
    print("=" * 50)
    
    try:
        import torch
        from config import get_config
        from game_abstraction import create_game_abstraction
        from information_set import create_information_set_manager
        from neural_networks import create_networks
        
        config = get_config(simplified=True)
        abstraction = create_game_abstraction(config)
        info_manager = create_information_set_manager(abstraction)
        networks = create_networks(config, 'cpu')
        
        print("✅ Neural networks initialized")
        
        # Generate training data
        print("📊 Generating training data...")
        training_data = []
        
        for _ in range(100):
            game_state = create_random_game_state()
            info_set = info_manager.get_information_set(game_state, 0)
            
            # Create training sample
            features = torch.tensor(info_set.features).unsqueeze(0)
            target_value = random.uniform(-50, 50)  # Simulated value
            
            training_data.append((features, target_value))
        
        # Train value network
        print("🎯 Training value network...")
        total_loss = 0
        
        for features, target in training_data[:50]:  # Use first 50 samples
            target_tensor = torch.tensor([target], dtype=torch.float32)
            loss = networks.train_value_network(features, target_tensor)
            total_loss += loss
        
        avg_loss = total_loss / 50
        print(f"✅ Value network trained, average loss: {avg_loss:.6f}")
        
        # Test prediction
        test_features, _ = training_data[0]
        prediction = networks.predict_value(test_features)
        print(f"🔮 Sample prediction: {prediction.item():.2f}")
        
        return networks
        
    except Exception as e:
        print(f"❌ Neural training failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def interactive_test():
    """Interactive test for bot decisions"""
    print("🎮 Interactive CFR Bot Test")
    print("=" * 50)
    
    try:
        from cfr_bot import CFRBot
        
        bot = CFRBot(simplified=True)
        print("✅ CFR bot created")
        
        # Test decision making
        test_scenarios = [
            {
                'name': 'Preflop with strong hand',
                'state': {
                    'betting_round': 'preflop',
                    'community': [],
                    'pot': 30,
                    'current_bet': 20,
                    'current_player': 1,
                    'players': [
                        {'name': 'Human', 'hand': ['7h', '2d'], 'stack': 1000, 'current_bet': 10, 'status': 'active'},
                        {'name': 'CFR Bot', 'hand': ['As', 'Kd'], 'stack': 980, 'current_bet': 20, 'status': 'active'}
                    ],
                    'action_history': []
                }
            },
            {
                'name': 'Flop with top pair',
                'state': {
                    'betting_round': 'flop',
                    'community': ['Ah', '5d', '9c'],
                    'pot': 50,
                    'current_bet': 20,
                    'current_player': 1,
                    'players': [
                        {'name': 'Human', 'hand': ['Kh', 'Qd'], 'stack': 980, 'current_bet': 20, 'status': 'active'},
                        {'name': 'CFR Bot', 'hand': ['As', 'Ks'], 'stack': 970, 'current_bet': 10, 'status': 'active'}
                    ],
                    'action_history': [{'player': 'Human', 'action': 'raise', 'amount': 20}]
                }
            }
        ]
        
        for scenario in test_scenarios:
            print(f"\n🎯 {scenario['name']}:")
            try:
                action, amount = bot.decide_action(scenario['state'])
                print(f"  🤖 Bot decision: {action} {amount}")
            except Exception as e:
                print(f"  ❌ Decision failed: {e}")
        
        return bot
        
    except Exception as e:
        print(f"❌ Interactive test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main function for command line usage"""
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'demo':
            quick_demo()
        elif command == 'neural':
            neural_training_demo()
        elif command == 'test':
            interactive_test()
        elif command == 'all':
            print("🚀 Running all CFR demos")
            print("=" * 60)
            
            print("\n1️⃣ Basic CFR Demo:")
            quick_demo()
            
            print("\n2️⃣ Neural Training Demo:")
            neural_training_demo()
            
            print("\n3️⃣ Interactive Bot Test:")
            interactive_test()
            
            print("\n✅ All demos completed!")
        else:
            print("Usage: python simple_train.py [demo|neural|test|all]")
    else:
        print("🎯 CFR Training Options:")
        print("  python simple_train.py demo    - Quick CFR training demo")  
        print("  python simple_train.py neural  - Neural network training demo")
        print("  python simple_train.py test    - Interactive bot testing")
        print("  python simple_train.py all     - Run all demos")

if __name__ == "__main__":
    main()