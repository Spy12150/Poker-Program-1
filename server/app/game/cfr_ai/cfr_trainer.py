"""
Neural CFR Trainer

This module implements the core CFR training algorithm with neural network approximation.
It includes both traditional CFR and neural CFR variants.
"""

import random
import numpy as np
import torch
from typing import List, Dict, Tuple, Optional, Any
from collections import defaultdict, deque
import time
import os

from .config import get_config
from .game_abstraction import create_game_abstraction
from .information_set import create_information_set_manager, GameState, InformationSet
from .neural_networks import create_networks

# Import game engine
try:
    from ..poker import create_deck
    from ..hand_eval_lib import evaluate_hand
    from ..config import BIG_BLIND, SMALL_BLIND
except ImportError:
    print("Warning: Could not import poker game modules")
    BIG_BLIND, SMALL_BLIND = 20, 10
    def create_deck():
        suits = ['s', 'h', 'd', 'c']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        return [r + s for r in ranks for s in suits]

class NeuralCFRTrainer:
    """
    Neural CFR trainer that combines traditional CFR with neural network approximation
    """
    
    def __init__(self, config=None, simplified: bool = True):
        self.config = config or get_config(simplified=simplified)
        self.device = torch.device(self.config.DEVICE)
        
        # Initialize components
        self.game_abstraction = create_game_abstraction(self.config)
        self.info_set_manager = create_information_set_manager(self.game_abstraction)
        
        # Initialize neural networks
        try:
            self.networks = create_networks(self.config, str(self.device))
        except Exception as e:
            print(f"Warning: Could not initialize neural networks: {e}")
            print("Falling back to tabular CFR")
            self.networks = None
        
        # Training state
        self.iteration = 0
        self.total_utility = defaultdict(float)
        self.training_history = []
        
        # Memory buffers for neural CFR
        self.advantage_buffer = deque(maxlen=self.config.MEMORY_SIZE)
        self.strategy_buffer = deque(maxlen=self.config.MEMORY_SIZE)
        
        print(f"Initialized Neural CFR Trainer")
        print(f"Game abstraction: {self.game_abstraction.get_bucket_info()}")
        if self.networks:
            print(f"Neural networks: {self.networks.get_model_info()}")
    
    def train(self, iterations: int = None):
        """Main training loop"""
        iterations = iterations or self.config.CFR_ITERATIONS
        
        print(f"Starting CFR training for {iterations:,} iterations...")
        start_time = time.time()
        
        for i in range(iterations):
            self.iteration += 1
            
            # Run one CFR iteration
            self.cfr_iteration()
            
            # Periodic updates and logging
            if self.iteration % 1000 == 0:
                elapsed = time.time() - start_time
                its_per_sec = self.iteration / elapsed
                print(f"Iteration {self.iteration:,} ({its_per_sec:.1f} it/s)")
            
            # Update neural networks periodically
            if self.networks and self.iteration % self.config.UPDATE_FREQUENCY == 0:
                self.update_neural_networks()
            
            # Save checkpoints
            if self.iteration % self.config.SAVE_FREQUENCY == 0:
                self.save_checkpoint()
            
            # Evaluation
            if self.iteration % self.config.EVAL_FREQUENCY == 0:
                self.evaluate()
        
        print(f"Training completed in {time.time() - start_time:.1f} seconds")
        self.save_final_strategy()
    
    def cfr_iteration(self):
        """Run one iteration of CFR"""
        # Create a new hand
        game_state = self.create_random_game_state()
        
        # Traverse game tree for both players
        for player in [0, 1]:
            self.cfr_recursive(game_state, player, 1.0, 1.0)
    
    def cfr_recursive(self, game_state: GameState, traversing_player: int, 
                     reach_prob_0: float, reach_prob_1: float) -> float:
        """
        Recursive CFR algorithm
        
        Args:
            game_state: Current game state
            traversing_player: Player whose regrets we're updating (0 or 1)
            reach_prob_0: Reach probability for player 0
            reach_prob_1: Reach probability for player 1
        
        Returns:
            Counterfactual utility for traversing player
        """
        
        # Terminal node
        if self.is_terminal(game_state):
            return self.get_terminal_utility(game_state, traversing_player)
        
        # Chance node (dealing cards)
        if self.is_chance_node(game_state):
            return self.handle_chance_node(game_state, traversing_player, reach_prob_0, reach_prob_1)
        
        # Player decision node
        current_player = game_state.current_player
        info_set = self.info_set_manager.get_information_set(game_state, current_player)
        
        # Get current strategy
        strategy = info_set.get_strategy()
        
        # Calculate counterfactual values for each action
        action_utilities = {}
        for action in info_set.legal_actions:
            # Create new game state after taking action
            new_game_state = self.apply_action(game_state, action)
            
            # Update reach probabilities
            if current_player == 0:
                new_reach_prob_0 = reach_prob_0 * strategy[action]
                new_reach_prob_1 = reach_prob_1
            else:
                new_reach_prob_0 = reach_prob_0
                new_reach_prob_1 = reach_prob_1 * strategy[action]
            
            # Recursive call
            action_utilities[action] = self.cfr_recursive(
                new_game_state, traversing_player, new_reach_prob_0, new_reach_prob_1
            )
        
        # Update regrets and strategies for traversing player
        if current_player == traversing_player:
            # Calculate reach probability for opponent
            opponent_reach_prob = reach_prob_1 if current_player == 0 else reach_prob_0
            
            # Update regrets
            info_set.update_regrets(action_utilities, opponent_reach_prob)
            
            # Store training data for neural networks
            if self.networks:
                self.store_training_data(info_set, action_utilities, opponent_reach_prob)
        
        # Update strategy sum
        reach_prob = reach_prob_0 if current_player == 0 else reach_prob_1
        info_set.update_strategy_sum(reach_prob)
        
        # Return expected utility
        expected_utility = sum(strategy[action] * action_utilities[action] 
                             for action in info_set.legal_actions)
        
        return expected_utility
    
    def create_random_game_state(self) -> GameState:
        """Create a random game state for training"""
        # Create deck and deal cards
        deck = create_deck()
        random.shuffle(deck)
        
        # Deal hole cards
        player_hands = [
            [deck.pop(), deck.pop()],  # Player 0
            [deck.pop(), deck.pop()]   # Player 1
        ]
        
        # Random street
        street = random.choice(['preflop', 'flop', 'turn', 'river'])
        
        # Deal community cards based on street
        board = []
        if street in ['flop', 'turn', 'river']:
            board.extend([deck.pop(), deck.pop(), deck.pop()])  # Flop
        if street in ['turn', 'river']:
            board.append(deck.pop())  # Turn
        if street == 'river':
            board.append(deck.pop())  # River
        
        # Create players
        stack_sizes = [random.randint(500, 2000), random.randint(500, 2000)]
        players = [
            {
                'name': f'Player {i}',
                'hand': player_hands[i],
                'stack': stack_sizes[i],
                'current_bet': 0,
                'status': 'active'
            }
            for i in range(2)
        ]
        
        # Random betting history
        betting_history = self.generate_random_betting_history(street)
        
        # Calculate pot size based on betting history
        pot = self.calculate_pot_from_history(betting_history)
        
        return GameState(
            street=street,
            board=board,
            pot=pot,
            current_bet=20,  # Simplified
            players=players,
            current_player=random.randint(0, 1),
            betting_history=betting_history,
            hand_history=[]
        )
    
    def generate_random_betting_history(self, street: str) -> List[str]:
        """Generate random but realistic betting history"""
        actions = ['check', 'call', 'bet_0.5', 'bet_1.0', 'raise_2.5']
        
        # Length depends on street
        max_actions = {'preflop': 4, 'flop': 3, 'turn': 2, 'river': 2}
        num_actions = random.randint(0, max_actions.get(street, 2))
        
        return [random.choice(actions) for _ in range(num_actions)]
    
    def calculate_pot_from_history(self, betting_history: List[str]) -> float:
        """Calculate pot size from betting history"""
        pot = SMALL_BLIND + BIG_BLIND  # Start with blinds
        
        for action in betting_history:
            if 'bet' in action or 'raise' in action:
                pot += 50  # Simplified
            elif action == 'call':
                pot += 25  # Simplified
        
        return pot
    
    def is_terminal(self, game_state: GameState) -> bool:
        """Check if game state is terminal"""
        # Simplified terminal conditions
        active_players = sum(1 for p in game_state.players if p['status'] == 'active')
        
        return (
            active_players <= 1 or  # Only one player left
            (game_state.street == 'river' and len(game_state.betting_history) >= 2)  # River betting done
        )
    
    def is_chance_node(self, game_state: GameState) -> bool:
        """Check if this is a chance node (dealing cards)"""
        # For simplicity, we handle chance nodes in create_random_game_state
        return False
    
    def get_terminal_utility(self, game_state: GameState, player: int) -> float:
        """Get utility for player at terminal node"""
        if len([p for p in game_state.players if p['status'] == 'active']) == 1:
            # One player remaining - they win the pot
            if game_state.players[player]['status'] == 'active':
                return game_state.pot / 2  # Normalize by pot size
            else:
                return -game_state.pot / 2
        else:
            # Showdown - compare hands
            try:
                player_hand = game_state.players[player]['hand']
                opponent_hand = game_state.players[1-player]['hand']
                
                player_score, _ = evaluate_hand(player_hand, game_state.board)
                opponent_score, _ = evaluate_hand(opponent_hand, game_state.board)
                
                if player_score < opponent_score:  # Lower score wins
                    return game_state.pot / 2
                elif player_score > opponent_score:
                    return -game_state.pot / 2
                else:
                    return 0  # Tie
                    
            except Exception:
                return random.choice([-game_state.pot / 2, game_state.pot / 2])
    
    def handle_chance_node(self, game_state: GameState, traversing_player: int,
                          reach_prob_0: float, reach_prob_1: float) -> float:
        """Handle chance nodes (not used in simplified version)"""
        return 0
    
    def apply_action(self, game_state: GameState, action: str) -> GameState:
        """Apply action to game state and return new state"""
        # Create copy of game state
        new_state = GameState(
            street=game_state.street,
            board=game_state.board.copy(),
            pot=game_state.pot,
            current_bet=game_state.current_bet,
            players=[p.copy() for p in game_state.players],
            current_player=1 - game_state.current_player,  # Switch player
            betting_history=game_state.betting_history + [action],
            hand_history=game_state.hand_history.copy()
        )
        
        # Apply action effects (simplified)
        current_player = game_state.current_player
        player = new_state.players[current_player]
        
        if action == 'fold':
            player['status'] = 'folded'
        elif action == 'call':
            call_amount = min(50, player['stack'])  # Simplified
            player['stack'] -= call_amount
            new_state.pot += call_amount
        elif 'bet' in action or 'raise' in action:
            bet_amount = min(100, player['stack'])  # Simplified
            player['stack'] -= bet_amount
            new_state.pot += bet_amount
            new_state.current_bet = bet_amount
        
        return new_state
    
    def store_training_data(self, info_set: InformationSet, action_utilities: Dict[str, float], 
                           reach_probability: float):
        """Store training data for neural network updates"""
        if not self.networks:
            return
        
        # Calculate advantages (regrets)
        strategy = info_set.get_strategy()
        expected_utility = sum(strategy[action] * action_utilities[action] 
                             for action in info_set.legal_actions)
        
        for action in info_set.legal_actions:
            advantage = action_utilities[action] - expected_utility
            
            self.advantage_buffer.append({
                'features': info_set.features.copy(),
                'action': action,
                'advantage': advantage * reach_probability,
                'info_set_key': info_set.get_key()
            })
        
        # Store strategy data
        self.strategy_buffer.append({
            'features': info_set.features.copy(),
            'strategy': strategy.copy(),
            'legal_actions': info_set.legal_actions.copy()
        })
    
    def update_neural_networks(self):
        """Update neural networks using stored training data"""
        if not self.networks or len(self.advantage_buffer) < self.config.BATCH_SIZE:
            return
        
        # Sample training batches
        advantage_batch = random.sample(list(self.advantage_buffer), 
                                      min(self.config.BATCH_SIZE, len(self.advantage_buffer)))
        strategy_batch = random.sample(list(self.strategy_buffer),
                                     min(self.config.BATCH_SIZE, len(self.strategy_buffer)))
        
        # Train advantage network
        self.train_advantage_network(advantage_batch)
        
        # Train policy network
        self.train_policy_network(strategy_batch)
        
        # Update learning rates
        if self.iteration % 50000 == 0:
            self.networks.update_learning_rates()
    
    def train_advantage_network(self, batch: List[Dict]):
        """Train advantage network on batch of data"""
        features = torch.stack([torch.tensor(item['features']) for item in batch]).to(self.device)
        
        # Create action indices (simplified mapping)
        action_map = {'fold': 0, 'check': 1, 'call': 2, 'bet_0.5': 3, 'bet_1.0': 4, 'raise_2.5': 5}
        action_indices = torch.tensor([action_map.get(item['action'], 0) for item in batch]).to(self.device)
        
        advantages = torch.tensor([item['advantage'] for item in batch], dtype=torch.float32).to(self.device)
        
        loss = self.networks.train_advantage_network(features, action_indices, advantages)
        
        if self.iteration % 10000 == 0:
            print(f"Advantage network loss: {loss:.6f}")
    
    def train_policy_network(self, batch: List[Dict]):
        """Train policy network on batch of data"""
        features = torch.stack([torch.tensor(item['features']) for item in batch]).to(self.device)
        
        # Convert strategies to probability vectors
        max_actions = 6  # Based on our action mapping
        action_probs = torch.zeros(len(batch), max_actions).to(self.device)
        
        for i, item in enumerate(batch):
            strategy = item['strategy']
            for action, prob in strategy.items():
                action_map = {'fold': 0, 'check': 1, 'call': 2, 'bet_0.5': 3, 'bet_1.0': 4, 'raise_2.5': 5}
                if action in action_map:
                    action_probs[i, action_map[action]] = prob
        
        loss = self.networks.train_policy_network(features, action_probs)
        
        if self.iteration % 10000 == 0:
            print(f"Policy network loss: {loss:.6f}")
    
    def evaluate(self):
        """Evaluate current strategy"""
        print(f"\n=== Evaluation at iteration {self.iteration:,} ===")
        
        # Basic statistics
        num_info_sets = len(self.info_set_manager.information_sets)
        print(f"Information sets created: {num_info_sets:,}")
        
        if self.advantage_buffer:
            avg_advantage = np.mean([abs(item['advantage']) for item in list(self.advantage_buffer)[-1000:]])
            print(f"Average advantage magnitude: {avg_advantage:.6f}")
        
        # Memory usage
        buffer_memory = (len(self.advantage_buffer) + len(self.strategy_buffer)) * 0.001
        print(f"Buffer memory usage: {buffer_memory:.1f} MB")
        
        print("=" * 50)
    
    def save_checkpoint(self):
        """Save training checkpoint"""
        checkpoint_dir = self.config.MODEL_SAVE_PATH
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        checkpoint_path = os.path.join(checkpoint_dir, f"checkpoint_{self.iteration}.pkl")
        
        # Save information sets
        self.info_set_manager.save_strategies(checkpoint_path.replace('.pkl', '_strategies.pkl'))
        
        # Save neural networks
        if self.networks:
            self.networks.save_models(checkpoint_path.replace('.pkl', '_networks.pth'))
        
        print(f"Saved checkpoint at iteration {self.iteration:,}")
    
    def save_final_strategy(self):
        """Save final trained strategy"""
        final_path = os.path.join(self.config.MODEL_SAVE_PATH, "final_strategy.pkl")
        self.info_set_manager.save_strategies(final_path)
        
        if self.networks:
            networks_path = os.path.join(self.config.MODEL_SAVE_PATH, "final_networks.pth")
            self.networks.save_models(networks_path)
        
        print(f"Saved final strategy to {final_path}")
    
    def load_checkpoint(self, checkpoint_path: str):
        """Load training checkpoint"""
        # Load information sets
        strategies_path = checkpoint_path.replace('.pkl', '_strategies.pkl')
        self.info_set_manager.load_strategies(strategies_path)
        
        # Load neural networks
        if self.networks:
            networks_path = checkpoint_path.replace('.pkl', '_networks.pth')
            self.networks.load_models(networks_path)
        
        print(f"Loaded checkpoint from {checkpoint_path}")

def create_trainer(config=None, simplified: bool = True) -> NeuralCFRTrainer:
    """Factory function to create CFR trainer"""
    return NeuralCFRTrainer(config, simplified)