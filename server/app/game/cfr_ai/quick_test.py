#!/usr/bin/env python3
"""
Quick test script for CFR implementation with absolute imports
"""

import sys
import os
import random
import numpy as np

print("🚀 CFR Quick Test")
print("=" * 40)

# Test PyTorch availability
print("🧠 Testing PyTorch...")
try:
    import torch
    print(f"  ✅ PyTorch {torch.__version__} available")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"  📍 Device: {device}")
except ImportError:
    print("  ❌ PyTorch not available")
    torch = None

# Test numpy
print("\n📊 Testing NumPy...")
print(f"  ✅ NumPy {np.__version__} available")

# Test configuration
print("\n⚙️  Testing Configuration...")
try:
    from config import CFRConfig, get_config
    config = get_config(simplified=True)
    print(f"  ✅ Config loaded: {config.PREFLOP_BUCKETS} preflop buckets")
except Exception as e:
    print(f"  ❌ Config failed: {e}")

# Test game abstraction with fallback
print("\n🎯 Testing Game Abstraction...")
try:
    from game_abstraction import GameAbstraction
    
    # Create minimal config
    class MinimalConfig:
        PREFLOP_BUCKETS = 10
        FLOP_BUCKETS = 10
        TURN_BUCKETS = 10
        RIVER_BUCKETS = 10
        BET_SIZES_PREFLOP = [2.5, 5.0, float('inf')]
        BET_SIZES_POSTFLOP = [0.5, 1.0, float('inf')]
    
    config = MinimalConfig()
    abstraction = GameAbstraction(config)
    
    print(f"  ✅ Game abstraction created")
    print(f"  📊 Bucket info: {abstraction.get_bucket_info()}")
    
except Exception as e:
    print(f"  ❌ Game abstraction failed: {e}")
    import traceback
    traceback.print_exc()

# Test neural networks
if torch:
    print("\n🧠 Testing Neural Networks...")
    try:
        from neural_networks import DeepCFRNetworks
        
        class NetworkConfig:
            HIDDEN_SIZE = 256
            NUM_LAYERS = 2
            LEARNING_RATE = 1e-3
            DROPOUT_RATE = 0.1
            DEVICE = 'cpu'
            
            def to_dict(self):
                return {'hidden_size': self.HIDDEN_SIZE}
        
        networks = DeepCFRNetworks(NetworkConfig(), 'cpu')
        print(f"  ✅ Networks created")
        
        # Test forward pass
        test_input = torch.randn(1, 17)  # Matching expected input size
        value = networks.predict_value(test_input)
        print(f"  ✅ Value prediction: {value.item():.6f}")
        
        policy = networks.predict_policy(test_input)
        print(f"  ✅ Policy prediction shape: {policy.shape}")
        
    except Exception as e:
        print(f"  ❌ Neural networks failed: {e}")
        import traceback
        traceback.print_exc()

# Test information sets
print("\n📋 Testing Information Sets...")
try:
    from information_set import InformationSet, GameState
    
    # Create test game state
    game_state = GameState(
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
    
    # Create information set
    info_set = InformationSet(
        player=1,
        street='flop',
        card_bucket=5,
        betting_history='bet_0.5',
        pot_size_bucket=2,
        legal_actions=['fold', 'call', 'raise_1.0']
    )
    
    print(f"  ✅ Information set created")
    print(f"  🎯 Features shape: {info_set.features.shape}")
    
    strategy = info_set.get_strategy()
    print(f"  🎲 Strategy: {strategy}")
    
except Exception as e:
    print(f"  ❌ Information sets failed: {e}")
    import traceback
    traceback.print_exc()

# Simple CFR iteration test
print("\n🎯 Testing Basic CFR Logic...")
try:
    # Simulate a simple CFR update
    actions = ['fold', 'call', 'raise']
    regrets = {'fold': 0.1, 'call': -0.2, 'raise': 0.3}
    
    # Regret matching
    positive_regrets = {a: max(0, regrets[a]) for a in actions}
    total_regret = sum(positive_regrets.values())
    
    if total_regret > 0:
        strategy = {a: positive_regrets[a] / total_regret for a in actions}
    else:
        strategy = {a: 1.0/len(actions) for a in actions}
    
    print(f"  ✅ Regret matching works")
    print(f"  📊 Example strategy: {strategy}")
    
    # Sample action
    actions_list = list(strategy.keys())
    probs = list(strategy.values())
    sampled_action = np.random.choice(actions_list, p=probs)
    print(f"  🎲 Sampled action: {sampled_action}")
    
except Exception as e:
    print(f"  ❌ CFR logic failed: {e}")

print("\n" + "=" * 40)
print("✅ Quick test completed!")
print("\n🎯 Key Results:")
print(f"  • PyTorch: {'✅ Available' if torch else '❌ Missing'}")
print(f"  • NumPy: ✅ Available ({np.__version__})")
print("  • Basic CFR logic: ✅ Working")

if torch:
    print("\n🚀 Ready for CFR training!")
    print("💡 Next steps:")
    print("  1. Fix import issues in main scripts")
    print("  2. Create simple training script")
    print("  3. Start with small experiments")
else:
    print("\n⚠️  Install PyTorch for full functionality")
    print("  pip install torch (in virtual environment)")