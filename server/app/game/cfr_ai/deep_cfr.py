"""
Deep CFR Implementation

This module implements Deep CFR, which uses neural networks to approximate
counterfactual values and regrets instead of storing them in memory.
This allows scaling to much larger games.
"""

import random
import numpy as np
import torch
from typing import List, Dict, Tuple, Optional, Any, Set
from collections import defaultdict, deque
import time
import os
import json
import datetime

from .config import get_config
from .game_abstraction import create_game_abstraction
from .information_set import create_information_set_manager, GameState, InformationSet
from .neural_networks import create_networks
from .cfr_trainer import NeuralCFRTrainer
from .action_space import ACTION_MAP, ACTION_LIST

class ReservoirBuffer:
    """
    Reservoir sampling buffer for storing training experiences
    """
    
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.buffer = []
        self.position = 0
        self.size = 0
    
    def add(self, experience):
        """Add experience using reservoir sampling"""
        if self.size < self.capacity:
            self.buffer.append(experience)
            self.size += 1
        else:
            # Reservoir sampling - replace random element
            if random.random() < self.capacity / (self.position + 1):
                idx = random.randint(0, self.capacity - 1)
                self.buffer[idx] = experience
        
        self.position += 1
    
    def sample(self, batch_size: int) -> List:
        """Sample batch from buffer"""
        if self.size == 0:
            return []
        return random.sample(self.buffer, min(batch_size, self.size))
    
    def __len__(self):
        return self.size

