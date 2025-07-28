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

  // Function definitions (moved above useEffect to avoid reference errors)
  const getCallAmount = () => {
    if (!gameState || !gameState.players) return 0;
    const player = gameState.players[0];
    const currentBet = gameState.current_bet || 0;
    const playerCurrentBet = player.current_bet || 0;
    return Math.max(0, currentBet - playerCurrentBet);
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
    const toCall = currentBet - playerCurrentBet;
    
    // Minimum raise: current bet + big blind (or 2x current bet if bigger)
    const bigBlind = 20; // From config
    let minRaise;
    
    if (currentBet === 0) {
      // First bet of the round
      minRaise = bigBlind;
    } else {
      // Must raise by at least the size of the last raise, or big blind minimum
      minRaise = Math.max(currentBet * 2, currentBet + bigBlind);
    }
    
    // Maximum bet: all-in
    const maxBetAmount = player.stack + playerCurrentBet;
    
    // Ensure min bet doesn't exceed max bet
    const finalMinBet = Math.min(minRaise, maxBetAmount);
    
    setMinBet(finalMinBet);
    setMaxBet(maxBetAmount);
    setBetSliderValue(Math.max(finalMinBet, betSliderValue));
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

  // Update betting limits when game state changes
  useEffect(() => {
    if (gameState) {
      updateBetLimits(gameState);
    }
  }, [gameState]);

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

      // Show AI action message for 2 seconds
      if (data.message) {
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
    return gameState.action_history.slice(-5); // Show last 5 actions
  };

  return (
    <div className="game-container">
      {/* Site Title */}
      <div className="site-title">
        Riposte
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
                    
                    {/* AI Thinking Indicator */}
                    {!handOver && gameState.current_player === 1 && (
                      <div className="turn-indicator ai-thinking">
                        AI is thinking...
                      </div>
                    )}
                  </div>
                  
                  {/* AI Current Bet */}
                  {gameState.players[1]?.current_bet > 0 && (
                    <div className="current-bet-container ai-bet">
                      ${gameState.players[1]?.current_bet}
                    </div>
                  )}
                </div>

                {/* Community Cards & Pot */}
                <div className="community-area">
                  <div className="pot-info">
                    POT: ${gameState.pot}
                  </div>
                  <div className="community-cards">
                    {gameState.community.map((card, idx) => (
                      <img 
                        key={idx} 
                        src={`/cards/${translateCard(card)}.png`} 
                        alt="community card"
                        className="community-card"
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
                  {gameState.players[0]?.current_bet > 0 && (
                    <div className="current-bet-container player-bet">
                      ${gameState.players[0]?.current_bet}
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
                    
                    {/* Your Turn Indicator */}
                    {!handOver && gameState.current_player === 0 && (
                      <div className="turn-indicator your-turn">
                        Your turn
                      </div>
                    )}
                  </div>
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
                  {canCheck() ? 'CHECK' : `CALL ${getCallAmount() > 0 ? getCallAmount() + ' BB' : ''}`}
                </button>
                
                <button
                  onClick={() => makeAction('raise', betSliderValue)}
                  disabled={loading || !canRaise() || betSliderValue < minBet}
                  className="modern-action-button raise-button"
                >
                  RAISE TO<br/>{Math.round(betSliderValue / 20)} BB
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
                  }}
                  disabled={betSliderValue <= minBet}
                >
                  −
                </button>
                
                <button 
                  className="bet-adjust-button bars"
                  onClick={() => setBetSliderValue(gameState.pot || 40)}
                >
                  |||
                </button>

                {/* Bet Slider */}
                <div className="slider-container">
                  <input
                    type="range"
                    min={minBet}
                    max={maxBet}
                    value={betSliderValue}
                    onChange={(e) => setBetSliderValue(Number(e.target.value))}
                    className="bet-slider"
                  />
                </div>

                <button 
                  className="bet-adjust-button increase"
                  onClick={() => {
                    const newValue = Math.min(maxBet, betSliderValue + 20);
                    setBetSliderValue(newValue);
                  }}
                  disabled={betSliderValue >= maxBet}
                >
                  +
                </button>

                {/* Bet Amount Display */}
                <div className="bet-amount-display">
                  {Math.round(betSliderValue / 20 * 10) / 10}
                </div>
              </div>

              {/* Quick Bet Buttons */}
              <div className="quick-bet-row">
                <button 
                  className="quick-bet-button"
                  onClick={() => setBetSliderValue(Math.round(gameState.pot * 0.5))}
                >
                  Pot
                </button>
                
                <button 
                  className="quick-bet-button"
                  onClick={() => setBetSliderValue(maxBet)}
                >
                  ALL-IN
                </button>
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
                      <div>Cards: {winner.hand?.join(', ')}</div>
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
                  <strong>{entry.player}</strong> {entry.action}
                  {entry.amount && ` $${entry.amount}`} 
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
