import React, { useState } from 'react';

const StartGameButton = ({ gameState, startGame, loading }) => {
  const [selectedAI, setSelectedAI] = useState('bladework_v2');
  const [hoveredAI, setHoveredAI] = useState(null);

  if (gameState) return null;

  const aiOptions = [
    {
      id: 'froggie',
      name: 'Froggie',
      description: 'A bot that performs random actions at every hand'
    },
    {
      id: 'bladework_v2',
      name: 'Bladework',
      description: 'A hard-coded bot with defined ranges that can beat intermediate heads up players'
    }
  ];

  const handleStartGame = () => {
    startGame(selectedAI);
  };

  return (
    <div className="start-game-container">
      <div className="ai-selection">
        <h3>Choose your opponent:</h3>
        <div className="ai-buttons">
          {aiOptions.map((ai) => (
            <div key={ai.id} className="ai-option">
              <button
                onClick={() => setSelectedAI(ai.id)}
                className={`ai-button ${selectedAI === ai.id ? 'selected' : ''}`}
                disabled={loading}
              >
                {ai.name}
              </button>
              <div 
                className="info-icon"
                onMouseEnter={() => setHoveredAI(ai.id)}
                onMouseLeave={() => setHoveredAI(null)}
              >
                <img src="/infoicon.webp" alt="Info" className="info-icon-img" />
                {hoveredAI === ai.id && (
                  <div className="custom-tooltip">
                    {ai.description}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
      <button 
        onClick={handleStartGame} 
        disabled={loading} 
        className="start-button"
      >
        {loading ? 'Starting...' : 'Start New Game'}
      </button>
    </div>
  );
};

export default StartGameButton;
