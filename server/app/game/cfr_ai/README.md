# Neural CFR Implementation

A complete implementation of Counterfactual Regret Minimization with neural network approximation for learning optimal poker strategies.

## 🚀 Quick Start

### Basic Training
```python
# Run in Python shell or Jupyter notebook
import sys
sys.path.append('server/app/game/cfr_ai')

from train_cfr import quick_train, quick_test

# Train for 50,000 iterations (takes ~5-10 minutes)
trainer = quick_train(50000)

# Test the trained bot
quick_test()
```

### Command Line Interface
```bash
cd server/app/game/cfr_ai

# Run quick demo
python train_cfr.py demo

# Train basic CFR
python train_cfr.py train --type basic --iterations 100000

# Train Deep CFR 
python train_cfr.py train --type deep --iterations 500000

# Test trained bot
python train_cfr.py test --model models/final_networks.pth --hands 1000

# Compare two bots
python train_cfr.py compare --model1 models/checkpoint_50000.pth --model2 models/checkpoint_100000.pth
```

## 🏗️ Architecture

### Core Components

1. **Game Abstraction** (`game_abstraction.py`)
   - Card abstraction using tier system
   - Bet size abstraction 
   - Reduces game complexity from ~10^160 to manageable size

2. **Information Sets** (`information_set.py`)
   - Represents game states indistinguishable to players
   - Handles regret matching and strategy updates
   - Feature encoding for neural networks

3. **Neural Networks** (`neural_networks.py`)
   - Value Network: Approximates counterfactual values
   - Advantage Network: Approximates regrets
   - Policy Network: Approximates strategies

4. **CFR Trainer** (`cfr_trainer.py`)
   - Basic Neural CFR implementation
   - Combines tabular CFR with neural approximation
   - Memory-efficient training

5. **Deep CFR** (`deep_cfr.py`)  
   - Advanced neural CFR with reservoir sampling
   - Scales to larger games
   - Pure neural approximation

6. **CFR Bot** (`cfr_bot.py`)
   - Integrates with existing poker game
   - Uses trained strategies for decision making
   - Compatible with your current AI system

## 🎯 Training Modes

### Simplified Mode (Recommended for Testing)
- 50 preflop buckets  
- 50 postflop buckets per street
- 3 bet sizes
- Trains in minutes

### Full Mode (For Competitive Play)
- 169 preflop buckets
- 200+ postflop buckets per street  
- 6+ bet sizes
- Requires hours/days of training

## 📊 Expected Performance

### Training Time (Simplified Mode)
- **10K iterations**: 30 seconds - 2 minutes
- **50K iterations**: 5-10 minutes  
- **100K iterations**: 10-20 minutes

### Training Time (Full Mode)
- **100K iterations**: 30-60 minutes
- **1M iterations**: 5-10 hours
- **10M iterations**: 2-5 days

### Memory Usage
- **Simplified**: 1-4 GB RAM
- **Full**: 8-32 GB RAM  
- **Deep CFR**: 4-16 GB RAM (more efficient)

## 🔧 Configuration

Edit `config.py` to customize:

```python
# Game abstraction sizes
PREFLOP_BUCKETS = 50        # 50 for simplified, 169 for full
FLOP_BUCKETS = 50           # 50 for simplified, 200+ for full
TURN_BUCKETS = 50           # 50 for simplified, 200+ for full  
RIVER_BUCKETS = 50          # 50 for simplified, 200+ for full

# Neural network architecture
HIDDEN_SIZE = 512           # Network width
NUM_LAYERS = 3              # Network depth
LEARNING_RATE = 1e-4        # Learning rate

# Training parameters
CFR_ITERATIONS = 1000000    # Total iterations
BATCH_SIZE = 1024           # Neural network batch size
UPDATE_FREQUENCY = 1000     # How often to train networks
```

## 🎮 Integration with Existing Game

The CFR bot integrates seamlessly with your existing poker game:

```python
# In your poker game engine
from cfr_ai.cfr_bot import decide_action_cfr

def ai_decision(game_state):
    if use_cfr_bot:
        return decide_action_cfr(game_state)
    else:
        return ai_bladework_v2_decision(game_state)
```

## 🧪 Evaluation Metrics

### Exploitability
- Measures how much an optimal opponent can exploit the strategy
- Lower is better (GTO = 0 exploitability)
- Target: <10 mbb/100 (very strong)

### Win Rate vs Existing AI
- Test against your ai_bladework_v2
- Target: >52% win rate indicates improvement

### Convergence Speed  
- How quickly strategy stabilizes
- Faster convergence = more efficient training

## ⚡ Performance Optimization

### For Faster Training
1. **Use GPU**: Set `DEVICE = "cuda"` in config
2. **Reduce Abstraction**: Lower bucket counts
3. **Parallel Training**: Multiple processes
4. **Batch Size**: Increase for GPU efficiency

### For Better Results
1. **More Iterations**: 1M+ for competitive play
2. **Finer Abstraction**: More buckets = more accuracy
3. **Deep CFR**: Better scaling to large games
4. **Hyperparameter Tuning**: Learning rates, network sizes

## 🐛 Troubleshooting

### Common Issues

**"No neural networks available"**
- Install PyTorch: `pip install torch`
- Falls back to tabular CFR (still works)

**"CUDA out of memory"**  
- Reduce `BATCH_SIZE` in config
- Use CPU: Set `DEVICE = "cpu"`

**Training very slow**
- Use simplified mode first
- Check if using GPU acceleration
- Reduce abstraction size

**Bot plays randomly**
- Train for more iterations
- Check if model loaded correctly
- Verify game state conversion

## 📚 Further Reading

- [Original CFR Paper](https://poker.cs.ualberta.ca/publications/NIPS07-cfr.pdf)
- [Deep CFR Paper](https://arxiv.org/abs/1811.00164)  
- [Libratus: Superhuman AI](https://science.sciencemag.org/content/359/6374/418)

## 🤝 Next Steps

1. **Start with Demo**: Run `python train_cfr.py demo`
2. **Train Basic CFR**: 100K iterations simplified mode
3. **Test Against Current AI**: Compare performance
4. **Scale Up**: Full abstraction + Deep CFR for competitive play
5. **Deploy**: Integrate trained bot into your web app

The implementation is complete and ready to use! Start with the simplified mode to verify everything works, then scale up for competitive performance.