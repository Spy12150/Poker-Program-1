import React from 'react';
import { AI_OPTIONS } from './aiOptions';

const DebugPanel = ({ gameState, handOver, isCheckAllowed, isCallAllowed, isRaiseAllowed, processAITurn, selectedAIType }) => {
  if (!gameState) return null;

  // Define AI info based on selectedAIType using shared options list
  const aiInfoMap = Object.fromEntries(
    AI_OPTIONS.map(({ id, name, logic }) => [id, { name, logic }])
  );

  const aiInfo = aiInfoMap[selectedAIType] || aiInfoMap['bladework_v2'];
  const aiName = aiInfo.name;
  const aiLogic = aiInfo.logic;

  return (
    <div className="debug-panel">
      <div className="debug-panel-item bold">AI Name: {aiName}</div>
      <div className="debug-panel-item bold">AI Logic: {aiLogic}</div>
      <div className="debug-panel-item">Current Player: {gameState.current_player} (0=You, 1=AI)</div>
      <div className="debug-panel-item">Hand Over: {handOver ? 'Yes' : 'No'}</div>
      <div className="debug-panel-item">Can Check: {isCheckAllowed() ? 'Yes' : 'No'}</div>
      <div className="debug-panel-item">Can Call: {isCallAllowed() ? 'Yes' : 'No'}</div>
      <div className="debug-panel-item">Can Raise: {isRaiseAllowed() ? 'Yes' : 'No'}</div>
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
