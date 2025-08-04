import React from 'react';

const DebugPanel = ({ gameState, handOver, canCheck, canCall, canRaise, processAITurn, selectedAIType }) => {
  if (!gameState) return null;

  // Define AI info based on selectedAIType
  const aiInfoMap = {
    'bladework_v2': {
      name: 'Bladework',
      logic: 'Hard Coded'
    },
    'froggie': {
      name: 'Froggie',
      logic: 'Random'
    }
  };

  const aiInfo = aiInfoMap[selectedAIType] || aiInfoMap['bladework_v2'];
  const aiName = aiInfo.name;
  const aiLogic = aiInfo.logic;

  return (
    <div className="debug-panel">
      <div className="debug-panel-item bold">AI Name: {aiName}</div>
      <div className="debug-panel-item bold">AI Logic: {aiLogic}</div>
      <div className="debug-panel-item">Current Player: {gameState.current_player} (0=You, 1=AI)</div>
      <div className="debug-panel-item">Hand Over: {handOver ? 'Yes' : 'No'}</div>
      <div className="debug-panel-item">Can Check: {canCheck() ? 'Yes' : 'No'}</div>
      <div className="debug-panel-item">Can Call: {canCall() ? 'Yes' : 'No'}</div>
      <div className="debug-panel-item">Can Raise: {canRaise() ? 'Yes' : 'No'}</div>
      <div className="debug-panel-item">Action Panel Should Show: {(!handOver && gameState.current_player === 0) ? 'YES' : 'NO'}</div>
      {gameState.current_player === 1 && (
        <button 
          onClick={() => processAITurn()}
          className="debug-panel-button"
        >
          Force AI Turn
        </button>
      )}
    </div>
  );
};

export default DebugPanel;
