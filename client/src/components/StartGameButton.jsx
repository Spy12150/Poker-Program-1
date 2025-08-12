import React, { useState } from 'react';
import { AI_OPTIONS } from './aiOptions';

const StartGameButton = ({ gameState, startGame, loading }) => {
  const [selectedAI, setSelectedAI] = useState('bladework_v2');
  const [hoveredAI, setHoveredAI] = useState(null);

  if (gameState) return null;

  // Names of all AI for start page and debug panel
  const aiOptionsList = AI_OPTIONS;

  const handleStartGame = () => {
    startGame(selectedAI);
  };

  return (
    <div className="start-game-container">
      <div className="ai-selection">
        <h3>Choose your opponent:</h3>
        <div className="ai-buttons">
          {aiOptionsList.map((aiOption) => (
            <div key={aiOption.id} className="ai-option">
              <button
                onClick={() => setSelectedAI(aiOption.id)}
                className={selectedAI === aiOption.id ? 'ai-button selected' : 'ai-button'}
                disabled={loading}
              >
                <span className="notranslate" translate="no">{aiOption.name}</span>
              </button>
              <div 
                className="info-icon"
                onMouseEnter={() => setHoveredAI(aiOption.id)}
                onMouseLeave={() => setHoveredAI(null)}
              >
                <img src="/infoicon.webp" alt="Info" className="info-icon-img" />
                {hoveredAI === aiOption.id && (
                  <div className="custom-tooltip">
                    {aiOption.description} 
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
