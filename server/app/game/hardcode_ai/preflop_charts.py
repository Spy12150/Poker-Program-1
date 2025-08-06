"""
Comprehensive Preflop Charts using 11-tier/bucket system from tier_config.py

I hard coded the preflop ranges, SB RFI is roughly 80% no limp, follow standard HU charts

I was going to import full poker charts from GTOWizard
but GTO wiz doesnt have limping as SB which people do, and not enough bet sizes
so I did tier system to hard code every possibility

This system provides complete coverage of all heads-up preflop scenarios:
- SB first action (RFI) with stack depth adjustments
- BB vs SB limp (check/raise decision)
- BB vs SB raise (fold/call/3-bet with sizing-dependent ranges)
- SB vs BB 3-bet (fold/call/4-bet decisions)
- BB vs SB 4-bet (fold/call/5-bet decisions)
- SB vs BB 5-bet (fold/call decisions, usually all-in)

Check for the tiers in tier_config.py

Now granted this is pretty explotable if you play enough
Could be improved by adding different percentages for each action for tiers to improve
"""
from typing import List, Tuple, Dict, Optional
from .tier_config import TIERS, class_lookup
import random

RANK_TO_INT = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
               "8": 8, "9": 9, "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14}
INT_TO_RANK = {v: k for k, v in RANK_TO_INT.items()}

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def hand_to_tuple(hand: List[str]) -> Tuple[int, int, bool]:
    """Convert ['Ah','Kd'] to (14, 13, False)"""
    c1, c2 = hand
    r1, s1 = c1[0], c1[1]
    r2, s2 = c2[0], c2[1]
    v1, v2 = RANK_TO_INT[r1], RANK_TO_INT[r2]
    if v1 == v2:
        return (v1, v1)
    return (max(v1, v2), min(v1, v2), s1 == s2)

def categorize_bet_size(bet_size_bb: float, previous_bet_bb: float = 1.0) -> str:
    """
    Categorize bet size based on multiple of previous bet
    
    Args:
        bet_size_bb: Current bet size in big blinds
        previous_bet_bb: Previous bet/raise size in big blinds (default 1.0 for initial raises)
        
    Returns:
        Bet size category: "minraise", "standard", "large", or "overbet"
    """
    if previous_bet_bb <= 0:
        previous_bet_bb = 1.0  # Avoid division by zero
    
    # For initial raises (RFI), use absolute BB measurement
    if previous_bet_bb == 1.0:  # This indicates it's an initial raise from BB
        if bet_size_bb <= 2.5:
            return "minraise"
        elif bet_size_bb <= 3.8:
            return "standard_low"
        elif bet_size_bb <= 6:
            return "standard"
        elif bet_size_bb <= 12:
            return "large"
        else:
            return "overbet"
    
    # use multiple to group the bet sizes for actions
    multiple = bet_size_bb / previous_bet_bb
    
    if multiple <= 2.5:
        return "minraise" 
    elif multiple <= 3.8:
        return "standard_low"  
    elif multiple <= 6:
        return "standard"  
    elif multiple <= 12:
        return "large"    
    else:
        return "overbet"  

def categorize_stack_depth(stack_bb: int) -> str:
    """Categorize effective stack depth"""
    if stack_bb <= 25:
        return "short"
    elif stack_bb <= 60:
        return "medium"
    else:
        return "deep"

# ---------------------------------------------------------------------------
# Main preflop decision engine
# ---------------------------------------------------------------------------

