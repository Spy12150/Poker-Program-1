// Betting utility functions

// Logarithmic slider conversion functions
export const betToSliderPosition = (betValue, minBet, maxBet) => {
  if (minBet >= maxBet || betValue <= minBet) return 0;
  if (betValue >= maxBet) return 100;
  
  // Logarithmic scale: log(betValue/minBet) / log(maxBet/minBet)
  const logRatio = Math.log(betValue / minBet) / Math.log(maxBet / minBet);
  return Math.round(logRatio * 100);
};

export const sliderPositionToBet = (position, minBet, maxBet) => {
  if (position <= 0) return minBet;
  if (position >= 100) return maxBet;
  
  // Convert logarithmic position back to bet value
  const ratio = position / 100;
  const betValue = minBet * Math.pow(maxBet / minBet, ratio);
  return Math.round(betValue);
};

// Game state utility functions
export const getCallAmount = (gameState) => {
  if (!gameState || !gameState.players) return 0;
  const player = gameState.players[0];
  const currentBet = gameState.current_bet || 0;
  const playerCurrentBet = player.current_bet || 0;
  return Math.max(0, currentBet - playerCurrentBet);
};

export const getActualCallAmount = (gameState) => {
  if (!gameState || !gameState.players) return 0;
  const player = gameState.players[0];
  const callAmount = getCallAmount(gameState);
  // Cap call amount at player's remaining stack (for all-in calls)
  return Math.min(callAmount, player.stack);
};

export const canCheck = (gameState) => {
  return getCallAmount(gameState) === 0;
};

export const canCall = (gameState) => {
  const callAmount = getCallAmount(gameState);
  // You can always call if there's a bet to call and you have chips
  // Even if the bet is larger than your stack (all-in call)
  return callAmount > 0 && gameState?.players[0]?.stack > 0;
};

export const canRaise = (gameState) => {
  if (!gameState || !gameState.players) return false;
  const player = gameState.players[0];
  const callAmount = getCallAmount(gameState);
  return player.stack > callAmount;
};

// Get position information for a player
export const getPlayerPosition = (gameState, playerIndex) => {
  if (!gameState || gameState.dealer_pos === undefined) return {};
  
  // In heads-up poker:
  // - Dealer (dealer_pos) is also small blind
  // - Other player is big blind
  const isDealer = playerIndex === gameState.dealer_pos;
  const isSmallBlind = playerIndex === gameState.dealer_pos;
  const isBigBlind = playerIndex === ((gameState.dealer_pos + 1) % 2);
  
  return { isDealer, isSmallBlind, isBigBlind };
};

// Check if a player has checked in the current round
export const hasPlayerChecked = (gameState, playerIndex) => {
  if (!gameState?.action_history) return false;
  
  const playerName = gameState.players[playerIndex]?.name;
  const currentRound = gameState.betting_round || 'preflop';
  
  // Look for the most recent check action by this player in the current round
  const recentActions = gameState.action_history.slice().reverse();
  for (const action of recentActions) {
    if (action.player === playerName && action.round === currentRound) {
      return action.action === 'check';
    }
  }
  return false;
};
