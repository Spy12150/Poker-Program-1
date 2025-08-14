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
import json
import datetime

from .config import get_config
from .game_abstraction import create_game_abstraction
from .information_set import create_information_set_manager, GameState, InformationSet
from .neural_networks import create_networks
from .action_space import ACTION_MAP, ACTION_LIST

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
        # Use module-level torch import; avoid local import shadowing
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
        
        # Set seeds for reproducibility (no local import to avoid shadowing)
        try:
            torch.manual_seed(42)
        except Exception:
            pass
        random.seed(42)
        np.random.seed(42)

        # Training state
        self.iteration = 0
        self.total_utility = defaultdict(float)
        self.training_history = []
        self._heartbeat_last = time.time()
        self._iter_budget_total = getattr(self.config, 'MAX_NODES_PER_ITERATION', 100000)
        # Results logging setup
        self._init_results_writer()
        # Per-run models directory aligned with results run folder
        try:
            run_tag = os.path.basename(getattr(self, '_results_dir', 'run_unknown'))
            self._models_dir = os.path.join(self.config.MODEL_SAVE_PATH, run_tag)
            os.makedirs(self._models_dir, exist_ok=True)
        except Exception:
            self._models_dir = self.config.MODEL_SAVE_PATH
        
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
        last_heartbeat = start_time
        
        for i in range(iterations):
            self.iteration += 1
            
            # Run one CFR iteration (shared traversal budget across both players)
            shared_budget = [self.config.MAX_NODES_PER_ITERATION]
            self._iter_budget_total = self.config.MAX_NODES_PER_ITERATION
            self.cfr_iteration(shared_budget)
            
            # Periodic updates and logging
            # Iteration-based progress
            if self.iteration % self.config.PRINT_FREQUENCY == 0:
                elapsed = max(1e-6, time.time() - start_time)
                its_per_sec = self.iteration / elapsed
                print(f"Iter {self.iteration:,} | {its_per_sec:.0f} it/s | InfoSets: {len(self.info_set_manager.information_sets):,}")
            # Optional per-iteration print (testing only)
            if getattr(self.config, 'VERBOSE_EACH_ITERATION', False):
                print(f"[Iter {self.iteration}] InfoSets: {len(self.info_set_manager.information_sets):,}")
            # Per-iteration results write (lightweight)
            if self.iteration % getattr(self.config, 'RESULTS_WRITE_EVERY', 1000) == 0:
                self._write_iteration_result({'iteration': self.iteration, 'info_sets': len(self.info_set_manager.information_sets)})

            # Time-based heartbeat every LOG_INTERVAL_SECONDS
            now = time.time()
            if now - last_heartbeat >= getattr(self.config, 'LOG_INTERVAL_SECONDS', 60):
                print(
                    f"[Heartbeat] Elapsed: {int(now - start_time)}s | Iter: {self.iteration:,} | "
                    f"InfoSets: {len(self.info_set_manager.information_sets):,}"
                )
                last_heartbeat = now
            
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
        self._close_results_writer()
    
    def cfr_iteration(self, shared_budget: list):
        """Run one iteration of CFR"""
        # Create a new hand
        game_state = self.create_random_game_state()
        
        # Traverse game tree for both players
        for player in [0, 1]:
            # Use the shared budget so both traversals combined respect MAX_NODES_PER_ITERATION
            self.cfr_recursive(game_state, player, 1.0, 1.0, 0, shared_budget)
    
    def cfr_recursive(self, game_state: GameState, traversing_player: int, 
                     reach_prob_0: float, reach_prob_1: float, depth: int = 0, node_budget: list = None) -> float:
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
        # Initialize and check traversal budgets
        if node_budget is None:
            node_budget = [self.config.MAX_NODES_PER_ITERATION]
        node_budget[0] -= 1
        if node_budget[0] <= 0:
            return 0.0

        # Depth guard to prevent runaway recursion in simplified simulator
        if depth >= 200:
            return 0.0
        if self.is_terminal(game_state):
            return self.get_terminal_utility(game_state, traversing_player)
        
        # Chance node (dealing cards)
        if self.is_chance_node(game_state):
            return self.handle_chance_node(game_state, traversing_player, reach_prob_0, reach_prob_1)
        
        # Player decision node (MCCFR outcome sampling)
        current_player = game_state.current_player
        info_set = self.info_set_manager.get_information_set(game_state, current_player)
        
        # Get current strategy
        strategy = info_set.get_strategy()

        # Time-based heartbeat even during traversal
        now = time.time()
        if now - self._heartbeat_last >= getattr(self.config, 'LOG_INTERVAL_SECONDS', 60):
            used = self._iter_budget_total - node_budget[0]
            print(
                f"[Heartbeat] Elapsed: {int(now - (now - (now - self._heartbeat_last)))}s | Iter: {self.iteration:,} | "
                f"UsedNodes: {used:,}/{self._iter_budget_total:,} | InfoSets: {len(self.info_set_manager.information_sets):,}"
            )
            self._heartbeat_last = now
        
        # Sampling both players to bound node growth
        actions = list(strategy.keys())
        if not actions:
            return 0.0
        probs = np.array([max(strategy.get(a, 0.0), 0.0) for a in actions], dtype=np.float64)
        s = probs.sum()
        if s <= 0 or not np.isfinite(s):
            probs = np.ones_like(probs, dtype=np.float64) / len(probs)
        else:
            probs = probs / s
        sampled_action = np.random.choice(actions, p=probs)
        new_state = self.apply_action(game_state, sampled_action)
        if current_player == 0:
            new_r0, new_r1 = reach_prob_0 * strategy.get(sampled_action, 0), reach_prob_1
        else:
            new_r0, new_r1 = reach_prob_0, reach_prob_1 * strategy.get(sampled_action, 0)
        sampled_value = self.cfr_recursive(new_state, traversing_player, new_r0, new_r1, depth + 1, node_budget)

        # Build action utilities for regret update: sampled gets its value, others baseline
        action_utilities = {a: sampled_value for a in actions}
        action_utilities[sampled_action] = sampled_value
        
        # Update regrets and strategies for traversing player
        if current_player == traversing_player:
            # Calculate reach probability for opponent
            opponent_reach_prob = reach_prob_1 if current_player == 0 else reach_prob_0
            
            # Update regrets
            info_set.update_regrets(action_utilities, opponent_reach_prob)
            
            # Store training data for neural networks
            if self.networks:
                self.store_training_data(info_set, action_utilities, opponent_reach_prob)
        
        # Update strategy sum with iteration weighting (CFR+ averaging)
        reach_prob = reach_prob_0 if current_player == 0 else reach_prob_1
        info_set.update_strategy_sum(reach_prob, iteration=self.iteration)
        
        # Return expected utility
        # Safe expected utility with strategy sanitization
        probs = np.array([max(strategy.get(a, 0.0), 0.0) for a in info_set.legal_actions], dtype=np.float64)
        s = probs.sum()
        if s <= 0:
            probs = np.ones_like(probs) / len(probs)
        else:
            probs = probs / s
        expected_utility = float(sum(probs[i] * action_utilities[a] for i, a in enumerate(info_set.legal_actions)))
        
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

        # Showdown marker in history
        if game_state.betting_history and game_state.betting_history[-1] == 'showdown':
            return True

        # Too long sequence guard
        if len(game_state.betting_history) > 60:
            return True

        # One player left
        if active_players <= 1:
            return True

        # River closed by call/check-check
        if game_state.street == 'river':
            # Bets matched and last action closed
            try:
                p0, p1 = game_state.players[0], game_state.players[1]
                bets_matched = p0['current_bet'] == p1['current_bet'] == game_state.current_bet
                prev = game_state.betting_history[-1] if game_state.betting_history else ''
                prev2 = game_state.betting_history[-2] if len(game_state.betting_history) >= 2 else ''
                if bets_matched and (prev == 'call' or (prev == 'check' and prev2 == 'check')):
                    return True
            except Exception:
                pass

        return False
    
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
            current_player=1 - game_state.current_player,  # Switch by default; may reset on street advance
            betting_history=game_state.betting_history + [action],
            hand_history=game_state.hand_history.copy()
        )
        
        # Apply action effects (improved simplified consistency)
        current_player = game_state.current_player
        player = new_state.players[current_player]
        opponent = new_state.players[1 - current_player]
        to_call = max(0, new_state.current_bet - player['current_bet'])
        prev_action = game_state.betting_history[-1] if game_state.betting_history else ''
        
        if action == 'fold':
            player['status'] = 'folded'
            # Hand ends immediately on fold
            new_state.betting_history.append('showdown')
            return new_state
        elif action == 'call':
            call_amount = min(to_call, player['stack'])
            player['stack'] -= call_amount
            player['current_bet'] += call_amount
            new_state.pot += call_amount
        elif 'bet' in action or 'raise' in action:
            # Extract fraction or BB size
            try:
                size_str = action.split('_')[1]
                size = float(size_str)
            except Exception:
                size = 1.0

            increment = 0
            if new_state.street == 'preflop':
                increment = int(size * 20)  # BB=20
            else:
                increment = int(size * max(new_state.pot, 1))

            # Raise to amount is current player bet + increment
            target_total = max(new_state.current_bet, player['current_bet']) + increment
            raise_amount = max(0, target_total - player['current_bet'])
            raise_amount = min(raise_amount, player['stack'])
            player['stack'] -= raise_amount
            player['current_bet'] += raise_amount
            new_state.pot += raise_amount
            new_state.current_bet = max(new_state.current_bet, player['current_bet'])
        
        # Determine if betting round is closed
        p0, p1 = new_state.players[0], new_state.players[1]
        bets_matched = p0['current_bet'] == p1['current_bet'] == new_state.current_bet
        last = new_state.betting_history[-1] if new_state.betting_history else ''
        second_last = new_state.betting_history[-2] if len(new_state.betting_history) >= 2 else ''
        round_closed = (last == 'call') or (last == 'check' and second_last == 'check')

        if bets_matched and round_closed:
            # Advance street or showdown
            if new_state.street == 'river':
                new_state.betting_history.append('showdown')
                return new_state

            # Advance to next street and deal missing cards
            next_street_map = {'preflop': 'flop', 'flop': 'turn', 'turn': 'river'}
            new_state.street = next_street_map.get(new_state.street, 'river')

            # Reset bets
            new_state.current_bet = 0
            for p in new_state.players:
                p['current_bet'] = 0

            # Deal community cards if needed
            try:
                deck = create_deck()
                used = set(new_state.board + new_state.players[0]['hand'] + new_state.players[1]['hand'])
                deck = [c for c in deck if c not in used]
                need_by_street = {'flop': 3, 'turn': 4, 'river': 5}
                need = need_by_street.get(new_state.street, len(new_state.board))
                while len(new_state.board) < need and deck:
                    new_state.board.append(deck.pop())
            except Exception:
                pass

            # Set action starts with player 0 on new street for simplicity
            new_state.current_player = 0

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
        
        # Use unified action mapping
        from .action_space import ACTION_MAP
        action_map = ACTION_MAP
        action_indices = torch.tensor([action_map.get(item['action'], 0) for item in batch]).to(self.device)
        
        advantages = torch.tensor([item['advantage'] for item in batch], dtype=torch.float32).to(self.device)
        # Normalize advantages for stability
        std = advantages.std().clamp(min=1e-6)
        advantages = advantages / std

        loss = self.networks.train_advantage_network(features, action_indices, advantages)
        
        if self.iteration % 10000 == 0:
            print(f"Advantage network loss: {loss:.6f}")
    
    def train_policy_network(self, batch: List[Dict]):
        """Train policy network on batch of data"""
        features = torch.stack([torch.tensor(item['features']) for item in batch]).to(self.device)
        
        # Convert strategies to probability vectors and build strict masks
        from .action_space import ACTION_MAP
        max_actions = len(ACTION_MAP)
        action_probs = torch.zeros(len(batch), max_actions).to(self.device)
        action_masks = torch.zeros(len(batch), max_actions, dtype=torch.float32).to(self.device)
        
        for i, item in enumerate(batch):
            strategy = item['strategy']
            legal_actions = item.get('legal_actions') or list(strategy.keys())
            for action in legal_actions:
                if action in ACTION_MAP:
                    action_masks[i, ACTION_MAP[action]] = 1.0
            # Fill probabilities only on legal actions
            for action, prob in strategy.items():
                if action in ACTION_MAP and action_masks[i, ACTION_MAP[action]] == 1.0:
                    action_probs[i, ACTION_MAP[action]] = prob
        
        loss = self.networks.train_policy_network(features, action_probs, action_masks)
        
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
        # Persist evaluation snapshot
        self._write_iteration_result({
            'iteration': self.iteration,
            'phase': 'eval',
            'info_sets': num_info_sets,
            'avg_advantage_abs': float(avg_advantage) if self.advantage_buffer else None,
            'buffer_memory_mb': float(buffer_memory),
        })
        
        print("=" * 50)
    
    def save_checkpoint(self):
        """Save training checkpoint"""
        # Save checkpoints under a dedicated per-run checkpoints directory
        base_dir = getattr(self, '_models_dir', self.config.MODEL_SAVE_PATH)
        checkpoint_dir = os.path.join(base_dir, 'checkpoints')
        os.makedirs(checkpoint_dir, exist_ok=True)
        checkpoint_path = os.path.join(checkpoint_dir, f"checkpoint_{self.iteration}.pkl")
        
        # Save information sets
        self.info_set_manager.save_strategies(checkpoint_path.replace('.pkl', '_strategies.pkl'))
        
        # Save neural networks
        if self.networks:
            self.networks.save_models(checkpoint_path.replace('.pkl', '_networks.pth'))
        
        print(f"Saved checkpoint at iteration {self.iteration:,} -> {checkpoint_dir}")
        # Track checkpoint in results
        self._write_iteration_result({'iteration': self.iteration, 'event': 'checkpoint', 'path': checkpoint_path})
    
    def save_final_strategy(self):
        """Save final trained strategy"""
        models_dir = getattr(self, '_models_dir', self.config.MODEL_SAVE_PATH)
        os.makedirs(models_dir, exist_ok=True)
        final_path = os.path.join(models_dir, "final_strategy.pkl")
        self.info_set_manager.save_strategies(final_path)
        
        if self.networks:
            networks_path = os.path.join(models_dir, "final_networks.pth")
            self.networks.save_models(networks_path)
        print(f"Saved final strategy to {final_path}")
        self._write_iteration_result({'iteration': self.iteration, 'event': 'final_save', 'strategy_path': final_path})
    
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

    # -------------------- Results logging helpers --------------------
    def _init_results_writer(self):
        base = getattr(self.config, 'RESULTS_BASE_PATH', 'server/app/game/cfr_ai/results')
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        run_dir = os.path.join(base, f"run_{timestamp}")
        os.makedirs(run_dir, exist_ok=True)
        self._results_dir = run_dir
        self._results_path = os.path.join(run_dir, 'results.jsonl')
        # Write run metadata
        meta = {
            'run_started_at': timestamp,
            'config': self.config.to_dict(),
            'trainer': 'NeuralCFRTrainer'
        }
        with open(os.path.join(run_dir, 'meta.json'), 'w') as f:
            json.dump(meta, f)
        # Create empty file for append-only writes
        with open(self._results_path, 'a') as _:
            pass

    def _write_iteration_result(self, obj: dict):
        try:
            obj = dict(obj)
            obj.setdefault('t', time.time())
            with open(self._results_path, 'a') as f:
                f.write(json.dumps(obj) + '\n')
        except Exception:
            pass

    def _close_results_writer(self):
        # Nothing to close for simple file appends, but keep for symmetry
        try:
            with open(os.path.join(self._results_dir, 'run_complete'), 'w') as f:
                f.write(str(time.time()))
        except Exception:
            pass

def create_trainer(config=None, simplified: bool = True) -> NeuralCFRTrainer:
    """Factory function to create CFR trainer"""
    return NeuralCFRTrainer(config, simplified)