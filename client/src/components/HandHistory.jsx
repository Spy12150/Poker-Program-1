import React from 'react';

// Left side panel for hand history

const HandHistory = ({ gameState }) => {
  const formatActionHistory = () => {
    if (!gameState?.action_history) return [];
    return gameState.action_history.slice(-10); // Show last 10 actions
  };

  return (
    <div className="side-panel">
      <div className="history-title">ACTION HISTORY</div>
      <div>
        {formatActionHistory().map((entry, idx) => (
          <div key={idx} className="history-entry">
            <strong>{entry.player}</strong> {entry.action.charAt(0).toUpperCase() + entry.action.slice(1)}
            {entry.action === 'raise' && entry.amount && entry.amount > 0 && ` $${entry.amount}`} 
            <span className="round">({entry.round})</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default HandHistory;
