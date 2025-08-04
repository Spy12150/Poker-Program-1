import React from 'react';
import { useCardImage } from '../hooks/useImagePreloader';

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
  selectedCardback,
  isBackground = false
}) => {
  // Card image component with WebP support and error handling
  const CardImage = ({ card, isCardback = false, className = "card", alt = "card" }) => {
    // Debug logging
    console.log('CardImage called with:', { card, isCardback, typeof_card: typeof card });
    
    let cardSrc;
    try {
      cardSrc = useCardImage(isCardback ? selectedCardback : translateCard(card));
    } catch (error) {
      console.error('Error in CardImage with card:', card, 'error:', error);
      cardSrc = useCardImage('Cardback1'); // Fallback
    }
    
    const handleImageError = (e) => {
      // If WebP fails, try PNG fallback
      const currentSrc = e.target.src;
      if (currentSrc.includes('.webp')) {
        e.target.src = currentSrc.replace('.webp', '.png');
      } else {
        // If both fail, show a placeholder
        e.target.style.display = 'none';
        console.warn('Failed to load card image:', currentSrc);
      }
    };
    
    return (
      <img 
        src={cardSrc} 
        alt={alt} 
        className={className} 
        onError={handleImageError}
      />
    );
  };
  // Show empty table in background mode
  if (isBackground) {
    return (
      <div className="table-container background-table">
        <div className="poker-table">
          <div className="table-inner">
            {/* Empty table for background */}
          </div>
        </div>
      </div>
    );
  }

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
                {(() => {
                  const playerHand = showdown ? gameState.players[1]?.hand || [selectedCardback, selectedCardback] : [selectedCardback, selectedCardback];
                  return playerHand.map((cardData, idx) => (
                    <CardImage
                      key={idx}
                      card={cardData}
                      isCardback={!showdown}
                      className="card"
                      alt="card"
                    />
                  ));
                })()}
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
              {gameState.community.map((communityCard, idx) => (
                <CardImage
                  key={idx}
                  card={communityCard}
                  className={`community-card ${dealingCards && newCardIndices.includes(idx) ? 'new-card' : ''}`}
                  alt="community card"
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
                {gameState.player_hand?.map((playerCard, idx) => (
                  <CardImage
                    key={idx}
                    card={playerCard}
                    className="card"
                    alt="your card"
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
    </div>
  );
};

export default PokerTable;
