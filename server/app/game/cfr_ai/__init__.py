"""
Neural CFR AI Implementation for Poker

This package implements Counterfactual Regret Minimization with neural network
approximation for learning optimal poker strategies.

Components:
- game_abstraction: Card and bet abstraction systems
- information_set: Information set representation
- neural_networks: Value and policy networks
- cfr_trainer: Neural CFR training algorithm
- deep_cfr: Deep CFR implementation
- cfr_bot: Bot interface for gameplay
"""

from .cfr_bot import CFRBot
from .cfr_trainer import NeuralCFRTrainer
from .deep_cfr import DeepCFRTrainer

__version__ = "1.0.0"
__author__ = "CFR Poker AI"

__all__ = [
    'CFRBot',
    'NeuralCFRTrainer', 
    'DeepCFRTrainer'
]