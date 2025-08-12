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
    PREFLOP_BUCKETS: int = 169
    FLOP_BUCKETS: int = 200
    TURN_BUCKETS: int = 200
    RIVER_BUCKETS: int = 200
    
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
    MEMORY_SIZE: int = 500000
    UPDATE_FREQUENCY: int = 1000
    
    # Deep CFR specific
    RESERVOIR_BUFFER_SIZE: int = 300000
    ADVANTAGE_MEMORY_SIZE: int = 20000000
    STRATEGY_MEMORY_SIZE: int = 7000000
    
    # Training settings
    DEVICE: str = "cpu"  # Will auto-detect GPU if available
    NUM_WORKERS: int = 4
    SAVE_FREQUENCY: int = 50000
    EVAL_FREQUENCY: int = 100000
    
    # File paths
    MODEL_SAVE_PATH: str = "server/app/game/cfr_ai/models/"
    # Remove unused directories to avoid creating empty folders during training
    TRAINING_DATA_PATH: str = ""
    LOG_PATH: str = ""
    RESULTS_BASE_PATH: str = "server/app/game/cfr_ai/results/"
    
    # Runtime/printing
    PRINT_FREQUENCY: int = 10000  # iterations between progress prints
    LOG_TO_FILE: bool = True
    LOG_INTERVAL_SECONDS: int = 300  # time-based heartbeat logging
    MAX_NODES_PER_ITERATION: int = 50000  # traversal budget per iteration
    VERBOSE_EACH_ITERATION: bool = False  # set True for testing only
    RESULTS_WRITE_EVERY: int = 1000  # how often to append iteration summaries
    
    def __post_init__(self):
        """Initialize default values and create directories"""
        if self.BET_SIZES_PREFLOP is None:
            # Use pot-multiple raises preflop (will be translated to amounts in BetAbstraction)
            self.BET_SIZES_PREFLOP = [1.0, 3.0, 5.0, float('inf')]  # 1x, 3x, 5x pot, all-in
            
        if self.BET_SIZES_POSTFLOP is None:
            # Restrict to the requested sizes only
            self.BET_SIZES_POSTFLOP = [0.35, 0.7, 1.1, float('inf')]  # All-in
        
        # Create only required directories
        for path in [self.MODEL_SAVE_PATH, self.RESULTS_BASE_PATH]:
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
            'results_base_path': self.RESULTS_BASE_PATH,
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
    
    PREFLOP_BUCKETS: int = 169
    FLOP_BUCKETS: int = 200
    TURN_BUCKETS: int = 200
    RIVER_BUCKETS: int = 200
    
    BET_SIZES_PREFLOP: List[float] = None
    BET_SIZES_POSTFLOP: List[float] = None
    
    HIDDEN_SIZE: int = 256
    NUM_LAYERS: int = 2
    LEARNING_RATE: float = 1e-3
    
    CFR_ITERATIONS: int = 100000
    BATCH_SIZE: int = 512
    # Make simplified runs faster per iteration
    MAX_NODES_PER_ITERATION: int = 2000
    VERBOSE_EACH_ITERATION: bool = False
    RESULTS_WRITE_EVERY: int = 500
    PRINT_FREQUENCY: int = 500
    
    def __post_init__(self):
        if self.BET_SIZES_PREFLOP is None:
            # Preflop: 1x, 3x, 5x pot; no all-in for now
            self.BET_SIZES_PREFLOP = [1.0, 3.0, 5.0]
            
        if self.BET_SIZES_POSTFLOP is None:
            self.BET_SIZES_POSTFLOP = [0.35, 0.7, 1.1, float('inf')]  # Simplified

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
        config.BET_SIZES_PREFLOP = simple.BET_SIZES_PREFLOP or [1.0, 3.0, 5.0]
        config.BET_SIZES_POSTFLOP = simple.BET_SIZES_POSTFLOP or [0.35, 0.7, 1.1, float('inf')]
        config.HIDDEN_SIZE = simple.HIDDEN_SIZE
        config.NUM_LAYERS = simple.NUM_LAYERS
        config.LEARNING_RATE = simple.LEARNING_RATE
        config.CFR_ITERATIONS = simple.CFR_ITERATIONS
        config.BATCH_SIZE = simple.BATCH_SIZE
        config.MAX_NODES_PER_ITERATION = getattr(simple, 'MAX_NODES_PER_ITERATION', config.MAX_NODES_PER_ITERATION)
        config.VERBOSE_EACH_ITERATION = getattr(simple, 'VERBOSE_EACH_ITERATION', False)
        config.RESULTS_WRITE_EVERY = getattr(simple, 'RESULTS_WRITE_EVERY', 1000)
        config.PRINT_FREQUENCY = getattr(simple, 'PRINT_FREQUENCY', config.PRINT_FREQUENCY)
        
        return config
    else:
        return CFR_CONFIG

# Auto-detect GPU availability (CUDA or Apple MPS)
try:
    import torch
    if torch.cuda.is_available():
        CFR_CONFIG.DEVICE = "cuda"
        print(f"GPU detected: {torch.cuda.get_device_name(0)}")
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        CFR_CONFIG.DEVICE = "mps"
        print("Apple Silicon GPU (MPS) detected")
    else:
        print("No GPU detected, using CPU")
except ImportError:
    print("PyTorch not installed, using CPU configuration")