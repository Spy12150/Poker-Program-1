"""
Neural Networks for Deep CFR

This module implements the neural networks used in Deep CFR:
- Value Network: Approximates counterfactual values
- Policy Network: Approximates regret and strategy functions
- Advantage Network: Approximates advantage functions
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import OrderedDict
from .action_space import ACTION_LIST

class ValueNetwork(nn.Module):
    """
    Value network for approximating counterfactual values
    
    Input: Information set features
    Output: Expected counterfactual value for the player
    """
    
    def __init__(self, input_size: int, hidden_size: int = 512, num_layers: int = 3, 
                 dropout_rate: float = 0.1):
        super().__init__()
        
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        # Build network layers (use LayerNorm instead of BatchNorm for small batches)
        layers = []

        # Input layer
        layers.append(('input', nn.Linear(input_size, hidden_size)))
        layers.append(('input_ln', nn.LayerNorm(hidden_size)))
        layers.append(('input_relu', nn.ReLU()))
        layers.append(('input_dropout', nn.Dropout(dropout_rate)))

        # Hidden layers
        for i in range(num_layers - 1):
            layers.append((f'hidden_{i}', nn.Linear(hidden_size, hidden_size)))
            layers.append((f'hidden_{i}_ln', nn.LayerNorm(hidden_size)))
            layers.append((f'hidden_{i}_relu', nn.ReLU()))
            layers.append((f'hidden_{i}_dropout', nn.Dropout(dropout_rate)))

        # Output layer
        layers.append(('output', nn.Linear(hidden_size, 1)))
        
        self.network = nn.Sequential(OrderedDict(layers))
        
        # Initialize weights
        self.apply(self._init_weights)
    
    def _init_weights(self, module):
        """Initialize network weights"""
        if isinstance(module, nn.Linear):
            nn.init.xavier_uniform_(module.weight)
            nn.init.constant_(module.bias, 0)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass"""
        return self.network(x)

class AdvantageNetwork(nn.Module):
    """
    Advantage network for approximating counterfactual regrets
    
    Input: Information set features + action encoding
    Output: Counterfactual regret for the action
    """
    
    def __init__(self, input_size: int, max_actions: int = 10, hidden_size: int = 512, 
                 num_layers: int = 3, dropout_rate: float = 0.1):
        super().__init__()
        
        self.input_size = input_size
        self.max_actions = max_actions
        self.hidden_size = hidden_size
        
        # Action embedding
        self.action_embedding = nn.Embedding(max_actions, 32)
        
        # Combined input size
        combined_input_size = input_size + 32
        
        # Build network (LayerNorm)
        layers = []

        # Input layer
        layers.append(('input', nn.Linear(combined_input_size, hidden_size)))
        layers.append(('input_ln', nn.LayerNorm(hidden_size)))
        layers.append(('input_relu', nn.ReLU()))
        layers.append(('input_dropout', nn.Dropout(dropout_rate)))

        # Hidden layers
        for i in range(num_layers - 1):
            layers.append((f'hidden_{i}', nn.Linear(hidden_size, hidden_size)))
            layers.append((f'hidden_{i}_ln', nn.LayerNorm(hidden_size)))
            layers.append((f'hidden_{i}_relu', nn.ReLU()))
            layers.append((f'hidden_{i}_dropout', nn.Dropout(dropout_rate)))

        # Output layer
        layers.append(('output', nn.Linear(hidden_size, 1)))
        
        self.network = nn.Sequential(OrderedDict(layers))
        
        # Initialize weights
        self.apply(self._init_weights)
    
    def _init_weights(self, module):
        """Initialize network weights"""
        if isinstance(module, nn.Linear):
            nn.init.xavier_uniform_(module.weight)
            nn.init.constant_(module.bias, 0)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, std=0.1)
    
    def forward(self, features: torch.Tensor, action_indices: torch.Tensor) -> torch.Tensor:
        """Forward pass"""
        # Embed actions
        action_embeds = self.action_embedding(action_indices)
        
        # Combine features and action embeddings
        combined_input = torch.cat([features, action_embeds], dim=1)
        
        return self.network(combined_input)

