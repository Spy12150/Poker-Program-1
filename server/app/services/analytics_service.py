"""
Analytics Service - Handles game analytics and statistics
"""
from typing import Dict, List
from app.game.analytics import analytics


class AnalyticsService:
    """Service class for managing game analytics and statistics"""
    
    def __init__(self):
        self.analytics_engine = analytics
    
    def get_session_summary(self) -> Dict:
        """
        Get analytics summary for the current session
        
        Returns:
            Dictionary containing session statistics
        """
        return self.analytics_engine.get_session_summary()
    
    def get_recent_hands(self, count: int = 5) -> List[Dict]:
        """
        Get recent hands data
        
        Args:
            count: Number of recent hands to retrieve
            
        Returns:
            List of recent hand data
        """
        return self.analytics_engine.get_recent_hands(count)
    
    def record_hand(self, game_state: Dict, winners: List[Dict], action_history: List[Dict]) -> None:
        """
        Record a completed hand for analytics
        
        Args:
            game_state: Current game state
            winners: List of winning players
            action_history: List of actions taken during the hand
        """
        self.analytics_engine.record_hand(game_state, winners, action_history)
    
    def get_player_statistics(self, player_name: str) -> Dict:
        """
        Get statistics for a specific player
        
        Args:
            player_name: Name of the player
            
        Returns:
            Dictionary containing player statistics
        """
        # This would be implemented if analytics.py supports it
        # For now, return basic stats from session summary
        summary = self.get_session_summary()
        return {
            'player_name': player_name,
            'hands_played': summary.get('total_hands', 0),
            'hands_won': summary.get('player_wins', 0),
            'win_rate': summary.get('player_win_rate', 0.0)
        }
    
    def get_analytics_report(self) -> Dict:
        """
        Get comprehensive analytics report
        
        Returns:
            Dictionary containing summary and recent hands
        """
        return {
            'summary': self.get_session_summary(),
            'recent_hands': self.get_recent_hands(5)
        }
