import React from 'react';

const StartGameButton = ({ gameState, startGame, loading }) => {
  if (gameState) return null;

  return (
    <div className="start-game-container">
      <button onClick={startGame} disabled={loading} className="start-button">
        {loading ? 'Starting...' : 'Start New Game'}
      </button>
    </div>
  );
};

export default StartGameButton;
