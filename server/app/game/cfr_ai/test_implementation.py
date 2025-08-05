#!/usr/bin/env python3
"""
Test script to verify CFR implementation is working correctly
"""

import sys
import os
import time
import traceback

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

def test_imports():
    """Test that all modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        from config import get_config
        print("  ✅ Config imported")
        
        from game_abstraction import create_game_abstraction
        print("  ✅ Game abstraction imported")
        
        from information_set import create_information_set_manager
        print("  ✅ Information sets imported")
        
        from neural_networks import create_networks
        print("  ✅ Neural networks imported") 
        
        from cfr_trainer import create_trainer
        print("  ✅ CFR trainer imported")
        
        from deep_cfr import create_deep_cfr_trainer
        print("  ✅ Deep CFR imported")
        
        from cfr_bot import create_cfr_bot
        print("  ✅ CFR bot imported")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        traceback.print_exc()
        return False

def test_basic_functionality():
    """Test basic functionality of components"""
    print("\n🔧 Testing basic functionality...")
    
    try:
        from config import get_config
        from game_abstraction import create_game_abstraction
        from information_set import create_information_set_manager, GameState
        
        # Test config
        config = get_config(simplified=True)
        print(f"  ✅ Config created: {config.PREFLOP_BUCKETS} preflop buckets")
        
        # Test game abstraction
        abstraction = create_game_abstraction(config)
        bucket_info = abstraction.get_bucket_info()
        print(f"  ✅ Game abstraction created: {bucket_info['total_card_buckets']} total buckets")
        
        # Test information set manager
        info_manager = create_information_set_manager(abstraction)
        print(f"  ✅ Information set manager created")
        
        # Test creating a game state
        test_game_state = GameState(
            street='flop',
            board=['Ah', '5d', '9c'],
            pot=50,
            current_bet=20,
            players=[
                {'name': 'Player1', 'hand': ['Kh', 'Qd'], 'stack': 980, 'current_bet': 10, 'status': 'active'},
                {'name': 'Player2', 'hand': ['As', 'Ks'], 'stack': 970, 'current_bet': 20, 'status': 'active'}
            ],
            current_player=1,
            betting_history=['bet_0.5'],
            hand_history=[]
        )
        
        # Test information set creation
        info_set = info_manager.get_information_set(test_game_state, 1)
        print(f"  ✅ Information set created: {len(info_set.legal_actions)} legal actions")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Basic functionality test failed: {e}")
        traceback.print_exc()
        return False

def test_neural_networks():
    """Test neural network creation"""
    print("\n🧠 Testing neural networks...")
    
    try:
        # Try with PyTorch
        import torch
        print("  ✅ PyTorch available")
        
        from config import get_config
        from neural_networks import create_networks
        
        config = get_config(simplified=True)
        networks = create_networks(config, 'cpu')
        
        model_info = networks.get_model_info()
        print(f"  ✅ Networks created: {model_info['total_params']:,} parameters")
        
        # Test forward pass
        import numpy as np
        test_features = torch.randn(1, model_info['input_size'])
        
        value = networks.predict_value(test_features)
        print(f"  ✅ Value network forward pass: {value.item():.6f}")
        
        policy = networks.predict_policy(test_features)
        print(f"  ✅ Policy network forward pass: shape {policy.shape}")
        
        return True
        
    except ImportError:
        print("  ⚠️  PyTorch not available - will use tabular CFR only")
        return True
        
    except Exception as e:
        print(f"  ❌ Neural network test failed: {e}")
        traceback.print_exc()
        return False

def test_cfr_training():
    """Test basic CFR training"""
    print("\n🎯 Testing CFR training...")
    
    try:
        from cfr_trainer import create_trainer
        from config import get_config
        
        config = get_config(simplified=True)
        trainer = create_trainer(config, simplified=True)
        
        print(f"  ✅ Trainer created")
        
        # Run a few iterations
        print("  🔄 Running 10 training iterations...")
        start_time = time.time()
        
        for i in range(10):
            trainer.cfr_iteration()
        
        elapsed = time.time() - start_time
        print(f"  ✅ Training completed: {elapsed:.2f} seconds, {10/elapsed:.1f} it/s")
        
        # Check that information sets were created
        num_info_sets = len(trainer.info_set_manager.information_sets)
        print(f"  ✅ Created {num_info_sets} information sets")
        
        return True
        
    except Exception as e:
        print(f"  ❌ CFR training test failed: {e}")
        traceback.print_exc()
        return False

def test_cfr_bot():
    """Test CFR bot functionality"""
    print("\n🎮 Testing CFR bot...")
    
    try:
        from cfr_bot import create_cfr_bot
        
        bot = create_cfr_bot(simplified=True)
        bot_info = bot.get_bot_info()
        print(f"  ✅ Bot created: {bot_info['type']}")
        
        # Test decision making
        test_game_state = {
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
        
        action, amount = bot.decide_action(test_game_state)
        print(f"  ✅ Bot decision: {action} {amount}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ CFR bot test failed: {e}")
        traceback.print_exc()
        return False

def test_integration():
    """Test integration with existing game format"""
    print("\n🔗 Testing game integration...")
    
    try:
        from cfr_bot import decide_action_cfr
        
        # Test game state in existing format
        game_state = {
            'betting_round': 'preflop',
            'community': [],
            'pot': 30,
            'current_bet': 20,
            'current_player': 1,
            'players': [
                {'name': 'Human', 'hand': ['7h', '2d'], 'stack': 1000, 'current_bet': 10, 'status': 'active'},
                {'name': 'AI', 'hand': ['As', 'Kd'], 'stack': 980, 'current_bet': 20, 'status': 'active'}
            ],
            'action_history': []
        }
        
        action, amount = decide_action_cfr(game_state)
        print(f"  ✅ Integration test: {action} {amount}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Integration test failed: {e}")
        traceback.print_exc()
        return False

def run_all_tests():
    """Run all tests"""
    print("🚀 CFR Implementation Test Suite")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Basic Functionality", test_basic_functionality), 
        ("Neural Networks", test_neural_networks),
        ("CFR Training", test_cfr_training),
        ("CFR Bot", test_cfr_bot),
        ("Game Integration", test_integration),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
        except Exception as e:
            print(f"  ❌ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! CFR implementation is ready to use.")
        print("\n🚀 Next steps:")
        print("  1. Run: python train_cfr.py demo")
        print("  2. Train for longer: python train_cfr.py train --iterations 50000")  
        print("  3. Integrate with your poker game")
    else:
        print("❌ Some tests failed. Check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)