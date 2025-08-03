"""
Game analytics and statistics tracking for poker sessions
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any

class GameAnalytics:
    def __init__(self, data_file="game_stats.json"):
        self.data_file = data_file
        self.session_stats = self.load_stats()
        self.read_only_mode = False
    
    def load_stats(self) -> Dict:
        """Load existing statistics from file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except (IOError, PermissionError, json.JSONDecodeError):
                # Handle file system issues gracefully
                print(f"Warning: Could not read {self.data_file}, using default stats")
                pass
        
        # Default stats structure
        return {
            'total_hands': 0,
            'player_wins': 0,
            'ai_wins': 0,
            'showdowns': 0,
            'player_stats': {
                'vpip': 0.0,  # Voluntarily put in pot %
                'pfr': 0.0,   # Pre-flop raise %
                'fold_to_bet': 0.0,
                'avg_bet_size': 0.0,
                'total_winnings': 0
            },
            'ai_stats': {
                'vpip': 0.0,
                'pfr': 0.0,
                'fold_to_bet': 0.0,
                'avg_bet_size': 0.0,
                'total_winnings': 0
            },
            'hand_history': []
        }
    
    def save_stats(self):
        """Save statistics to file"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.session_stats, f, indent=2)
        except Exception as e:
            print(f"Error saving stats: {e}")
    
    def record_hand(self, game_state: Dict, winner_info: List[Dict], 
                   action_history: List[Dict]):
        """Record a completed hand for analysis"""
        hand_data = {
            'timestamp': datetime.now().isoformat(),
            'winner': winner_info[0]['name'] if winner_info else 'Unknown',
            'pot_size': game_state.get('pot', 0),
            'showdown': len([p for p in game_state['players'] if p['status'] == 'active']) > 1,
            'player_hand': game_state['players'][0]['hand'],
            'ai_hand': game_state['players'][1]['hand'],
            'community': game_state['community'],
            'actions': action_history
        }
        
        self.session_stats['hand_history'].append(hand_data)
        self.session_stats['total_hands'] += 1
        
        # Update win counts
        if winner_info and len(winner_info) > 0:
            if 'Player 1' in winner_info[0]['name']:
                self.session_stats['player_wins'] += 1
            else:
                self.session_stats['ai_wins'] += 1
        
        # Update showdown count
        if hand_data['showdown']:
            self.session_stats['showdowns'] += 1
        
        # Calculate player statistics
        self._update_player_stats(game_state, action_history)
        
        # Save after each hand
        self.save_stats()
    
    def _update_player_stats(self, game_state: Dict, action_history: List[Dict]):
        """Update detailed player statistics"""
        player_actions = [a for a in action_history if 'Player 1' in a['player']]
        ai_actions = [a for a in action_history if 'Player 2' in a['player']]
        
        # Calculate VPIP (voluntarily put money in pot)
        preflop_actions = [a for a in action_history if a['round'] == 'preflop']
        player_preflop = [a for a in preflop_actions if 'Player 1' in a['player']]
        ai_preflop = [a for a in preflop_actions if 'Player 2' in a['player']]
        
        # Update running averages (simplified)
        total_hands = self.session_stats['total_hands']
        
        if total_hands > 1:
            # Player VPIP
            player_vpip_hands = len([a for a in player_preflop if a['action'] in ['call', 'raise']])
            self.session_stats['player_stats']['vpip'] = player_vpip_hands / total_hands
            
            # AI VPIP  
            ai_vpip_hands = len([a for a in ai_preflop if a['action'] in ['call', 'raise']])
            self.session_stats['ai_stats']['vpip'] = ai_vpip_hands / total_hands
    
    def get_session_summary(self) -> Dict:
        """Get summary of current session"""
        stats = self.session_stats
        total_hands = stats['total_hands']
        
        if total_hands == 0:
            return {'message': 'No hands played yet'}
        
        player_win_rate = (stats['player_wins'] / total_hands) * 100
        ai_win_rate = (stats['ai_wins'] / total_hands) * 100
        showdown_rate = (stats['showdowns'] / total_hands) * 100
        
        return {
            'total_hands': total_hands,
            'player_win_rate': f"{player_win_rate:.1f}%",
            'ai_win_rate': f"{ai_win_rate:.1f}%",
            'showdown_rate': f"{showdown_rate:.1f}%",
            'player_vpip': f"{stats['player_stats']['vpip']*100:.1f}%",
            'ai_vpip': f"{stats['ai_stats']['vpip']*100:.1f}%"
        }
    
    def get_recent_hands(self, count: int = 10) -> List[Dict]:
        """Get recent hand history"""
        return self.session_stats['hand_history'][-count:]

# Global analytics instance
analytics = GameAnalytics()
