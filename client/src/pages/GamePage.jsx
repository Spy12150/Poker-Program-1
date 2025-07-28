import React, { useState } from 'react';

const GamePage = () => {
  const [gameState, setGameState] = useState(null);
  const [gameId, setGameId] = useState(null);
  const [message, setMessage] = useState('');
  const [winners, setWinners] = useState([]);
  const [handOver, setHandOver] = useState(false);
  const [showdown, setShowdown] = useState(false);
  const [raiseAmount, setRaiseAmount] = useState('');
  const [loading, setLoading] = useState(false);

  const startGame = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:5000/start-game', {
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
      setMessage('New game started! You are Player 1.');
      setHandOver(false);
      setShowdown(false);
      setWinners([]);
    } catch (error) {
      setMessage('Failed to start game. Make sure the server is running.');
    } finally {
      setLoading(false);
    }
  };

  const makeAction = async (action, amount = 0) => {
    if (!gameId || handOver || loading) return;
    
    setLoading(true);
    try {
      const res = await fetch('http://localhost:5000/player-action', {
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
      setMessage(data.message || `You ${action}${amount > 0 ? ` ${amount}` : ''}`);
      setRaiseAmount('');
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
      const res = await fetch('http://localhost:5000/new-hand', {
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

  // Calculate what actions are available
  const getAvailableActions = () => {
    if (!gameState || handOver || gameState.current_player !== 0) return [];
    
    const player = gameState.players[0];
    const toCall = gameState.current_bet - player.current_bet;
    const actions = [];

    actions.push('fold');
    
    if (toCall === 0) {
      actions.push('check');
    } else {
      actions.push('call');
    }
    
    if (player.stack > toCall) {
      actions.push('raise');
    }

    return actions;
  };

  const formatActionHistory = () => {
    if (!gameState?.action_history) return [];
    return gameState.action_history.slice(-5); // Show last 5 actions
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1>Heads-Up Poker</h1>
        {!gameState ? (
          <button onClick={startGame} disabled={loading} style={styles.startButton}>
            {loading ? 'Starting...' : 'Start New Game'}
          </button>
        ) : (
          <div style={styles.gameInfo}>
            <div>Pot: ${gameState.pot}</div>
            <div>Round: {gameState.betting_round}</div>
            {gameState.current_bet > 0 && <div>Current Bet: ${gameState.current_bet}</div>}
          </div>
        )}
      </div>

      {message && (
        <div style={styles.message}>
          {message}
        </div>
      )}

      {gameState && (
        <>
          {/* AI Player Section */}
          <div style={styles.playerSection}>
            <h3>🤖 {gameState.players[1]?.name} (AI)</h3>
            <div style={styles.playerInfo}>
              <span>Stack: ${gameState.players[1]?.stack}</span>
              <span>Bet: ${gameState.players[1]?.current_bet}</span>
              <span>Status: {gameState.players[1]?.status}</span>
            </div>
            <div style={styles.handContainer}>
              {/* Always show 2 card backs for AI unless showdown */}
              {(showdown ? gameState.players[1]?.hand || ['cardback', 'cardback'] : ['cardback', 'cardback']).map((card, idx) => (
                <img 
                  key={idx} 
                  src={`/cards/${showdown ? translateCard(card) : 'cardback'}.png`} 
                  alt="card"
                  style={styles.card}
                />
              ))}
            </div>
          </div>

          {/* Community Cards */}
          <div style={styles.communitySection}>
            <h3>🃏 Community Cards</h3>
            <div style={styles.handContainer}>
              {gameState.community.map((card, idx) => (
                <img 
                  key={idx} 
                  src={`/cards/${translateCard(card)}.png`} 
                  alt="community card"
                  style={styles.card}
                />
              ))}
              {/* Show placeholders for undealt cards */}
              {Array(5 - gameState.community.length).fill().map((_, idx) => (
                <div key={`placeholder-${idx}`} style={styles.cardPlaceholder}>?</div>
              ))}
            </div>
          </div>

          {/* Human Player Section */}
          <div style={styles.playerSection}>
            <h3>👤 {gameState.players[0]?.name} (You)</h3>
            <div style={styles.playerInfo}>
              <span>Stack: ${gameState.players[0]?.stack}</span>
              <span>Bet: ${gameState.players[0]?.current_bet}</span>
              <span>Status: {gameState.players[0]?.status}</span>
            </div>
            <div style={styles.handContainer}>
              {gameState.player_hand?.map((card, idx) => (
                <img 
                  key={idx} 
                  src={`/cards/${translateCard(card)}.png`} 
                  alt="your card"
                  style={styles.card}
                />
              ))}
            </div>
          </div>

          {/* Action Buttons */}
          {!handOver && gameState.current_player === 0 && (
            <div style={styles.actionSection}>
              <h3>Your Turn - Choose Action:</h3>
              <div style={styles.actionButtons}>
                {getAvailableActions().map(action => {
                  if (action === 'raise') {
                    return (
                      <div key={action} style={styles.raiseContainer}>
                        <input
                          type="number"
                          placeholder="Raise amount"
                          value={raiseAmount}
                          onChange={(e) => setRaiseAmount(e.target.value)}
                          style={styles.raiseInput}
                          min={gameState.current_bet + 1}
                        />
                        <button 
                          onClick={handleRaise} 
                          disabled={loading}
                          style={styles.actionButton}
                        >
                          Raise
                        </button>
                      </div>
                    );
                  }
                  
                  return (
                    <button
                      key={action}
                      onClick={() => makeAction(action)}
                      disabled={loading}
                      style={styles.actionButton}
                    >
                      {action.charAt(0).toUpperCase() + action.slice(1)}
                      {action === 'call' && ` $${gameState.current_bet - gameState.players[0].current_bet}`}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Hand Over Section */}
          {handOver && (
            <div style={styles.handOverSection}>
              <h2>🏆 Hand Over!</h2>
              {showdown && (
                <div style={styles.winnersSection}>
                  <h3>Showdown Results:</h3>
                  {winners.map((winner, idx) => (
                    <div key={idx} style={styles.winnerInfo}>
                      <strong>{winner.name}</strong> wins with {winner.hand_class}
                      <div>Cards: {winner.hand?.join(', ')}</div>
                    </div>
                  ))}
                </div>
              )}
              <button onClick={newHand} disabled={loading} style={styles.startButton}>
                {loading ? 'Starting...' : 'Deal Next Hand'}
              </button>
            </div>
          )}

          {/* Action History */}
          <div style={styles.historySection}>
            <h4>Recent Actions:</h4>
            <div style={styles.history}>
              {formatActionHistory().map((entry, idx) => (
                <div key={idx} style={styles.historyEntry}>
                  <strong>{entry.player}</strong> {entry.action}
                  {entry.amount && ` $${entry.amount}`} 
                  <span style={styles.round}>({entry.round})</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

// e.g. "As" → "ace_of_spades"
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

const styles = {
  container: {
    backgroundImage: 'url(/cards/background.png)',
    backgroundSize: 'cover',
    minHeight: '100vh',
    padding: '20px',
    color: 'white',
    fontFamily: 'Arial, sans-serif'
  },
  header: {
    textAlign: 'center',
    marginBottom: '20px',
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    padding: '20px',
    borderRadius: '10px'
  },
  gameInfo: {
    display: 'flex',
    justifyContent: 'center',
    gap: '30px',
    fontSize: '18px',
    fontWeight: 'bold',
    marginTop: '10px'
  },
  message: {
    textAlign: 'center',
    backgroundColor: 'rgba(0, 100, 0, 0.8)',
    padding: '15px',
    borderRadius: '8px',
    marginBottom: '20px',
    fontSize: '16px',
    fontWeight: 'bold'
  },
  playerSection: {
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    padding: '20px',
    borderRadius: '10px',
    marginBottom: '20px',
    textAlign: 'center'
  },
  playerInfo: {
    display: 'flex',
    justifyContent: 'center',
    gap: '20px',
    marginBottom: '15px',
    fontSize: '14px'
  },
  communitySection: {
    backgroundColor: 'rgba(0, 50, 0, 0.8)',
    padding: '20px',
    borderRadius: '10px',
    marginBottom: '20px',
    textAlign: 'center'
  },
  handContainer: {
    display: 'flex',
    justifyContent: 'center',
    gap: '10px',
    flexWrap: 'wrap'
  },
  card: {
    height: '100px',
    borderRadius: '8px',
    boxShadow: '0 4px 8px rgba(0,0,0,0.3)'
  },
  cardPlaceholder: {
    width: '71px',
    height: '100px',
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    border: '2px dashed rgba(255, 255, 255, 0.5)',
    borderRadius: '8px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '24px',
    color: 'rgba(255, 255, 255, 0.7)'
  },
  actionSection: {
    backgroundColor: 'rgba(100, 0, 0, 0.8)',
    padding: '20px',
    borderRadius: '10px',
    marginBottom: '20px',
    textAlign: 'center'
  },
  actionButtons: {
    display: 'flex',
    justifyContent: 'center',
    gap: '15px',
    flexWrap: 'wrap',
    marginTop: '15px'
  },
  actionButton: {
    padding: '12px 24px',
    fontSize: '16px',
    fontWeight: 'bold',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    backgroundColor: '#4CAF50',
    color: 'white',
    transition: 'all 0.3s ease',
    minWidth: '100px'
  },
  startButton: {
    padding: '15px 30px',
    fontSize: '18px',
    fontWeight: 'bold',
    border: 'none',
    borderRadius: '10px',
    cursor: 'pointer',
    backgroundColor: '#2196F3',
    color: 'white',
    transition: 'all 0.3s ease'
  },
  raiseContainer: {
    display: 'flex',
    gap: '10px',
    alignItems: 'center'
  },
  raiseInput: {
    padding: '12px',
    fontSize: '16px',
    borderRadius: '8px',
    border: '2px solid #ccc',
    width: '120px'
  },
  handOverSection: {
    backgroundColor: 'rgba(255, 215, 0, 0.9)',
    color: 'black',
    padding: '30px',
    borderRadius: '15px',
    marginBottom: '20px',
    textAlign: 'center'
  },
  winnersSection: {
    marginBottom: '20px'
  },
  winnerInfo: {
    backgroundColor: 'rgba(0, 0, 0, 0.1)',
    padding: '10px',
    borderRadius: '8px',
    marginBottom: '10px'
  },
  historySection: {
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    padding: '15px',
    borderRadius: '8px',
    maxHeight: '200px',
    overflowY: 'auto'
  },
  history: {
    marginTop: '10px'
  },
  historyEntry: {
    padding: '5px 0',
    borderBottom: '1px solid rgba(255, 255, 255, 0.2)',
    fontSize: '14px'
  },
  round: {
    color: 'rgba(255, 255, 255, 0.6)',
    fontSize: '12px',
    marginLeft: '10px'
  }
};

export default GamePage;
