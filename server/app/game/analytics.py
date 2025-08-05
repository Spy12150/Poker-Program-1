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
        # Session-only stats (in memory, no persistence)
        self.session_stats = self._get_default_stats()
        self.read_only_mode = False
        self.persist_data = False  # Disable file persistence
    
    def _get_default_stats(self) -> Dict:
        """Get default stats structure (session-only, no file loading)"""
        return {
            'total_hands': 0,
            'player_wins': 0,
            'ai_wins': 0,
            'showdowns': 0,
            'player_stats': {
                'vpip': 0.0,  # Voluntarily put in pot %
                'hands_played': 0,
                'vpip_hands': 0
            },
            'ai_stats': {
                'vpip': 0.0,
                'hands_played': 0,  
                'vpip_hands': 0
            }
            # Removed hand_history - no persistence needed
        }
    
    def save_stats(self):
        """Save statistics to file - DISABLED for session-only mode"""
        if not self.persist_data:
            return  # Skip file operations for session-only analytics
        
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.session_stats, f, indent=2)
        except Exception as e:
            print(f"Error saving stats: {e}")
    
    def record_hand(self, game_state: Dict, winner_info: List[Dict], 
                   action_history: List[Dict]):
        """Record a completed hand for session analytics (no persistence)"""
        self.session_stats['total_hands'] += 1
        
        # Update win counts
        if winner_info and len(winner_info) > 0:
            if 'Player 1' in winner_info[0]['name']:
                self.session_stats['player_wins'] += 1
            else:
                self.session_stats['ai_wins'] += 1
        
        # Update showdown count (simplified check)
        active_players = len([p for p in game_state['players'] if p['status'] == 'active'])
        if active_players > 1:
            self.session_stats['showdowns'] += 1
        
        # Calculate VPIP only (lightweight)
        self._update_player_vpip(action_history)
        
        # No file saving - session only!
    
    def _update_player_vpip(self, action_history: List[Dict]):
        """Update VPIP statistics only (session-only, lightweight)"""
        # Get preflop actions only
        preflop_actions = [a for a in action_history if a.get('round') == 'preflop']
        
        # Check if players voluntarily put money in pot preflop
        player_preflop = [a for a in preflop_actions if 'Player 1' in a.get('player', '')]
        ai_preflop = [a for a in preflop_actions if 'Player 2' in a.get('player', '')]
        
        # Update hands played counter
        self.session_stats['player_stats']['hands_played'] += 1
        self.session_stats['ai_stats']['hands_played'] += 1
        
        # Check for VPIP actions (call/raise, not fold)
        if any(a.get('action') in ['call', 'raise'] for a in player_preflop):
            self.session_stats['player_stats']['vpip_hands'] += 1
            
        if any(a.get('action') in ['call', 'raise'] for a in ai_preflop):
            self.session_stats['ai_stats']['vpip_hands'] += 1
        
        # Calculate VPIP percentage
        player_hands = self.session_stats['player_stats']['hands_played']
        ai_hands = self.session_stats['ai_stats']['hands_played']
        
        if player_hands > 0:
            self.session_stats['player_stats']['vpip'] = (
                self.session_stats['player_stats']['vpip_hands'] / player_hands
            )
        
        if ai_hands > 0:
            self.session_stats['ai_stats']['vpip'] = (
                self.session_stats['ai_stats']['vpip_hands'] / ai_hands
            )
    
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
        """Get recent hand history - DISABLED (no hand history stored)"""
        return []

# Global analytics instance
analytics = GameAnalytics()
