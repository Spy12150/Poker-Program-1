import React from 'react';
import { AI_OPTIONS } from './aiOptions';

// Left side panel for hand history

const HandHistory = ({ gameState }) => {
  const formatActionHistory = () => {
    if (!gameState?.action_history) return [];
    const last = gameState.action_history.slice(-20);
    const youEngineName = gameState?.players?.[0]?.name || 'Player 1';
    const deduped = [];
    let prevSig = null;
    for (const entry of last) {
      const normalized = entry || {};
      let displayPlayer;
      if (normalized.player === (gameState?.players?.[1]?.name || 'AI')) {
        displayPlayer = opponentDisplayName;
      } else if (normalized.player === youEngineName) {
        displayPlayer = 'You';
      } else {
        displayPlayer = normalized.player;
      }
      const action = (normalized.action || '').toLowerCase();
      const amount = Number(normalized.amount || 0);
      const round = normalized.round || 'preflop';
      const sig = action === 'raise'
        ? `${displayPlayer}|${action}|${amount}|${round}`
        : `${displayPlayer}|${action}|${round}`;
      if (sig !== prevSig) {
        deduped.push({ displayPlayer, action, amount, round });
        prevSig = sig;
      }
    }
    return deduped.slice(-10);
  };

  // Resolve opponent display name from shared options using ai_type
  const aiType = gameState?.ai_info?.type || 'bladework_v2';
  const aiNameMap = Object.fromEntries(AI_OPTIONS.map(o => [o.id, o.name]));
  const opponentDisplayName = aiNameMap[aiType] || gameState?.players?.[1]?.name || 'AI';

  return (
    <div className="side-panel">
      <div className="history-title">ACTION HISTORY</div>
      <div>
        {formatActionHistory().map((entry, idx) => {
          const displayPlayer = entry.displayPlayer;
          const isAI = displayPlayer !== 'You';
          const formatVerb = (action, thirdPerson) => {
            const a = (action || '').toLowerCase();
            const map = {
              call: thirdPerson ? 'calls' : 'call',
              check: thirdPerson ? 'checks' : 'check',
              fold: thirdPerson ? 'folds' : 'fold',
              raise: thirdPerson ? 'raises' : 'raise',
              bet: thirdPerson ? 'bets' : 'bet',
            };
            return (map[a] || a).replace(/^./, c => c.toUpperCase());
          };
          const verb = formatVerb(entry.action, isAI);
          return (
          <div key={idx} className="history-entry">
            <strong>{displayPlayer}</strong> {verb}
            {entry.action === 'raise' && entry.amount && entry.amount > 0 && ` $${entry.amount}`} 
            <span className="round">({entry.round})</span>
          </div>
          );
        })}
      </div>
    </div>
  );
};

export default HandHistory;