class PolicyNetwork(nn.Module):
    """
    Policy network for approximating strategies
    
    Input: Information set features
    Output: Action probabilities
    """
    
    def __init__(self, input_size: int, max_actions: int = 10, hidden_size: int = 512,
                 num_layers: int = 3, dropout_rate: float = 0.1):
        super().__init__()
        
        self.input_size = input_size
        self.max_actions = max_actions
        self.hidden_size = hidden_size
        
        # Build network (LayerNorm)
        layers = []

        # Input layer
        layers.append(('input', nn.Linear(input_size, hidden_size)))
        layers.append(('input_ln', nn.LayerNorm(hidden_size)))
        layers.append(('input_relu', nn.ReLU()))
        layers.append(('input_dropout', nn.Dropout(dropout_rate)))

        # Hidden layers
        for i in range(num_layers - 1):
            layers.append((f'hidden_{i}', nn.Linear(hidden_size, hidden_size)))
            layers.append((f'hidden_{i}_ln', nn.LayerNorm(hidden_size)))
            layers.append((f'hidden_{i}_relu', nn.ReLU()))
            layers.append((f'hidden_{i}_dropout', nn.Dropout(dropout_rate)))

        # Output layer (no activation - will apply softmax later)
        layers.append(('output', nn.Linear(hidden_size, max_actions)))
        
        self.network = nn.Sequential(OrderedDict(layers))
        
        # Initialize weights
        self.apply(self._init_weights)
    
    def _init_weights(self, module):
        """Initialize network weights"""
        if isinstance(module, nn.Linear):
            nn.init.xavier_uniform_(module.weight)
            nn.init.constant_(module.bias, 0)
    
    def forward(self, x: torch.Tensor, action_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Forward pass
        
        Args:
            x: Input features
            action_mask: Mask for legal actions (1 for legal, 0 for illegal)
        """
        logits = self.network(x)
        
        if action_mask is not None:
            # Mask illegal actions with large negative values
            logits = logits.masked_fill(action_mask == 0, -1e9)
        
        # Apply softmax to get probabilities
        return F.softmax(logits, dim=1)

class DeepCFRNetworks:
    """
    Container for all networks used in Deep CFR
    """
    
    def __init__(self, config, device: str = 'cpu'):
        self.config = config
        self.device = torch.device(device)
        
        # Determine input size based on information set features
        self.input_size = self._calculate_input_size()
        self.max_actions = len(ACTION_LIST)
        
        # Initialize networks
        self.value_network = ValueNetwork(
            input_size=self.input_size,
            hidden_size=config.HIDDEN_SIZE,
            num_layers=config.NUM_LAYERS,
            dropout_rate=config.DROPOUT_RATE
        ).to(self.device)
        
        self.advantage_network = AdvantageNetwork(
            input_size=self.input_size,
            max_actions=self.max_actions,
            hidden_size=config.HIDDEN_SIZE,
            num_layers=config.NUM_LAYERS,
            dropout_rate=config.DROPOUT_RATE
        ).to(self.device)
        
        self.policy_network = PolicyNetwork(
            input_size=self.input_size,
            max_actions=self.max_actions,
            hidden_size=config.HIDDEN_SIZE,
            num_layers=config.NUM_LAYERS,
            dropout_rate=config.DROPOUT_RATE
        ).to(self.device)
        
        # Initialize optimizers
        self.value_optimizer = torch.optim.Adam(
            self.value_network.parameters(), 
            lr=config.LEARNING_RATE
        )
        
        self.advantage_optimizer = torch.optim.Adam(
            self.advantage_network.parameters(), 
            lr=config.LEARNING_RATE
        )
        
        self.policy_optimizer = torch.optim.Adam(
            self.policy_network.parameters(), 
            lr=config.LEARNING_RATE
        )
        
        # Learning rate schedulers
        self.value_scheduler = torch.optim.lr_scheduler.StepLR(
            self.value_optimizer, step_size=100000, gamma=0.9
        )
        
        self.advantage_scheduler = torch.optim.lr_scheduler.StepLR(
            self.advantage_optimizer, step_size=100000, gamma=0.9
        )
        
        self.policy_scheduler = torch.optim.lr_scheduler.StepLR(
            self.policy_optimizer, step_size=100000, gamma=0.9
        )
        
        print(f"Initialized Deep CFR networks on {self.device}")
        print(f"Value network parameters: {sum(p.numel() for p in self.value_network.parameters()):,}")
        print(f"Advantage network parameters: {sum(p.numel() for p in self.advantage_network.parameters()):,}")
        print(f"Policy network parameters: {sum(p.numel() for p in self.policy_network.parameters()):,}")
    
    def _calculate_input_size(self) -> int:
        """Calculate input feature size based on information set encoding"""
        # Based on InformationSet.create_features()
        feature_size = (
            4 +      # Street encoding (one-hot)
            1 +      # Card bucket (normalized)
            1 +      # Pot size bucket (normalized)
            2 +      # Pot odds, SPR approx
            12 +     # Betting history features (expanded)
            1        # Player position
        )
        return feature_size
    
    def predict_value(self, features: torch.Tensor) -> torch.Tensor:
        """Predict counterfactual value"""
        self.value_network.eval()
        with torch.no_grad():
            return self.value_network(features)
    
    def predict_advantages(self, features: torch.Tensor, action_indices: torch.Tensor) -> torch.Tensor:
        """Predict counterfactual regrets/advantages"""
        self.advantage_network.eval()
        with torch.no_grad():
            return self.advantage_network(features, action_indices)
    
    def predict_policy(self, features: torch.Tensor, action_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """Predict action probabilities"""
        self.policy_network.eval()
        with torch.no_grad():
            return self.policy_network(features, action_mask)
    
    def train_value_network(self, features: torch.Tensor, targets: torch.Tensor) -> float:
        """Train value network"""
        self.value_network.train()
        self.value_optimizer.zero_grad()
        
        predictions = self.value_network(features)
        loss = F.mse_loss(predictions.squeeze(), targets)
        
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.value_network.parameters(), max_norm=1.0)
        self.value_optimizer.step()
        
        return loss.item()
    
    def train_advantage_network(self, features: torch.Tensor, action_indices: torch.Tensor, 
                              targets: torch.Tensor) -> float:
        """Train advantage network"""
        self.advantage_network.train()
        self.advantage_optimizer.zero_grad()
        
        predictions = self.advantage_network(features, action_indices)
        loss = F.mse_loss(predictions.squeeze(), targets)
        
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.advantage_network.parameters(), max_norm=1.0)
        self.advantage_optimizer.step()
        
        return loss.item()
    
    def train_policy_network(self, features: torch.Tensor, action_probs: torch.Tensor,
                           action_mask: Optional[torch.Tensor] = None) -> float:
        """Train policy network using cross-entropy loss"""
        self.policy_network.train()
        self.policy_optimizer.zero_grad()
        
        predictions = self.policy_network(features, action_mask)
        
        # Use KL divergence loss to match target probabilities
        loss = F.kl_div(
            torch.log(predictions + 1e-8), 
            action_probs, 
            reduction='batchmean'
        )
        
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_network.parameters(), max_norm=1.0)
        self.policy_optimizer.step()
        
        return loss.item()
    
    def update_learning_rates(self):
        """Update learning rate schedulers"""
        self.value_scheduler.step()
        self.advantage_scheduler.step()
        self.policy_scheduler.step()
    
    def save_models(self, filepath: str):
        """Save all models to file"""
        torch.save({
            'value_network': self.value_network.state_dict(),
            'advantage_network': self.advantage_network.state_dict(),
            'policy_network': self.policy_network.state_dict(),
            'value_optimizer': self.value_optimizer.state_dict(),
            'advantage_optimizer': self.advantage_optimizer.state_dict(),
            'policy_optimizer': self.policy_optimizer.state_dict(),
            'config': self.config.to_dict(),
        }, filepath)
        
        print(f"Saved models to {filepath}")
    
    def load_models(self, filepath: str):
        """Load all models from file"""
        try:
            checkpoint = torch.load(filepath, map_location=self.device)
            
            self.value_network.load_state_dict(checkpoint['value_network'])
            self.advantage_network.load_state_dict(checkpoint['advantage_network'])
            self.policy_network.load_state_dict(checkpoint['policy_network'])
            
            self.value_optimizer.load_state_dict(checkpoint['value_optimizer'])
            self.advantage_optimizer.load_state_dict(checkpoint['advantage_optimizer'])
            self.policy_optimizer.load_state_dict(checkpoint['policy_optimizer'])
            
            print(f"Loaded models from {filepath}")
            
        except FileNotFoundError:
            print(f"Model file {filepath} not found")
        except Exception as e:
            print(f"Error loading models: {e}")
    
    def get_model_info(self) -> Dict[str, int]:
        """Get information about model sizes"""
        return {
            'value_params': sum(p.numel() for p in self.value_network.parameters()),
            'advantage_params': sum(p.numel() for p in self.advantage_network.parameters()),
            'policy_params': sum(p.numel() for p in self.policy_network.parameters()),
            'total_params': sum(p.numel() for p in self.value_network.parameters()) +
                           sum(p.numel() for p in self.advantage_network.parameters()) +
                           sum(p.numel() for p in self.policy_network.parameters()),
            'input_size': self.input_size,
            'device': str(self.device)
        }

def create_networks(config, device: str = 'cpu') -> DeepCFRNetworks:
    """Factory function to create Deep CFR networks"""
    return DeepCFRNetworks(config, device)