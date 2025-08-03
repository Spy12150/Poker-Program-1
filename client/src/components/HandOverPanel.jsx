import React from 'react';

const HandOverPanel = ({ handOver, showdown, winners, newHand, newRound, loading, gameState }) => {
  if (!handOver) return null;

  // Check if game is over (someone has 0 chips)
  const isGameOver = gameState && gameState.players && gameState.players.some(player => player.stack === 0);

  return (
    <div className="hand-over-panel">
      <h2>HAND COMPLETE!</h2>
      {winners && winners.length > 0 && (
        <div className="winners-section">
          {winners.map((winner, idx) => (
            <div key={idx} className="winner-info">
              <strong>{winner.name}</strong> wins with {winner.hand_class}
            </div>
          ))}
        </div>
      )}
      
      {isGameOver && (
        <div className="game-over-section">
          <h3>ROUND COMPLETE!</h3>
          <p>One player is out of chips. Ready for a new round?</p>
        </div>
      )}
      
      <button 
        onClick={isGameOver ? newRound : newHand} 
        disabled={loading} 
        className="start-button"
      >
        {loading ? 'Starting...' : (isGameOver ? 'Start New Round' : 'Deal Next Hand')}
      </button>
    </div>
  );
};

export default HandOverPanel;