class PreflopCharts:
    def __init__(self):
        self._build_strategy_tables()

    def _build_strategy_tables(self):
        # SB RFI ranges by stack depth
        self.sb_rfi_ranges = {
            "short": 7,    # RFI less hands when short stacked
            "medium": 8,   
            "deep": 8     
        }
        
        # BB vs SB limp: which hands to raise
        self.bb_vs_limp_raise_range = 6  # tiers 0-6 (~70%)
        
        # BB defense vs SB raise - more granular based on raise size
        self.bb_defense_ranges = {
            "minraise": {
                "call": 7,    # 7 means tiers 4-7
                "3bet": 3     # 3 means 0-3
            },
            "standard_low": {
                "call": 6,   
                "3bet": 3     
            },
            "standard": {
                "call": 5,     
                "3bet": 2      
            },
            "large": {
                "call": 3,     
                "3bet": 2     
            },
            "overbet": {
                "call": 1,   
                "3bet": 0      # Nuts only
            }
        }
        
        # SB vs BB 3-bet responses
        self.sb_vs_3bet_ranges = {
            "minraise": {  # BB 3-bet is small
                "call": 6,     
                "4bet": 3     
            },
            "standard_low": {
                "call": 4,    
                "3bet": 1     
            },
            "standard": {  
                "call": 3,    
                "4bet": 0     
            },
            "large": {  
                "call": 1,    
                "4bet": 0      
            },
            "overbet": {  
                "call": 1,     
                "4bet": 0    
            }
        }
        
        # BB vs SB 4-bet responses  
        self.bb_vs_4bet_ranges = {
            "standard_low": {
                "call": 1,    
                "5bet": 0      
            },
            "standard": {
                "call": 1,   
                "5bet": 0    
            },
            "large": {
                "5bet": 0    
            },
            "overbet": {
                "5bet": 0    
            }
        }
        
        # SB vs BB 5-bet responses - sizing dependent
        self.sb_vs_5bet_ranges = {
            "minraise": {   
                "call": 2  
            },
            "standard_low": { 
                "call": 1     
            },
            "standard": {    
                "call": 1    
            },
            "large": {       
                "call": 0    
            },
            "overbet": {      
                "call": 0     
            }
        }

    # ---------------------------------------------------------------------------
    # Public utility methods
    # ---------------------------------------------------------------------------
    
    def get_hand_tuple(self, hand: List[str]) -> Tuple:
        """Convert hand to tuple representation"""
        return hand_to_tuple(hand)

    def tier_of(self, tup: Tuple) -> int:
        """Get 0-based tier index for hand tuple"""
        return class_lookup[tup]

    def get_hand_tier(self, hand: List[str]) -> int:
        """Get tier index for a hand"""
        return self.tier_of(self.get_hand_tuple(hand))

    # ---------------------------------------------------------------------------
    # Scenario-specific decision methods
    # ---------------------------------------------------------------------------

    def sb_first_action(self, hand: List[str], stack_bb: int = 100) -> str:
        """
        SB first action
        
        Args:
            hand: Two-card hand
            stack_bb: Effective stack in big blinds
            
        Returns:
            'raise' or 'fold'
        """
        tier = self.get_hand_tier(hand)
        stack_category = categorize_stack_depth(stack_bb)
        max_tier = self.sb_rfi_ranges[stack_category]
        
        return "raise" if tier <= max_tier else "fold"

    def bb_vs_sb_limp(self, hand: List[str], stack_bb: int = 100) -> str:
        """
        BB response to SB limp
        
        Args:
            hand: Two-card hand
            stack_bb: Effective stack in big blinds
            
        Returns:
            'raise' or 'check'
        """
        tier = self.get_hand_tier(hand)
        
        # With strong hands, raise for value and to take initiative
        if tier <= self.bb_vs_limp_raise_range:
            return "raise"
        else:
            return "check"

    def bb_vs_sb_raise(self, hand: List[str], raise_size_bb: float, stack_bb: int = 100) -> str:
        """
        BB response to SB raise
        
        Args:
            hand: Two-card hand  
            raise_size_bb: Size of SB's raise in big blinds
            stack_bb: Effective stack in big blinds
            
        Returns:
            'fold', 'call', or '3bet'
        """
        tier = self.get_hand_tier(hand)
        # For initial raises, previous bet is the BB (1.0)
        bet_category = categorize_bet_size(raise_size_bb, 1.0)
        
        if bet_category not in self.bb_defense_ranges:
            bet_category = "overbet"
            
        ranges = self.bb_defense_ranges[bet_category]
        
        # First check if we should 3-bet
        if tier <= ranges["3bet"]:
            return "3bet"
        # Then check if we should call
        elif tier <= ranges["call"]:
            return "call"
        else:
            return "fold"

    def sb_vs_bb_3bet(self, hand: List[str], threeBet_size_bb: float, original_raise_bb: float, stack_bb: int = 100) -> str:
        """
        SB response to BB 3-bet
        
        Args:
            hand: Two-card hand
            threeBet_size_bb: Size of BB's 3-bet in big blinds  
            original_raise_bb: Size of original SB raise in big blinds
            stack_bb: Effective stack in big blinds
            
        Returns:
            'fold', 'call', or '4bet'
        """
        tier = self.get_hand_tier(hand)
        bet_category = categorize_bet_size(threeBet_size_bb, original_raise_bb)
        
        if bet_category not in self.sb_vs_3bet_ranges:
            bet_category = "overbet"
            
        ranges = self.sb_vs_3bet_ranges[bet_category]
        
        # Check if we should 4-bet
        if tier <= ranges["4bet"]:
            return "4bet"
        # Then check if we should call
        elif tier <= ranges["call"]:
            return "call"
        else:
            return "fold"

    def bb_vs_sb_4bet(self, hand: List[str], fourBet_size_bb: float, threeBet_size_bb: float, stack_bb: int = 100) -> str:
        """
        BB response to SB 4-bet
        
        Args:
            hand: Two-card hand
            fourBet_size_bb: Size of SB's 4-bet in big blinds
            threeBet_size_bb: Size of BB's 3-bet in big blinds
            stack_bb: Effective stack in big blinds
            
        Returns:
            'fold', 'call', or '5bet' (usually all-in)
        """
        tier = self.get_hand_tier(hand)
        bet_category = categorize_bet_size(fourBet_size_bb, threeBet_size_bb)
        
        if bet_category not in self.bb_vs_4bet_ranges:
            bet_category = "overbet"
            
        ranges = self.bb_vs_4bet_ranges[bet_category]
        
        # Check if we should 5-bet (usually all-in)
        if tier <= ranges["5bet"]:
            return "5bet"
        # Then check if we should call
        elif tier <= ranges["call"]:
            return "call"
        else:
            return "fold"

    def bb_vs_sb_3bet(self, hand: List[str], threeBet_size_bb: float, original_raise_bb: float, stack_bb: int = 100) -> str:
        """
        BB response to SB 3-bet (after BB raised and SB 3-bet)
        
        Args:
            hand: Two-card hand
            threeBet_size_bb: Size of SB's 3-bet in big blinds
            original_raise_bb: Size of BB's original raise in big blinds
            stack_bb: Effective stack in big blinds
            
        Returns:
            'fold', 'call', or '4bet'
        """
        tier = self.get_hand_tier(hand)
        bet_category = categorize_bet_size(threeBet_size_bb, original_raise_bb)
        
        # Use the same ranges as SB vs BB 3-bet (symmetric)
        if bet_category not in self.sb_vs_3bet_ranges:
            bet_category = "overbet"
            
        ranges = self.sb_vs_3bet_ranges[bet_category]
        
        # Check if we should 4-bet
        if tier <= ranges["4bet"]:
            return "4bet"
        # Then check if we should call
        elif tier <= ranges["call"]:
            return "call"
        else:
            return "fold"

    def sb_vs_bb_5bet(self, hand: List[str], fiveBet_size_bb: float, fourBet_size_bb: float, stack_bb: int = 100) -> str:
        """
        SB response to BB 5-bet (sizing-dependent ranges)
        
        Args:
            hand: Two-card hand
            fiveBet_size_bb: Size of BB's 5-bet in big blinds
            fourBet_size_bb: Size of SB's 4-bet in big blinds
            stack_bb: Effective stack in big blinds
            
        Returns:
            'fold' or 'call'
        """
        tier = self.get_hand_tier(hand)
        bet_category = categorize_bet_size(fiveBet_size_bb, fourBet_size_bb)
        
        if bet_category not in self.sb_vs_5bet_ranges:
            bet_category = "overbet"
            
        call_range = self.sb_vs_5bet_ranges[bet_category]["call"]
        
        # Call if our hand is strong enough for this bet size
        return "call" if tier <= call_range else "fold"

    # ---------------------------------------------------------------------------
    # Main decision engine
    # ---------------------------------------------------------------------------

    def get_preflop_action(
        self,
        hand: List[str],
        position: str,
        action_to_hero: str,
        raise_size_bb: float = 0,
        stack_bb: int = 100,
        pot_bb: float = 0,
        num_raises: int = 0,
        bet_history: List[float] = None
    ) -> str:
        """
        Comprehensive preflop decision engine
        
        Args:
            hand: Two-card hand
            position: 'button' (SB) or 'bb' (BB)
            action_to_hero: 'none', 'limp', 'raise', '3bet', '4bet', '5bet'
            raise_size_bb: Size of last raise in big blinds
            stack_bb: Effective stack in big blinds
            pot_bb: Current pot size in big blinds
            num_raises: Number of raises in current betting round
            bet_history: List of bet sizes in order [original_raise, 3bet, 4bet, ...]
            
        Returns:
            Action string: 'fold', 'check', 'call', 'raise', '3bet', '4bet', '5bet'
        """
        
        if bet_history is None:
            bet_history = []
        
        # SCENARIO 1: SB first action (RFI opportunity)
        if position == "button" and action_to_hero == "none":
            return self.sb_first_action(hand, stack_bb)
        
        # SCENARIO 2: BB vs SB limp
        elif position == "bb" and action_to_hero == "limp":
            return self.bb_vs_sb_limp(hand, stack_bb)
        
        # SCENARIO 3: BB vs SB raise (first raise)
        elif position == "bb" and action_to_hero == "raise" and num_raises == 1:
            return self.bb_vs_sb_raise(hand, raise_size_bb, stack_bb)
        
        # SCENARIO 4A: SB vs BB 3-bet  
        elif position == "button" and action_to_hero == "raise" and num_raises == 2:
            # Get original SB raise size from bet history or estimate
            original_raise_bb = bet_history[0] if bet_history else self._estimate_original_raise(pot_bb, raise_size_bb)
            return self.sb_vs_bb_3bet(hand, raise_size_bb, original_raise_bb, stack_bb)
        
        # SCENARIO 4B: BB vs SB 3-bet (after BB isolated a limper or raised)
        elif position == "bb" and action_to_hero == "raise" and num_raises == 2:
            # BB is facing a 3-bet - need to treat this as 3-bet defense, not initial raise defense
            original_raise_bb = bet_history[0] if bet_history else self._estimate_original_raise(pot_bb, raise_size_bb)
            return self.bb_vs_sb_3bet(hand, raise_size_bb, original_raise_bb, stack_bb)
        
        # SCENARIO 5: BB vs SB 4-bet
        elif position == "bb" and action_to_hero == "raise" and num_raises == 3:
            # Get 3-bet size from bet history or estimate
            threeBet_size_bb = bet_history[1] if len(bet_history) > 1 else self._estimate_previous_3bet(pot_bb, raise_size_bb)
            return self.bb_vs_sb_4bet(hand, raise_size_bb, threeBet_size_bb, stack_bb)
        
        # SCENARIO 6: SB vs BB 5-bet
        elif position == "button" and action_to_hero == "raise" and num_raises == 4:
            # Get 4-bet size from bet history or estimate
            fourBet_size_bb = bet_history[2] if len(bet_history) > 2 else self._estimate_previous_4bet(pot_bb, raise_size_bb)
            return self.sb_vs_bb_5bet(hand, raise_size_bb, fourBet_size_bb, stack_bb)
        
        # FALLBACK: Unknown scenario (6-bet, 7-bet+) - be conservative but aggressive with nuts
        else:
            tier = self.get_hand_tier(hand)
            if tier == 0:  # Tier 0: Shove with absolute premium hands (AA, KK, QQ, JJ, AKs, AKo, AQs)
                return "raise"  # Go all-in
            elif tier == 1:  # Tier 1: Call with strong hands (99, TT, AJs, AQo, etc.)
                return "call" if raise_size_bb > 0 else "check"
            else:
                return "fold"
    
    def _estimate_original_raise(self, pot_bb: float, threeBet_size_bb: float) -> float:
        """Estimate original raise size from pot and 3-bet size"""
        # Rough estimation: if pot is X and 3-bet is Y, original raise was likely (pot - 1.5) / 2
        # This is imperfect but better than nothing
        estimated = max(2.0, (pot_bb - 1.5) / 2)
        return min(estimated, threeBet_size_bb / 2.5)  # Cap at reasonable multiple
    
    def _estimate_previous_3bet(self, pot_bb: float, fourBet_size_bb: float) -> float:
        """Estimate 3-bet size from pot and 4-bet size"""
        # Rough estimation based on typical 4-bet sizing relative to 3-bet
        return max(6.0, fourBet_size_bb / 2.5)
    
    def _estimate_previous_4bet(self, pot_bb: float, fiveBet_size_bb: float) -> float:
        """Estimate 4-bet size from pot and 5-bet size"""
        # Rough estimation - 5-bets are usually 2-3x the 4-bet
        return max(15.0, fiveBet_size_bb / 2.5)

    # ---------------------------------------------------------------------------
    # Legacy methods (for backward compatibility)
    # ---------------------------------------------------------------------------

    def should_open_button(self, hand: List[str], stack_bb: int = 100) -> bool:
        """Legacy method - use sb_first_action instead"""
        return self.sb_first_action(hand, stack_bb) == "raise"

    def should_defend_bb(self, hand: List[str], raise_size_bb: float = 3, stack_bb: int = 100) -> str:
        """Legacy method - use bb_vs_sb_raise instead"""
        return self.bb_vs_sb_raise(hand, raise_size_bb, stack_bb)
