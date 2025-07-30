import React from 'react';

const DebugPanel = ({ gameState, handOver, canCheck, canCall, canRaise, processAITurn }) => {
  if (!gameState || handOver) return null;

  return (
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
  );
};

export default DebugPanel;
