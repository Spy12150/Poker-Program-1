import React from 'react';

const PokerTable = ({ 
  gameState, 
  showdown, 
  dealingCards, 
  newCardIndices, 
  hasPlayerChecked, 
  getPlayerPosition, 
  handOver, 
  evaluateHand, 
  translateCard,
  selectedCardback 
}) => {
  if (!gameState) return null;

  return (
    <div className="table-container">
      <div className="poker-table">
        <div className="table-inner">
          
          {/* AI Player (Opponent) */}
          <div className="opponent-area">
            <div className="player-card">
              <div className="player-name">{gameState.players[1]?.name} (AI)</div>
              <div className="player-stats">
                <span>Stack: ${gameState.players[1]?.stack}</span>
              </div>
              <div className="hand-container">
                {(showdown ? gameState.players[1]?.hand || [selectedCardback, selectedCardback] : [selectedCardback, selectedCardback]).map((card, idx) => (
                  <img 
                    key={idx} 
                    src={`/IvoryCards/${showdown ? translateCard(card) : selectedCardback}.png`} 
                    alt="card"
                    className="card"
                  />
                ))}
              </div>
              
              {/* Position Indicators */}
              <div className="position-indicators">
                {(() => {
                  const position = getPlayerPosition(1);
                  return (
                    <>
                      {position.isDealer && (
                        <div className="position-indicator dealer-button">D</div>
                      )}
                      {position.isSmallBlind && (
                        <div className="position-indicator small-blind">SB</div>
                      )}
                      {position.isBigBlind && (
                        <div className="position-indicator big-blind">BB</div>
                      )}
                    </>
                  );
                })()}
              </div>
              
              {/* AI Thinking Indicator */}
              {!handOver && gameState.current_player === 1 && (
                <div className="turn-indicator ai-thinking">
                  AI is thinking...
                </div>
              )}
            </div>
            
            {/* AI Current Bet */}
            {(gameState.players[1]?.current_bet > 0 || hasPlayerChecked(1)) && (
              <div className="current-bet-container ai-bet">
                {gameState.players[1]?.current_bet > 0 ? 
                  `$${gameState.players[1]?.current_bet}` : 
                  'CHECK'
                }
              </div>
            )}
          </div>

          {/* Community Cards & Pot */}
          <div className="community-area">
            <div className="pot-info">
              POT: ${gameState.pot}
            </div>
            <div className={`community-cards ${dealingCards ? 'dealing-animation' : ''}`}>
              {gameState.community.map((card, idx) => (
                <img 
                  key={idx} 
                  src={`/IvoryCards/${translateCard(card)}.png`} 
                  alt="community card"
                  className={`community-card ${dealingCards && newCardIndices.includes(idx) ? 'new-card' : ''}`}
                />
              ))}
              {/* Show placeholders for undealt cards */}
              {Array(5 - gameState.community.length).fill().map((_, idx) => (
                <div key={`placeholder-${idx}`} className="card-placeholder">?</div>
              ))}
            </div>
          </div>

          {/* Human Player */}
          <div className="player-area">
            {/* Player Current Bet */}
            {(gameState.players[0]?.current_bet > 0 || hasPlayerChecked(0)) && (
              <div className="current-bet-container player-bet">
                {gameState.players[0]?.current_bet > 0 ? 
                  `$${gameState.players[0]?.current_bet}` : 
                  'CHECK'
                }
              </div>
            )}
            
            <div className="player-card">
              <div className="player-name">{gameState.players[0]?.name} (You)</div>
              <div className="player-stats">
                <span>Stack: ${gameState.players[0]?.stack}</span>
              </div>
              <div className="hand-container">
                {gameState.player_hand?.map((card, idx) => (
                  <img 
                    key={idx} 
                    src={`/IvoryCards/${translateCard(card)}.png`} 
                    alt="your card"
                    className="card"
                  />
                ))}
              </div>
              
              {/* Position Indicators */}
              <div className="position-indicators">
                {(() => {
                  const position = getPlayerPosition(0);
                  return (
                    <>
                      {position.isDealer && (
                        <div className="position-indicator dealer-button">D</div>
                      )}
                      {position.isSmallBlind && (
                        <div className="position-indicator small-blind">SB</div>
                      )}
                      {position.isBigBlind && (
                        <div className="position-indicator big-blind">BB</div>
                      )}
                    </>
                  );
                })()}
              </div>
              
              {/* Your Turn Indicator */}
              {!handOver && gameState.current_player === 0 && (
                <div className="turn-indicator your-turn">
                  Your turn
                </div>
              )}
            </div>

            {/* Hand Evaluation Display */}
            {gameState.player_hand && (
              <div className="hand-evaluation">
                {evaluateHand(gameState.player_hand, gameState.community || [])}
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
};

export default PokerTable;
