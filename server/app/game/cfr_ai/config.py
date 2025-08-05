"""
Configuration and hyperparameters for Neural CFR implementation
"""

import os
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class CFRConfig:
    """Main configuration for CFR training and evaluation"""
    
    # Game abstraction settings
    PREFLOP_BUCKETS: int = 169  # All starting hands initially
    FLOP_BUCKETS: int = 200     # Start smaller, can increase
    TURN_BUCKETS: int = 200     # Start smaller, can increase  
    RIVER_BUCKETS: int = 200    # Start smaller, can increase
    
    # Bet abstraction
    BET_SIZES_PREFLOP: List[float] = None
    BET_SIZES_POSTFLOP: List[float] = None
    
    # Neural network architecture
    HIDDEN_SIZE: int = 512
    NUM_LAYERS: int = 3
    LEARNING_RATE: float = 1e-4
    DROPOUT_RATE: float = 0.1
    
    # CFR training parameters
    CFR_ITERATIONS: int = 1000000
    BATCH_SIZE: int = 1024
    MEMORY_SIZE: int = 1000000
    UPDATE_FREQUENCY: int = 1000
    
    # Deep CFR specific
    RESERVOIR_BUFFER_SIZE: int = 2000000
    ADVANTAGE_MEMORY_SIZE: int = 10000000
    STRATEGY_MEMORY_SIZE: int = 10000000
    
    # Training settings
    DEVICE: str = "cpu"  # Will auto-detect GPU if available
    NUM_WORKERS: int = 4
    SAVE_FREQUENCY: int = 10000
    EVAL_FREQUENCY: int = 50000
    
    # File paths
    MODEL_SAVE_PATH: str = "server/app/game/cfr_ai/models/"
    TRAINING_DATA_PATH: str = "server/app/game/cfr_ai/data/"
    LOG_PATH: str = "server/app/game/cfr_ai/logs/"
    
    def __post_init__(self):
        """Initialize default values and create directories"""
        if self.BET_SIZES_PREFLOP is None:
            self.BET_SIZES_PREFLOP = [2.0, 2.5, 3.0, 4.0, 8.0, float('inf')]  # All-in
            
        if self.BET_SIZES_POSTFLOP is None:
            self.BET_SIZES_POSTFLOP = [0.33, 0.5, 0.67, 1.0, 1.5, float('inf')]  # All-in
        
        # Create directories
        for path in [self.MODEL_SAVE_PATH, self.TRAINING_DATA_PATH, self.LOG_PATH]:
            os.makedirs(path, exist_ok=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for serialization"""
        return {
            'preflop_buckets': self.PREFLOP_BUCKETS,
            'flop_buckets': self.FLOP_BUCKETS,
            'turn_buckets': self.TURN_BUCKETS,
            'river_buckets': self.RIVER_BUCKETS,
            'bet_sizes_preflop': self.BET_SIZES_PREFLOP,
            'bet_sizes_postflop': self.BET_SIZES_POSTFLOP,
            'hidden_size': self.HIDDEN_SIZE,
            'num_layers': self.NUM_LAYERS,
            'learning_rate': self.LEARNING_RATE,
            'cfr_iterations': self.CFR_ITERATIONS,
            'batch_size': self.BATCH_SIZE,
        }

@dataclass
class TrainingConfig:
    """Configuration for training process"""
    
    # Training schedule
    WARMUP_ITERATIONS: int = 100000
    EXPLORATION_RATE: float = 0.1
    EXPLORATION_DECAY: float = 0.999
    
    # Evaluation settings
    EVAL_HANDS: int = 100000
    EXPLOITABILITY_CALCULATION: bool = True
    BEST_RESPONSE_CALCULATION: bool = False  # Expensive, enable for final evaluation
    
    # Checkpointing
    CHECKPOINT_FREQUENCY: int = 100000
    MAX_CHECKPOINTS: int = 5
    
    # Logging
    LOG_LEVEL: str = "INFO"
    TENSORBOARD_LOGGING: bool = True
    WANDB_LOGGING: bool = False  # Can enable for experiment tracking

# Global configuration instances
CFR_CONFIG = CFRConfig()
TRAINING_CONFIG = TrainingConfig()

# Simplified configurations for development/testing
@dataclass
class SimplifiedConfig:
    """Simplified config for rapid prototyping and testing"""
    
    PREFLOP_BUCKETS: int = 50
    FLOP_BUCKETS: int = 50
    TURN_BUCKETS: int = 50
    RIVER_BUCKETS: int = 50
    
    BET_SIZES_PREFLOP: List[float] = None
    BET_SIZES_POSTFLOP: List[float] = None
    
    HIDDEN_SIZE: int = 256
    NUM_LAYERS: int = 2
    LEARNING_RATE: float = 1e-3
    
    CFR_ITERATIONS: int = 100000
    BATCH_SIZE: int = 512
    
    def __post_init__(self):
        if self.BET_SIZES_PREFLOP is None:
            self.BET_SIZES_PREFLOP = [2.5, 5.0, float('inf')]  # Simplified
            
        if self.BET_SIZES_POSTFLOP is None:
            self.BET_SIZES_POSTFLOP = [0.5, 1.0, float('inf')]  # Simplified

# Use simplified config for initial development
SIMPLIFIED_CONFIG = SimplifiedConfig()

def get_config(simplified: bool = True) -> CFRConfig:
    """Get configuration based on complexity level"""
    if simplified:
        # Convert simplified config to CFRConfig format
        config = CFRConfig()
        simple = SIMPLIFIED_CONFIG
        
        config.PREFLOP_BUCKETS = simple.PREFLOP_BUCKETS
        config.FLOP_BUCKETS = simple.FLOP_BUCKETS
        config.TURN_BUCKETS = simple.TURN_BUCKETS
        config.RIVER_BUCKETS = simple.RIVER_BUCKETS
        config.BET_SIZES_PREFLOP = simple.BET_SIZES_PREFLOP or [2.5, 5.0, float('inf')]
        config.BET_SIZES_POSTFLOP = simple.BET_SIZES_POSTFLOP or [0.5, 1.0, float('inf')]
        config.HIDDEN_SIZE = simple.HIDDEN_SIZE
        config.NUM_LAYERS = simple.NUM_LAYERS
        config.LEARNING_RATE = simple.LEARNING_RATE
        config.CFR_ITERATIONS = simple.CFR_ITERATIONS
        config.BATCH_SIZE = simple.BATCH_SIZE
        
        return config
    else:
        return CFR_CONFIG

# Auto-detect GPU availability
try:
    import torch
    if torch.cuda.is_available():
        CFR_CONFIG.DEVICE = "cuda"
        print(f"GPU detected: {torch.cuda.get_device_name(0)}")
    else:
        print("No GPU detected, using CPU")
except ImportError:
    print("PyTorch not installed, using CPU configuration")