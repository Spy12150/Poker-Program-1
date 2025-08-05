import React, { memo, useMemo } from 'react';
import { useCardImage } from '../hooks/useImagePreloader';

// Card image component moved outside to prevent recreation and fix hook calls
const CardImage = React.memo(({ card, isCardback = false, className = "card", alt = "card", selectedCardback, translateCard }) => {
  // Additional validation to prevent invalid cards
  if (!isCardback && (!card || typeof card !== 'string' || card.length < 2)) {
    isCardback = true;
    card = selectedCardback;
  }
  
  // Special check for corrupt cardback strings
  if (!isCardback && card.startsWith('Cardback')) {
    isCardback = true;
    card = selectedCardback;
  }
  
  // Call useCardImage hooks at component level (proper hook usage)
  const cardbackSrc = useCardImage(selectedCardback);
  
  // Get the actual card image - only call useCardImage if we have a valid card
  let actualCardSrc = cardbackSrc; // fallback
  if (!isCardback && card && typeof card === 'string' && card.length >= 2) {
    try {
      const translatedCard = translateCard(card);
      if (translatedCard && translatedCard !== 'Cardback1') {
        actualCardSrc = useCardImage(translatedCard);
      }
    } catch (error) {
      // Use cardback fallback
    }
  }
  
  // Use stable image src
  const cardSrc = isCardback ? cardbackSrc : actualCardSrc;
  
  const handleImageError = (e) => {
    // If WebP fails, try PNG fallback
    const currentSrc = e.target.src;
    if (currentSrc.includes('.webp')) {
      const pngSrc = currentSrc.replace('.webp', '.png');
      e.target.src = pngSrc;
    } else {
      // If both fail, use a different cardback as last resort
      e.target.src = '/IvoryCards/Cardback1.webp';
    }
  };
  
  return (
    <img 
      key={`${card}-${isCardback}`} // Stable key for React reconciliation
      src={cardSrc} 
      alt={alt} 
      className={className} 
      loading="eager" // Eager loading for instant display
      draggable={false}
      onError={handleImageError}
    />
  );
});

const PokerTable = memo(({ 
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
                  let playerHand;
                  if (showdown && gameState.players[1]?.hand && Array.isArray(gameState.players[1].hand)) {
                    // Validate each card in the hand
                    playerHand = gameState.players[1].hand.map(cardData => {
                      if (!cardData || typeof cardData !== 'string' || cardData.length < 2) {
            
                        return selectedCardback;
                      }
                      return cardData;
                    });
                  } else {
                    // Not showdown or invalid hand data - use cardbacks
                    playerHand = [selectedCardback, selectedCardback];
                  }
                  
          
                  
                  return playerHand.map((cardData, idx) => (
                    <CardImage
                      key={idx}
                      card={cardData}
                      isCardback={!showdown}
                      className="card"
                      alt="card"
                      selectedCardback={selectedCardback}
                      translateCard={translateCard}
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
                  key={`${communityCard}-${idx}`}
                  card={communityCard}
                  className={`community-card ${dealingCards && newCardIndices.includes(idx) ? 'new-card' : ''}`}
                  alt="community card"
                  selectedCardback={selectedCardback}
                  translateCard={translateCard}
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
                {(() => {
                  const playerHand = gameState.player_hand;
                  if (!playerHand || !Array.isArray(playerHand)) {
              
                    return null;
                  }
                  
                  return playerHand.map((playerCard, idx) => {
                    if (!playerCard || typeof playerCard !== 'string' || playerCard.length < 2) {
          
                      return (
                        <CardImage
                          key={idx}
                          card={selectedCardback}
                          isCardback={true}
                          className="card"
                          alt="invalid card"
                          selectedCardback={selectedCardback}
                          translateCard={translateCard}
                        />
                      );
                    }
                    
                    return (
                      <CardImage
                        key={idx}
                        card={playerCard}
                        className="card"
                        alt="your card"
                        selectedCardback={selectedCardback}
                        translateCard={translateCard}
                      />
                    );
                  });
                })()}
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
});

// Network-resilient animation - block ALL re-renders during animation
const arePropsEqual = (prevProps, nextProps) => {
  // CRITICAL: Block ALL re-renders when either prev OR next is animating
  // This handles slow WiFi where delayed messages arrive during animation
  if (prevProps.dealingCards || nextProps.dealingCards) {
    // If we're entering animation (start) or have essential changes, allow re-render
    if (prevProps.dealingCards !== nextProps.dealingCards) {
      return false; // Animation state changed - allow re-render for setup
    }
    
    // During animation: only allow re-renders for new cards (length increase)
    const prevCommunity = prevProps.gameState?.community || [];
    const nextCommunity = nextProps.gameState?.community || [];
    if (nextCommunity.length > prevCommunity.length) {
      return false; // New cards dealt - allow re-render for DOM update
    }
    
    // Block everything else during animation (delayed network updates, etc.)
    return true; // "Equal" props - prevent re-render during animation
  }
  
  // Outside animation: normal React behavior (allow all re-renders)
  return false;
};

export default memo(PokerTable, arePropsEqual);