class DeepCFRTrainer(NeuralCFRTrainer):
    """
    Deep CFR trainer that uses neural networks to approximate values and strategies
    instead of storing them in tabular form
    """
    
    def __init__(self, config=None, simplified: bool = True):
        super().__init__(config, simplified)
        
        # Deep CFR specific components
        self.advantage_memories = ReservoirBuffer(self.config.ADVANTAGE_MEMORY_SIZE)
        self.strategy_memories = ReservoirBuffer(self.config.STRATEGY_MEMORY_SIZE)
        
        # Training statistics
        self.advantages_trained = 0
        self.strategies_trained = 0
        
        # Neural network training schedule
        self.train_advantage_every = 100  # Train advantage network every N iterations
        self.train_strategy_every = 1000   # Train strategy network every N iterations
        
        print(f"Initialized Deep CFR Trainer")
        print(f"Advantage memory: {self.config.ADVANTAGE_MEMORY_SIZE:,}")
        print(f"Strategy memory: {self.config.STRATEGY_MEMORY_SIZE:,}")
        # Override trainer label in results meta
        try:
            # Recreate meta with correct trainer type
            base = getattr(self.config, 'RESULTS_BASE_PATH', 'server/app/game/cfr_ai/results')
            # Reuse existing directory created by parent
            meta = {
                'run_started_at': os.path.basename(self._results_dir).replace('run_', ''),
                'config': self.config.to_dict(),
                'trainer': 'DeepCFRTrainer'
            }
            with open(os.path.join(self._results_dir, 'meta.json'), 'w') as f:
                json.dump(meta, f)
        except Exception:
            pass
    
    def train(self, iterations: int = None):
        """Enhanced training loop for Deep CFR"""
        iterations = iterations or self.config.CFR_ITERATIONS
        
        print(f"Starting Deep CFR training for {iterations:,} iterations...")
        start_time = time.time()
        
        for i in range(iterations):
            self.iteration += 1
            
            # Run CFR iteration with neural network approximation
            shared_budget = [getattr(self.config, 'MAX_NODES_PER_ITERATION', 50000)]
            self.deep_cfr_iteration(shared_budget)
            
            # Train neural networks on schedule
            if self.iteration % self.train_advantage_every == 0:
                self.train_advantage_memory()
            
            if self.iteration % self.train_strategy_every == 0:
                self.train_strategy_memory()
            
            # Periodic logging
            if self.iteration % self.config.PRINT_FREQUENCY == 0:
                elapsed = max(1e-6, time.time() - start_time)
                its_per_sec = self.iteration / elapsed
                print(
                    f"Iter {self.iteration:,} | {its_per_sec:.0f} it/s | "
                    f"InfoSets: {len(self.info_set_manager.information_sets):,} | "
                    f"AdvMem: {len(self.advantage_memories):,} | StratMem: {len(self.strategy_memories):,}"
                )
            # Optional per-iteration print (testing only)
            if getattr(self.config, 'VERBOSE_EACH_ITERATION', False):
                print(
                    f"[Iter {self.iteration}] InfoSets: {len(self.info_set_manager.information_sets):,} | "
                    f"AdvMem: {len(self.advantage_memories):,} | StratMem: {len(self.strategy_memories):,}"
                )
            # Per-iteration results
            self._write_iteration_result({
                'iteration': self.iteration,
                'info_sets': len(self.info_set_manager.information_sets),
                'adv_mem': len(self.advantage_memories),
                'strat_mem': len(self.strategy_memories)
            })
            
            # Checkpoints and evaluation
            if self.iteration % self.config.SAVE_FREQUENCY == 0:
                self.save_checkpoint()
            
            if self.iteration % self.config.EVAL_FREQUENCY == 0:
                self.evaluate()
        
        print(f"Deep CFR training completed in {time.time() - start_time:.1f} seconds")
        self.save_final_strategy()
        self._close_results_writer()
    
    def deep_cfr_iteration(self, node_budget: list):
        """Run one iteration of Deep CFR"""
        # Create random game states for training
        for _ in range(2):  # Multiple states per iteration
            game_state = self.create_random_game_state()
            
            # Traverse for both players
            for player in [0, 1]:
                self.deep_cfr_recursive(game_state, player, 1.0, 1.0, 0, node_budget)
    
    def deep_cfr_recursive(self, game_state: GameState, traversing_player: int,
                          reach_prob_0: float, reach_prob_1: float,
                          depth: int = 0, node_budget: list = None) -> float:
        """
        Deep CFR recursive algorithm using neural network approximation
        """
        
        # Initialize and check traversal budgets
        if node_budget is None:
            node_budget = [getattr(self.config, 'MAX_NODES_PER_ITERATION', 50000)]
        node_budget[0] -= 1
        if node_budget[0] <= 0:
            return 0.0
        # Depth guard to prevent runaway recursion
        if depth >= 200:
            return 0.0

        # Terminal node
        if self.is_terminal(game_state):
            return self.get_terminal_utility(game_state, traversing_player)
        
        # Get information set
        current_player = game_state.current_player
        info_set = self.info_set_manager.get_information_set(game_state, current_player)
        
        # Get strategy using neural network or regret matching
        if self.networks and random.random() < 0.5:  # Mix neural and tabular
            strategy = self.get_neural_strategy(info_set)
        else:
            strategy = info_set.get_strategy()
        
        # Calculate counterfactual values
        action_utilities = {}
        for action in info_set.legal_actions:
            new_game_state = self.apply_action(game_state, action)
            # Update reach probabilities
            if current_player == 0:
                new_reach_0 = reach_prob_0 * strategy[action]
                new_reach_1 = reach_prob_1
            else:
                new_reach_0 = reach_prob_0
                new_reach_1 = reach_prob_1 * strategy[action]
            action_utilities[action] = self.deep_cfr_recursive(
                new_game_state, traversing_player, new_reach_0, new_reach_1, depth + 1, node_budget
            )
        
        # Store training data for neural networks
        if current_player == traversing_player:
            opponent_reach = reach_prob_1 if current_player == 0 else reach_prob_0
            self.store_deep_cfr_data(info_set, action_utilities, strategy, opponent_reach)
        
        # Return expected utility
        # Safe expected utility
        probs = np.array([max(strategy.get(a, 0.0), 0.0) for a in info_set.legal_actions], dtype=np.float64)
        s = probs.sum()
        if s <= 0:
            probs = np.ones_like(probs) / len(probs)
        else:
            probs = probs / s
        return float(sum(probs[i] * action_utilities[a] for i, a in enumerate(info_set.legal_actions)))
    
    def get_neural_strategy(self, info_set: InformationSet) -> Dict[str, float]:
        """Get strategy using neural network prediction"""
        if not self.networks:
            return info_set.get_strategy()
        
        try:
            # Prepare features
            features = torch.tensor(info_set.features).unsqueeze(0).to(self.device)
            
            # Create action mask for legal actions
            action_map = self.get_action_mapping()
            action_mask = torch.zeros(1, len(action_map)).to(self.device)
            
            for action in info_set.legal_actions:
                if action in action_map:
                    action_mask[0, action_map[action]] = 1
            
            # Get neural network prediction
            with torch.no_grad():
                action_probs = self.networks.predict_policy(features, action_mask)
                action_probs = action_probs.cpu().numpy()[0]
            
            # Convert to strategy dictionary with strict normalization (zeros below threshold)
            raw = [float(action_probs[action_map[a]]) if a in action_map else 0.0 for a in info_set.legal_actions]
            raw = np.array([max(v, 0.0) for v in raw], dtype=np.float64)
            s = raw.sum()
            if s <= 0 or not np.isfinite(s):
                prob = 1.0 / max(1, len(info_set.legal_actions))
                strategy = {a: prob for a in info_set.legal_actions}
            else:
                norm = raw / s
                norm = np.where(norm < 1e-8, 0.0, norm)
                s2 = norm.sum()
                if s2 == 0:
                    prob = 1.0 / max(1, len(info_set.legal_actions))
                    strategy = {a: prob for a in info_set.legal_actions}
                else:
                    norm = norm / s2
                    strategy = {a: float(norm[i]) for i, a in enumerate(info_set.legal_actions)}
            
            return strategy
            
        except Exception as e:
            print(f"Neural strategy prediction failed: {e}")
            return info_set.get_strategy()
    
    def get_action_mapping(self) -> Dict[str, int]:
        """Get mapping from action strings to indices"""
        from .action_space import ACTION_MAP
        return ACTION_MAP
    
    def store_deep_cfr_data(self, info_set: InformationSet, action_utilities: Dict[str, float],
                           strategy: Dict[str, float], reach_probability: float):
        """Store training data for Deep CFR neural networks"""
        
        # Calculate baseline utility
        baseline_utility = sum(strategy[action] * action_utilities[action] 
                             for action in info_set.legal_actions)
        
        # Store advantage data for each action
        action_map = self.get_action_mapping()
        
        for action in info_set.legal_actions:
            if action in action_map:
                advantage = (action_utilities[action] - baseline_utility) * reach_probability
                
                self.advantage_memories.add({
                    'features': info_set.features.copy(),
                    'action_index': action_map[action],
                    'advantage': advantage,
                    'iteration': self.iteration
                })
        
        # Store strategy data (use float32 to reduce RAM footprint)
        strategy_vector = np.zeros(len(action_map), dtype=np.float32)
        for action, prob in strategy.items():
            if action in action_map:
                strategy_vector[action_map[action]] = prob
        
        # Create action mask (use float32 to reduce RAM footprint)
        action_mask = np.zeros(len(action_map), dtype=np.float32)
        for action in info_set.legal_actions:
            if action in action_map:
                action_mask[action_map[action]] = 1
        
        self.strategy_memories.add({
            'features': info_set.features.copy(),
            'strategy': strategy_vector.copy(),
            'action_mask': action_mask.copy(),
            'iteration': self.iteration
        })
    
    def train_advantage_memory(self):
        """Train advantage network on stored memories"""
        if not self.networks or len(self.advantage_memories) < self.config.BATCH_SIZE:
            return
        
        # Sample batch
        batch = self.advantage_memories.sample(self.config.BATCH_SIZE)
        
        # Prepare tensors
        features = torch.stack([torch.tensor(item['features']) for item in batch]).to(self.device)
        action_indices = torch.tensor([item['action_index'] for item in batch]).to(self.device)
        advantages = torch.tensor([item['advantage'] for item in batch], dtype=torch.float32).to(self.device)
        # Normalize advantages for stability
        std = advantages.std().clamp(min=1e-6)
        advantages = advantages / std
        
        # Train network
        loss = self.networks.train_advantage_network(features, action_indices, advantages)
        self.advantages_trained += len(batch)
        
        if self.iteration % 10000 == 0:
            print(f"Advantage network: Loss={loss:.6f}, Trained={self.advantages_trained:,}")
    
    def train_strategy_memory(self):
        """Train strategy network on stored memories"""
        if not self.networks or len(self.strategy_memories) < self.config.BATCH_SIZE:
            return
        
        # Sample batch
        batch = self.strategy_memories.sample(self.config.BATCH_SIZE)
        
        # Prepare tensors
        features = torch.stack([torch.tensor(item['features']) for item in batch]).to(self.device)
        strategies = torch.stack([torch.tensor(item['strategy']) for item in batch]).to(self.device)
        action_masks = torch.stack([torch.tensor(item['action_mask']) for item in batch]).to(self.device)
        
        # Train network
        loss = self.networks.train_policy_network(features, strategies, action_masks)
        self.strategies_trained += len(batch)
        
        if self.iteration % 10000 == 0:
            print(f"Strategy network: Loss={loss:.6f}, Trained={self.strategies_trained:,}")
    
    def get_neural_value(self, info_set: InformationSet) -> float:
        """Get counterfactual value using neural network"""
        if not self.networks:
            return 0.0
        
        try:
            features = torch.tensor(info_set.features).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                value = self.networks.predict_value(features)
                return value.cpu().item()
                
        except Exception as e:
            print(f"Neural value prediction failed: {e}")
            return 0.0
    
    def evaluate(self):
        """Enhanced evaluation for Deep CFR"""
        print(f"\n=== Deep CFR Evaluation at iteration {self.iteration:,} ===")
        
        # Basic statistics
        num_info_sets = len(self.info_set_manager.information_sets)
        print(f"Information sets: {num_info_sets:,}")
        print(f"Advantage memories: {len(self.advantage_memories):,}")
        print(f"Strategy memories: {len(self.strategy_memories):,}")
        print(f"Advantages trained: {self.advantages_trained:,}")
        print(f"Strategies trained: {self.strategies_trained:,}")
        
        # Neural network performance
        if self.networks:
            # Test neural network predictions
            if len(self.advantage_memories) > 0:
                test_batch = self.advantage_memories.sample(min(100, len(self.advantage_memories)))
                features = torch.stack([torch.tensor(item['features']) for item in test_batch]).to(self.device)
                action_indices = torch.tensor([item['action_index'] for item in test_batch]).to(self.device)

                with torch.no_grad():
                    predictions = self.networks.advantage_network(features, action_indices)
                    pred_mean = predictions.mean().item()
                    pred_std = predictions.std().item()

                print(f"Advantage predictions: mean={pred_mean:.6f}, std={pred_std:.6f}")
            
            # Memory usage estimate
            total_params = self.networks.get_model_info()['total_params']
            model_memory_mb = total_params * 4 / 1024 / 1024  # Assuming float32
            buffer_memory_mb = (len(self.advantage_memories) + len(self.strategy_memories)) * 0.001
            print(f"Memory usage: Models={model_memory_mb:.1f}MB, Buffers={buffer_memory_mb:.1f}MB")
        # Persist evaluation snapshot
        self._write_iteration_result({
            'iteration': self.iteration,
            'phase': 'deep_eval',
            'info_sets': num_info_sets,
            'advantages_trained': self.advantages_trained,
            'strategies_trained': self.strategies_trained,
            'model_memory_mb': float(model_memory_mb),
            'buffer_memory_mb': float(buffer_memory_mb),
        })
        
        print("=" * 60)
    
    def save_checkpoint(self):
        """Enhanced checkpoint saving for Deep CFR"""
        checkpoint_dir = self.config.MODEL_SAVE_PATH
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        # Save neural networks
        if self.networks:
            networks_path = os.path.join(checkpoint_dir, f"deep_cfr_networks_{self.iteration}.pth")
            
            # Enhanced save with training statistics
            checkpoint_data = {
                'value_network': self.networks.value_network.state_dict(),
                'advantage_network': self.networks.advantage_network.state_dict(),
                'policy_network': self.networks.policy_network.state_dict(),
                'value_optimizer': self.networks.value_optimizer.state_dict(),
                'advantage_optimizer': self.networks.advantage_optimizer.state_dict(),
                'policy_optimizer': self.networks.policy_optimizer.state_dict(),
                'iteration': self.iteration,
                'advantages_trained': self.advantages_trained,
                'strategies_trained': self.strategies_trained,
                'config': self.config.to_dict(),
            }
            
            torch.save(checkpoint_data, networks_path)
            print(f"Saved Deep CFR networks to {networks_path}")
        
        # Save a sample of memories for analysis
        if len(self.advantage_memories) > 0:
            import pickle
            sample_path = os.path.join(checkpoint_dir, f"memories_sample_{self.iteration}.pkl")
            
            sample_data = {
                'advantage_sample': self.advantage_memories.sample(min(1000, len(self.advantage_memories))),
                'strategy_sample': self.strategy_memories.sample(min(1000, len(self.strategy_memories))),
                'iteration': self.iteration
            }
            
            with open(sample_path, 'wb') as f:
                pickle.dump(sample_data, f)
    
    def load_checkpoint(self, checkpoint_path: str):
        """Enhanced checkpoint loading for Deep CFR"""
        if not self.networks:
            print("No neural networks available for loading")
            return
        
        try:
            checkpoint = torch.load(checkpoint_path, map_location=self.device)
            
            # Load network states
            self.networks.value_network.load_state_dict(checkpoint['value_network'])
            self.networks.advantage_network.load_state_dict(checkpoint['advantage_network'])
            self.networks.policy_network.load_state_dict(checkpoint['policy_network'])
            
            # Load optimizers
            self.networks.value_optimizer.load_state_dict(checkpoint['value_optimizer'])
            self.networks.advantage_optimizer.load_state_dict(checkpoint['advantage_optimizer'])
            self.networks.policy_optimizer.load_state_dict(checkpoint['policy_optimizer'])
            
            # Load training state
            self.iteration = checkpoint.get('iteration', 0)
            self.advantages_trained = checkpoint.get('advantages_trained', 0)
            self.strategies_trained = checkpoint.get('strategies_trained', 0)
            
            print(f"Loaded Deep CFR checkpoint from iteration {self.iteration:,}")
            print(f"Training state: Adv={self.advantages_trained:,}, Strat={self.strategies_trained:,}")
            
        except Exception as e:
            print(f"Error loading Deep CFR checkpoint: {e}")
    
    def get_exploitability_estimate(self) -> float:
        """Estimate exploitability of current strategy"""
        # Simplified exploitability calculation
        # In practice, this would require computing best response
        
        if len(self.advantage_memories) == 0:
            return float('inf')
        
        # Use average advantage magnitude as proxy
        recent_advantages = [
            abs(item['advantage']) 
            for item in list(self.advantage_memories.buffer)[-1000:]
        ]
        
        if recent_advantages:
            return np.mean(recent_advantages) * 1000  # Scale to mbb/100
        else:
            return float('inf')

def create_deep_cfr_trainer(config=None, simplified: bool = True) -> DeepCFRTrainer:
    """Factory function to create Deep CFR trainer"""
    return DeepCFRTrainer(config, simplified)