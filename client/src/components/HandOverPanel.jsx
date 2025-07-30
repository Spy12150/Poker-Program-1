import React from 'react';

const HandOverPanel = ({ handOver, showdown, winners, newHand, loading }) => {
  if (!handOver) return null;

  return (
    <div className="hand-over-panel">
      <h2>HAND COMPLETE!</h2>
      {showdown && (
        <div className="winners-section">
          <h3>SHOWDOWN RESULTS:</h3>
          {winners.map((winner, idx) => (
            <div key={idx} className="winner-info">
              <strong>{winner.name}</strong> wins with {winner.hand_class}
            </div>
          ))}
        </div>
      )}
      <button onClick={newHand} disabled={loading} className="start-button">
        {loading ? 'Dealing...' : 'Deal Next Hand'}
      </button>
    </div>
  );
};

export default HandOverPanel;
