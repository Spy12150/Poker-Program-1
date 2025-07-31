import React from 'react';

const DebugPanel = ({ gameState, handOver, canCheck, canCall, canRaise, processAITurn }) => {
  if (!gameState) return null;

  // Determine AI info based on current setup
  // Currently using ai_gto_enhanced.py, so showing "Bladework v1"
  const aiName = "Bladework v1";
  const aiLogic = "Hard Coded";

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
