import React, { useState, useEffect } from 'react';
import './GamePage.css';

const GamePage = () => {
  const [gameState, setGameState] = useState(null);
  const [gameId, setGameId] = useState(null);
  const [message, setMessage] = useState('');
  const [winners, setWinners] = useState([]);
  const [handOver, setHandOver] = useState(false);
  const [showdown, setShowdown] = useState(false);
  const [raiseAmount, setRaiseAmount] = useState('');
  const [loading, setLoading] = useState(false);
  const [betSliderValue, setBetSliderValue] = useState(0);
  const [minBet, setMinBet] = useState(0);
  const [maxBet, setMaxBet] = useState(0);
  const [dealingCards, setDealingCards] = useState(false);
  const [previousCommunityLength, setPreviousCommunityLength] = useState(0);
  const [newCardIndices, setNewCardIndices] = useState([]);

  // Function definitions (moved above useEffect to avoid reference errors)
  const getCallAmount = () => {
    if (!gameState || !gameState.players) return 0;
    const player = gameState.players[0];
    const currentBet = gameState.current_bet || 0;
    const playerCurrentBet = player.current_bet || 0;
    return Math.max(0, currentBet - playerCurrentBet);
  };

  // Logarithmic slider conversion functions
  const betToSliderPosition = (betValue, minBet, maxBet) => {
    if (minBet >= maxBet || betValue <= minBet) return 0;
    if (betValue >= maxBet) return 100;
    
    // Logarithmic scale: log(betValue/minBet) / log(maxBet/minBet)
    const logRatio = Math.log(betValue / minBet) / Math.log(maxBet / minBet);
    return Math.round(logRatio * 100);
  };

  const sliderPositionToBet = (position, minBet, maxBet) => {
    if (position <= 0) return minBet;
    if (position >= 100) return maxBet;
    
    // Convert logarithmic position back to bet value
    const ratio = position / 100;
    const betValue = minBet * Math.pow(maxBet / minBet, ratio);
    return Math.round(betValue);
  };

  const canCheck = () => {
    return getCallAmount() === 0;
  };

  const canCall = () => {
    const callAmount = getCallAmount();
    return callAmount > 0 && gameState?.players[0]?.stack >= callAmount;
  };

  const canRaise = () => {
    if (!gameState || !gameState.players) return false;
    const player = gameState.players[0];
    const callAmount = getCallAmount();
    return player.stack > callAmount;
  };

  const updateBetLimits = (state) => {
    if (!state || !state.players || state.current_player !== 0) return;
    
    const player = state.players[0];
    const currentBet = state.current_bet || 0;
    const playerCurrentBet = player.current_bet || 0;
    const lastBetAmount = state.last_bet_amount || 0;
    
    // Minimum raise calculation (matches backend logic)
    const bigBlind = 20; // From config
    let minRaise;
    
    if (currentBet === 0) {
      // First bet of the round - minimum is big blind
      minRaise = bigBlind;
    } else {
      // Must raise by at least the size of the last bet/raise
      minRaise = currentBet + Math.max(lastBetAmount, bigBlind);
    }
    
    // Maximum bet: all-in
    const maxBetAmount = player.stack + playerCurrentBet;
    
    // Ensure min bet doesn't exceed max bet
    const finalMinBet = Math.min(minRaise, maxBetAmount);
    
    setMinBet(finalMinBet);
    setMaxBet(maxBetAmount);
    // Always default to minimum bet for new actions
    setBetSliderValue(finalMinBet);
    setRaiseAmount(finalMinBet.toString());
  };

  const handleSliderRaise = () => {
    if (betSliderValue < minBet) {
      setMessage(`Minimum bet is $${minBet}`);
      return;
    }
    if (betSliderValue > maxBet) {
      setMessage(`Maximum bet is $${maxBet}`);
      return;
    }
    makeAction('raise', betSliderValue);
  };

  // Get position information for a player
  const getPlayerPosition = (playerIndex) => {
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
  const hasPlayerChecked = (playerIndex) => {
    if (!gameState?.action_history) return false;
    
    const playerName = gameState.players[playerIndex]?.name;
    const currentRound = gameState.round || 'preflop';
    
    // Look for the most recent check action by this player in the current round
    const recentActions = gameState.action_history.slice().reverse();
    for (const action of recentActions) {
      if (action.player === playerName && action.round === currentRound) {
        return action.action === 'check';
      }
    }
    return false;
  };

  // Update betting limits when game state changes
  useEffect(() => {
    if (gameState) {
      updateBetLimits(gameState);
    }
  }, [gameState]);

  // Handle card dealing animation
  useEffect(() => {
    if (gameState && gameState.community) {
      const currentCommunityLength = gameState.community.length;
      if (currentCommunityLength > previousCommunityLength) {
        setDealingCards(true);
        
        // Determine which cards are new
        const newIndices = [];
        for (let i = previousCommunityLength; i < currentCommunityLength; i++) {
          newIndices.push(i);
        }
        
        // Special case for flop: if we're going from 0 to 3 cards, animate all 3
        if (previousCommunityLength === 0 && currentCommunityLength === 3) {
          setNewCardIndices([0, 1, 2]);
        } else {
          setNewCardIndices(newIndices);
        }
        
        // Check if it's an all-in showdown with multiple cards dealt at once
        const cardsDifference = currentCommunityLength - previousCommunityLength;
        const animationDuration = cardsDifference > 1 ? 1500 : 1000; // Longer for multiple cards
        
        setTimeout(() => {
          setDealingCards(false);
          setNewCardIndices([]);
        }, animationDuration);
      }
      setPreviousCommunityLength(currentCommunityLength);
    }
  }, [gameState?.community?.length, previousCommunityLength]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (event) => {
      if (!gameState || handOver || gameState.current_player !== 0 || loading) return;

      switch (event.key.toLowerCase()) {
        case 'f':
          if (event.ctrlKey || event.metaKey) return; // Don't interfere with browser shortcuts
          makeAction('fold');
          break;
        case 'c':
          if (event.ctrlKey || event.metaKey) return;
          if (canCheck()) {
            makeAction('check');
          } else if (canCall()) {
            makeAction('call');
          }
          break;
        case 'r':
          if (event.ctrlKey || event.metaKey) return;
          if (canRaise()) {
            handleSliderRaise();
          }
          break;
        default:
          break;
      }
    };

    document.addEventListener('keypress', handleKeyPress);
    return () => document.removeEventListener('keypress', handleKeyPress);
  }, [gameState, handOver, loading]);

  const startGame = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:5001/start-game', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await res.json();

      if (data.error) {
        setMessage(`Error: ${data.error}`);
        return;
      }

      setGameId(data.game_id);
      setGameState(data);
      setHandOver(false);
      setShowdown(false);
      setWinners([]);
      updateBetLimits(data);
      
      // Check if AI needs to act first
      if (data.current_player === 1 && !data.hand_over) {
        setTimeout(() => {
          processAITurn();
        }, 1000); // Give a moment for UI to update, then process AI turn
      }
    } catch (error) {
      setMessage('Failed to start game. Make sure the server is running.');
    } finally {
      setLoading(false);
    }
  };

  const processAITurn = async () => {
    if (!gameId) return;
    
    try {
      const res = await fetch('http://localhost:5001/process-ai-turn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_id: gameId })
      });
      const data = await res.json();

      if (data.game_state) {
        setGameState(data.game_state);
        updateBetLimits(data.game_state);
      }

      if (data.hand_over) {
        setHandOver(true);
        setWinners(data.winners || []);
        setShowdown(data.showdown || false);
      }

      // Handle all-in showdown
      if (data.all_in_showdown) {
        setShowdown(true);
        setWinners(data.winners || []);
        if (data.message) {
          setMessage(data.message);
        }
      }

      // Show AI action message for 2 seconds
      if (data.message && !data.all_in_showdown) {
        setMessage(data.message);
        setTimeout(() => {
          setMessage('');
        }, 2000);
      }
    } catch (error) {
      console.error('Failed to process AI turn:', error);
    }
  };

  const makeAction = async (action, amount = 0) => {
    if (!gameId || handOver || loading) return;
    
    setLoading(true);
    try {
      const res = await fetch('http://localhost:5001/player-action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: gameId,
          action: action,
          amount: amount
        })
      });
      const data = await res.json();

      if (data.error) {
        setMessage(`Error: ${data.error}`);
        return;
      }

      setGameState(data.game_state);
      setHandOver(data.hand_over || false);
      setShowdown(data.showdown || false);
      setWinners(data.winners || []);
      setMessage(data.message || `You ${action}${amount > 0 ? ` $${amount}` : ''}`);
      setRaiseAmount('');
      updateBetLimits(data.game_state);

      // Handle all-in showdown
      if (data.all_in_showdown) {
        setShowdown(true);
        setWinners(data.winners || []);
        if (data.message) {
          setMessage(data.message);
        }
        return; // Don't process AI turn if showdown occurred
      }

      // Clear player action message after 1 second, then check for AI turn
      setTimeout(() => {
        setMessage('');
        // If it's now AI's turn and game isn't over, process AI turn after a brief delay
        if (data.game_state && data.game_state.current_player === 1 && !data.hand_over) {
          setTimeout(() => {
            processAITurn();
          }, 500); // Short delay before AI acts
        }
      }, 1000);

    } catch (error) {
      setMessage('Failed to make action. Check your connection.');
    } finally {
      setLoading(false);
    }
  };

  const newHand = async () => {
    if (!gameId || loading) return;
    
    setLoading(true);
    try {
      const res = await fetch('http://localhost:5001/new-hand', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_id: gameId })
      });
      const data = await res.json();

      if (data.error) {
        setMessage(`Error: ${data.error}`);
        return;
      }

      setGameState(data);
      setHandOver(false);
      setShowdown(false);
      setWinners([]);
      setMessage('New hand started!');
      updateBetLimits(data);
      
      // Check if AI needs to act first in the new hand
      if (data.current_player === 1 && !data.hand_over) {
        setTimeout(() => {
          processAITurn();
        }, 1000); // Give a moment for UI to update, then process AI turn
      }
    } catch (error) {
      setMessage('Failed to start new hand.');
    } finally {
      setLoading(false);
    }
  };

  const handleRaise = () => {
    const amount = parseInt(raiseAmount);
    if (isNaN(amount) || amount <= 0) {
      setMessage('Please enter a valid raise amount');
      return;
    }
    makeAction('raise', amount);
  };

  // Calculate what actions are available - removed, now using individual can* functions

  const formatActionHistory = () => {
    if (!gameState?.action_history) return [];
    return gameState.action_history.slice(-10); // Show last 10 actions
  };

  // Hand evaluation function
  const evaluateHand = (playerHand, communityCards) => {
    if (!playerHand || playerHand.length < 2) {
      return "No hand";
    }

    // Combine player hand and community cards
    const allCards = [...playerHand, ...(communityCards || [])];
    
    // If we have less than 5 cards, just evaluate what we have
    if (allCards.length < 5) {
      return evaluatePartialHand(allCards);
    }

    // Convert cards to a format we can work with
    const cards = allCards.map(card => {
      const rank = card[0];
      const suit = card[1];
      return { rank, suit };
    });

    // Count ranks and suits
    const rankCounts = {};
    const suitCounts = {};
    const ranks = [];

    cards.forEach(card => {
      rankCounts[card.rank] = (rankCounts[card.rank] || 0) + 1;
      suitCounts[card.suit] = (suitCounts[card.suit] || 0) + 1;
      ranks.push(card.rank);
    });

    // Convert ranks to numbers for comparison
    const rankValues = {
      '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
    };

    const rankNames = {
      '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9', 'T': '10', 'J': 'Jack', 'Q': 'Queen', 'K': 'King', 'A': 'Ace'
    };

    // Sort ranks by frequency and value
    const sortedRanks = Object.keys(rankCounts).sort((a, b) => {
      if (rankCounts[b] !== rankCounts[a]) {
        return rankCounts[b] - rankCounts[a];
      }
      return rankValues[b] - rankValues[a];
    });

    // Check for flush
    const isFlush = Object.values(suitCounts).some(count => count >= 5);
    
    // Check for straight
    const uniqueRanks = [...new Set(ranks)].map(r => rankValues[r]).sort((a, b) => b - a);
    let isStraight = false;
    let straightHigh = 0;
    
    // Check for regular straight
    for (let i = 0; i <= uniqueRanks.length - 5; i++) {
      if (uniqueRanks[i] - uniqueRanks[i + 4] === 4) {
        isStraight = true;
        straightHigh = uniqueRanks[i];
        break;
      }
    }
    
    // Check for A-2-3-4-5 straight (wheel)
    if (!isStraight && uniqueRanks.includes(14) && uniqueRanks.includes(2) && uniqueRanks.includes(3) && uniqueRanks.includes(4) && uniqueRanks.includes(5)) {
      isStraight = true;
      straightHigh = 5;
    }

    // Determine hand type
    const pairs = sortedRanks.filter(rank => rankCounts[rank] === 2);
    const trips = sortedRanks.filter(rank => rankCounts[rank] === 3);
    const quads = sortedRanks.filter(rank => rankCounts[rank] === 4);

    if (isStraight && isFlush) {
      if (straightHigh === 14) {
        return "Royal Flush";
      } else {
        const highCard = Object.keys(rankValues).find(k => rankValues[k] === straightHigh);
        return `Straight Flush, ${rankNames[highCard]}-high`;
      }
    } else if (quads.length > 0) {
      return `Four of a Kind, ${rankNames[quads[0]]}s`;
    } else if (trips.length > 0 && pairs.length > 0) {
      return `Full House, ${rankNames[trips[0]]}s full of ${rankNames[pairs[0]]}s`;
    } else if (isFlush) {
      const highCard = sortedRanks[0];
      return `Flush, ${rankNames[highCard]}-high`;
    } else if (isStraight) {
      const highCard = Object.keys(rankValues).find(k => rankValues[k] === straightHigh);
      return `Straight, ${rankNames[highCard]}-high`;
    } else if (trips.length > 0) {
      return `Three of a Kind, ${rankNames[trips[0]]}s`;
    } else if (pairs.length >= 2) {
      return `Two Pair, ${rankNames[pairs[0]]}s and ${rankNames[pairs[1]]}s`;
    } else if (pairs.length === 1) {
      return `Pair, ${rankNames[pairs[0]]}s`;
    } else {
      const highCard = sortedRanks[0];
      return `High Card, ${rankNames[highCard]}`;
    }
  };

  // Helper function for hands with fewer than 5 cards
  const evaluatePartialHand = (cards) => {
    if (cards.length === 0) return "No hand";
    
    const rankCounts = {};
    const ranks = [];
    
    cards.forEach(card => {
      const rank = card[0];
      rankCounts[rank] = (rankCounts[rank] || 0) + 1;
      ranks.push(rank);
    });

    const rankValues = {
      '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
    };

    const rankNames = {
      '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9', 'T': '10', 'J': 'Jack', 'Q': 'Queen', 'K': 'King', 'A': 'Ace'
    };

    // Sort ranks by frequency and value
    const sortedRanks = Object.keys(rankCounts).sort((a, b) => {
      if (rankCounts[b] !== rankCounts[a]) {
        return rankCounts[b] - rankCounts[a];
      }
      return rankValues[b] - rankValues[a];
    });

    const pairs = sortedRanks.filter(rank => rankCounts[rank] === 2);
    
    if (pairs.length >= 1) {
      return `Pair, ${rankNames[pairs[0]]}s`;
    } else {
      const highCard = sortedRanks[0];
      return `High Card, ${rankNames[highCard]}`;
    }
  };

  return (
    <div className="game-container">
      {/* Site Title */}
      <div className="site-title">
        <div className="main-title">RIPOSTE</div>
        <div className="subtitle">POKER AI</div>
      </div>

      {/* Start Game Button - only show when no game */}
      {!gameState && (
        <div className="start-game-container">
          <button onClick={startGame} disabled={loading} className="start-button">
            {loading ? 'Starting...' : 'Start New Game'}
          </button>
        </div>
      )}

      {/* Message */}
      {message && (
        <div className="message">
          {message}
        </div>
      )}

      {gameState && (
        <>
          {/* Main Poker Table */}
          <div className="table-container">
            <div className="poker-table">
              <div className="table-inner">
                
                {/* AI Player (Opponent) */}
                <div className="opponent-area">
                  <div className="player-card">
                    <div className="player-name">{gameState.players[1]?.name} (AI)</div>
                    <div className="player-stats">
                      <span>Stack: ${gameState.players[1]?.stack}</span>
                    </div>
                    <div className="hand-container">
                      {(showdown ? gameState.players[1]?.hand || ['cardback', 'cardback'] : ['cardback', 'cardback']).map((card, idx) => (
                        <img 
                          key={idx} 
                          src={`/cards/${showdown ? translateCard(card) : 'cardback'}.png`} 
                          alt="card"
                          className="card"
                        />
                      ))}
                    </div>
                    
                    {/* Position Indicators */}
                    <div className="position-indicators">
                      {(() => {
                        const position = getPlayerPosition(1);
                        return (
                          <>
                            {position.isDealer && (
                              <div className="position-indicator dealer-button">D</div>
                            )}
                            {position.isSmallBlind && (
                              <div className="position-indicator small-blind">SB</div>
                            )}
                            {position.isBigBlind && (
                              <div className="position-indicator big-blind">BB</div>
                            )}
                          </>
                        );
                      })()}
                    </div>
                    
                    {/* AI Thinking Indicator */}
                    {!handOver && gameState.current_player === 1 && (
                      <div className="turn-indicator ai-thinking">
                        AI is thinking...
                      </div>
                    )}
                  </div>
                  
                  {/* AI Current Bet */}
                  {(gameState.players[1]?.current_bet > 0 || hasPlayerChecked(1)) && (
                    <div className="current-bet-container ai-bet">
                      {gameState.players[1]?.current_bet > 0 ? 
                        `$${gameState.players[1]?.current_bet}` : 
                        'CHECK'
                      }
                    </div>
                  )}
                </div>

                {/* Community Cards & Pot */}
                <div className="community-area">
                  <div className="pot-info">
                    POT: ${gameState.pot}
                  </div>
                  <div className={`community-cards ${dealingCards ? 'dealing-animation' : ''}`}>
                    {gameState.community.map((card, idx) => (
                      <img 
                        key={idx} 
                        src={`/cards/${translateCard(card)}.png`} 
                        alt="community card"
                        className={`community-card ${dealingCards && newCardIndices.includes(idx) ? 'new-card' : ''}`}
                      />
                    ))}
                    {/* Show placeholders for undealt cards */}
                    {Array(5 - gameState.community.length).fill().map((_, idx) => (
                      <div key={`placeholder-${idx}`} className="card-placeholder">?</div>
                    ))}
                  </div>
                </div>

                {/* Human Player */}
                <div className="player-area">
                  {/* Player Current Bet */}
                  {(gameState.players[0]?.current_bet > 0 || hasPlayerChecked(0)) && (
                    <div className="current-bet-container player-bet">
                      {gameState.players[0]?.current_bet > 0 ? 
                        `$${gameState.players[0]?.current_bet}` : 
                        'CHECK'
                      }
                    </div>
                  )}
                  
                  <div className="player-card">
                    <div className="player-name">{gameState.players[0]?.name} (You)</div>
                    <div className="player-stats">
                      <span>Stack: ${gameState.players[0]?.stack}</span>
                    </div>
                    <div className="hand-container">
                      {gameState.player_hand?.map((card, idx) => (
                        <img 
                          key={idx} 
                          src={`/cards/${translateCard(card)}.png`} 
                          alt="your card"
                          className="card"
                        />
                      ))}
                    </div>
                    
                    {/* Position Indicators */}
                    <div className="position-indicators">
                      {(() => {
                        const position = getPlayerPosition(0);
                        return (
                          <>
                            {position.isDealer && (
                              <div className="position-indicator dealer-button">D</div>
                            )}
                            {position.isSmallBlind && (
                              <div className="position-indicator small-blind">SB</div>
                            )}
                            {position.isBigBlind && (
                              <div className="position-indicator big-blind">BB</div>
                            )}
                          </>
                        );
                      })()}
                    </div>
                    
                    {/* Your Turn Indicator */}
                    {!handOver && gameState.current_player === 0 && (
                      <div className="turn-indicator your-turn">
                        Your turn
                      </div>
                    )}
                  </div>

                  {/* Hand Evaluation Display */}
                  {gameState.player_hand && (
                    <div className="hand-evaluation">
                      {evaluateHand(gameState.player_hand, gameState.community || [])}
                    </div>
                  )}
                </div>

              </div>
            </div>
          </div>

          {/* New Action Panel - Modern Poker UI */}
          {!handOver && gameState.current_player === 0 && (
            <div className="modern-action-panel">
              {/* Main Action Buttons Row */}
              <div className="main-actions-row">
                <button
                  onClick={() => makeAction('fold')}
                  disabled={loading}
                  className="modern-action-button fold-button"
                >
                  FOLD
                </button>
                
                <button
                  onClick={() => makeAction(canCheck() ? 'check' : 'call')}
                  disabled={loading || (!canCheck() && !canCall())}
                  className="modern-action-button call-button"
                >
                  {canCheck() ? 'CHECK' : `CALL ${getCallAmount() > 0 ? '$' + getCallAmount() : ''}`}
                </button>
                
                <button
                  onClick={() => makeAction('raise', betSliderValue)}
                  disabled={loading || !canRaise() || betSliderValue === '' || betSliderValue < minBet || betSliderValue > maxBet}
                  className="modern-action-button raise-button"
                >
                  RAISE TO<br/>${betSliderValue || 0}
                </button>
              </div>

              {/* Betting Controls Row */}
              <div className="betting-controls-row">
                {/* Decrease/Increase Buttons */}
                <button 
                  className="bet-adjust-button decrease"
                  onClick={() => {
                    const newValue = Math.max(minBet, betSliderValue - 20);
                    setBetSliderValue(newValue);
                    setRaiseAmount(newValue.toString());
                  }}
                  disabled={betSliderValue <= minBet}
                >
                  −
                </button>
                
                <button 
                  className="bet-adjust-button bars"
                  onClick={() => {
                    const callAmount = getCallAmount();
                    const currentPot = gameState.pot;
                    const opponentCurrentBet = gameState.players[1].current_bet || 0;
                    const potBet = currentPot + callAmount + opponentCurrentBet;
                    const finalBet = Math.min(maxBet, Math.max(minBet, potBet));
                    setBetSliderValue(finalBet);
                    setRaiseAmount(finalBet.toString());
                  }}
                >
                  |||
                </button>

                {/* Bet Slider */}
                <div className="slider-container">
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={betToSliderPosition(betSliderValue, minBet, maxBet)}
                    onChange={(e) => {
                      const sliderPosition = Number(e.target.value);
                      const betValue = sliderPositionToBet(sliderPosition, minBet, maxBet);
                      setBetSliderValue(betValue);
                      setRaiseAmount(betValue.toString());
                    }}
                    className="bet-slider"
                  />
                </div>

                <button 
                  className="bet-adjust-button increase"
                  onClick={() => {
                    const newValue = Math.min(maxBet, betSliderValue + 20);
                    setBetSliderValue(newValue);
                    setRaiseAmount(newValue.toString());
                  }}
                  disabled={betSliderValue >= maxBet}
                >
                  +
                </button>

                {/* Bet Amount Display as Input */}
                <input
                  type="number"
                  value={betSliderValue}
                  onChange={(e) => {
                    const inputValue = e.target.value;
                    // Allow empty string or any valid number input
                    if (inputValue === '') {
                      setBetSliderValue('');
                      setRaiseAmount('');
                    } else {
                      const numValue = Number(inputValue);
                      setBetSliderValue(numValue);
                      setRaiseAmount(inputValue);
                    }
                  }}
                  onBlur={(e) => {
                    const inputValue = e.target.value;
                    // If empty on blur, don't set to 0, keep it empty
                    if (inputValue === '') {
                      setBetSliderValue('');
                      setRaiseAmount('');
                    } else {
                      const numValue = Number(inputValue) || 0;
                      setBetSliderValue(numValue);
                      setRaiseAmount(numValue.toString());
                    }
                  }}
                  className="bet-amount-input"
                />
              </div>

              {/* Quick Bet Buttons - Conditional based on betting round */}
              <div className="quick-bet-row">
                {gameState.betting_round === 'preflop' ? (
                  // Preflop buttons: 2.5x (50), 3x (60), Pot, All-in
                  <>
                    {minBet <= 50 && (
                      <button 
                        className="quick-bet-button bet-2-5x"
                        onClick={() => {
                          setBetSliderValue(50);
                          setRaiseAmount('50');
                        }}
                      >
                        2.5x
                      </button>
                    )}
                    {minBet <= 60 && (
                      <button 
                        className="quick-bet-button bet-3x"
                        onClick={() => {
                          setBetSliderValue(60);
                          setRaiseAmount('60');
                        }}
                      >
                        3x
                      </button>
                    )}
                    {(() => {
                      const callAmount = getCallAmount();
                      const currentPot = gameState.pot;
                      const opponentCurrentBet = gameState.players[1].current_bet || 0;
                      const potBet = currentPot + callAmount + opponentCurrentBet;
                      
                      // Only show Pot button if calculated bet is greater than minimum bet
                      return potBet > minBet ? (
                        <button 
                          className="quick-bet-button bet-pot"
                          onClick={() => {
                            const finalBet = Math.min(maxBet, Math.max(minBet, potBet));
                            setBetSliderValue(finalBet);
                            setRaiseAmount(finalBet.toString());
                          }}
                        >
                          Pot
                        </button>
                      ) : null;
                    })()}
                    <button 
                      className="quick-bet-button bet-allin"
                      onClick={() => {
                        setBetSliderValue(maxBet);
                        setRaiseAmount(maxBet.toString());
                      }}
                    >
                      ALL-IN
                    </button>
                  </>
                ) : (
                  // Post-flop buttons: 1/3, 1/2, Pot, All-in
                  <>
                    {(() => {
                      const callAmount = getCallAmount();
                      const currentPot = gameState.pot;
                      const opponentCurrentBet = gameState.players[1].current_bet || 0;
                      const totalPot = currentPot + opponentCurrentBet;
                      const oneThirdPot = Math.ceil(totalPot / 3) + callAmount;
                      
                      // Only show 1/3 button if calculated bet is greater than minimum bet
                      return oneThirdPot > minBet ? (
                        <button 
                          className="quick-bet-button bet-third"
                          onClick={() => {
                            const finalBet = Math.min(maxBet, Math.max(minBet, oneThirdPot));

                            setBetSliderValue(finalBet);
                            setRaiseAmount(finalBet.toString());
                          }}
                        >
                          1/3 Pot
                        </button>
                      ) : null;
                    })()}
                    
                    {(() => {
                      const callAmount = getCallAmount();
                      const currentPot = gameState.pot;
                      const opponentCurrentBet = gameState.players[1].current_bet || 0;
                      const totalPot = currentPot + opponentCurrentBet;
                      const halfPot = Math.ceil(totalPot / 2) + callAmount;
                      
                      // Only show 1/2 button if calculated bet is greater than minimum bet
                      return halfPot > minBet ? (
                        <button 
                          className="quick-bet-button bet-half"
                          onClick={() => {
                            const finalBet = Math.min(maxBet, Math.max(minBet, halfPot));
                            setBetSliderValue(finalBet);
                            setRaiseAmount(finalBet.toString());
                          }}
                        >
                          1/2 Pot
                        </button>
                      ) : null;
                    })()}
                    
                    {(() => {
                      const callAmount = getCallAmount();
                      const currentPot = gameState.pot;
                      const opponentCurrentBet = gameState.players[1].current_bet || 0;
                      const potBet = currentPot + callAmount + opponentCurrentBet;
                      
                      // Only show Pot button if calculated bet is greater than minimum bet
                      return potBet > minBet ? (
                        <button 
                          className="quick-bet-button bet-pot"
                          onClick={() => {
                            const finalBet = Math.min(maxBet, Math.max(minBet, potBet));
                            setBetSliderValue(finalBet);
                            setRaiseAmount(finalBet.toString());
                          }}
                        >
                          Pot
                        </button>
                      ) : null;
                    })()}
                    
                    <button 
                      className="quick-bet-button bet-allin"
                      onClick={() => {
                        setBetSliderValue(maxBet);
                        setRaiseAmount(maxBet.toString());
                      }}
                    >
                      ALL-IN
                    </button>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Debug Info - remove this after testing */}
          {gameState && !handOver && (
            <div style={{position: 'fixed', bottom: '10px', left: '10px', background: 'white', padding: '10px', fontSize: '12px', zIndex: 1000}}>
              <div>Current Player: {gameState.current_player} (0=You, 1=AI)</div>
              <div>Your Status: {gameState.players[0]?.status}</div>
              <div>AI Status: {gameState.players[1]?.status}</div>
              <div>Hand Over: {handOver ? 'Yes' : 'No'}</div>
              <div>Can Check: {canCheck() ? 'Yes' : 'No'}</div>
              <div>Can Call: {canCall() ? 'Yes' : 'No'}</div>
              <div>Can Raise: {canRaise() ? 'Yes' : 'No'}</div>
              <div>Action Panel Should Show: {(!handOver && gameState.current_player === 0) ? 'YES' : 'NO'}</div>
              {gameState.current_player === 1 && (
                <button 
                  onClick={processAITurn}
                  style={{marginTop: '5px', padding: '5px 10px', background: '#4CAF50', color: 'white', border: 'none', borderRadius: '3px'}}
                >
                  Force AI Turn
                </button>
              )}
            </div>
          )}

          {/* Hand Over Panel */}
          {handOver && (
            <div className="hand-over-panel">
              <h2>HAND COMPLETE!</h2>
              {showdown && (
                <div className="winners-section">
                  <h3>SHOWDOWN RESULTS:</h3>
                  {winners.map((winner, idx) => (
                    <div key={idx} className="winner-info">
                      <strong>{winner.name}</strong> wins with {winner.hand_class}
                    </div>
                  ))}
                </div>
              )}
              <button onClick={newHand} disabled={loading} className="start-button">
                {loading ? 'Dealing...' : 'Deal Next Hand'}
              </button>
            </div>
          )}

          {/* Side Panel - Action History */}
          <div className="side-panel">
            <div className="history-title">ACTION HISTORY</div>
            <div>
              {formatActionHistory().map((entry, idx) => (
                <div key={idx} className="history-entry">
                  <strong>{entry.player}</strong> {entry.action.charAt(0).toUpperCase() + entry.action.slice(1)}
                  {entry.action === 'raise' && entry.amount && entry.amount > 0 && ` $${entry.amount}`} 
                  <span className="round">({entry.round})</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

const translateCard = (shortCode) => {
  const rankMap = {
    '2': '2', '3': '3', '4': '4', '5': '5', '6': '6',
    '7': '7', '8': '8', '9': '9', 'T': '10', 'J': 'jack',
    'Q': 'queen', 'K': 'king', 'A': 'ace'
  };
  const suitMap = {
    's': 'spades',
    'h': 'hearts',
    'd': 'diamonds',
    'c': 'clubs'
  };

  const rank = rankMap[shortCode[0]];
  const suit = suitMap[shortCode[1]];
  return `${rank}_of_${suit}`;
};

export default GamePage;
