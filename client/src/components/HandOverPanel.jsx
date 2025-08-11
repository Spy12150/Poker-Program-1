import React from 'react';
import { AI_OPTIONS } from './aiOptions';

//Right side panel shows up when showdown or someone folds

const HandOverPanel = ({ handOver, showdown, winners, newHand, newRound, loading, gameState }) => {
  if (!handOver) return null;

  // Check if game is over (someone has 0 chips)
  const isGameOver = gameState && gameState.players && gameState.players.some(player => player.stack === 0);

  // Map engine names to branded names: AI -> aiOptions, Player 1 -> You
  const aiType = gameState?.ai_info?.type || 'bladework_v2';
  const aiNameMap = Object.fromEntries(AI_OPTIONS.map(o => [o.id, o.name]));
  const opponentDisplayName = aiNameMap[aiType] || gameState?.players?.[1]?.name || 'AI';
  const youEngineName = gameState?.players?.[0]?.name || 'Player 1';

  const resolveName = (name) => {
    if (name === (gameState?.players?.[1]?.name || 'AI')) return opponentDisplayName;
    if (name === youEngineName) return 'You';
    return name || 'Player';
  };

  return (
    <div className="hand-over-panel">
      <h2>HAND COMPLETE!</h2>
      {winners && winners.length > 0 && (
        <div className="winners-section">
          {winners.map((winner, idx) => {
            const name = resolveName(winner.name);
            const verb = name === 'You' ? 'win' : 'wins';
            const handClass = winner.hand_class || '';
            const isFoldWin = typeof handClass === 'string' && handClass.toLowerCase().includes('fold');
            const description = isFoldWin ? 'by fold' : `with ${handClass}`;
            return (
              <div key={idx} className="winner-info">
                <strong>{name}</strong> {verb} {description}
              </div>
            );
          })}
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
