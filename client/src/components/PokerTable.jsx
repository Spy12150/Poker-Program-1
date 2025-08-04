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
    
    // Additional validation to prevent invalid cards
    if (!isCardback && (!card || typeof card !== 'string' || card.length < 2)) {
      console.error('CardImage received invalid card, using fallback:', card);
      isCardback = true;
      card = selectedCardback;
    }
    
    // Special check for corrupt cardback strings
    if (!isCardback && card.startsWith('Cardback')) {
      console.warn('CardImage: Received cardback string when expecting regular card:', card);
      isCardback = true;
      card = selectedCardback;
    }
    
    let cardSrc;
    try {
      if (isCardback) {
        console.log('CardImage: Using cardback:', selectedCardback);
        cardSrc = useCardImage(selectedCardback);
      } else {
        console.log('CardImage: Processing regular card:', card);
        const translatedCard = translateCard(card);
        if (translatedCard === 'Cardback1') {
          // translateCard returned fallback, use cardback instead
          console.warn('CardImage: translateCard returned fallback, using cardback');
          cardSrc = useCardImage(selectedCardback);
        } else {
          cardSrc = useCardImage(translatedCard);
        }
      }
    } catch (error) {
      console.error('Error in CardImage with card:', card, 'error:', error);
      cardSrc = useCardImage(selectedCardback); // Use selected cardback as fallback
    }
    
    const handleImageError = (e) => {
      console.error('Image failed to load:', e.target.src);
      // If WebP fails, try PNG fallback
      const currentSrc = e.target.src;
      if (currentSrc.includes('.webp')) {
        const pngSrc = currentSrc.replace('.webp', '.png');
        console.log('Trying PNG fallback:', pngSrc);
        e.target.src = pngSrc;
      } else {
        // If both fail, use a different cardback as last resort
        console.warn('Both WebP and PNG failed, using Cardback1 as last resort');
        e.target.src = '/IvoryCards/Cardback1.webp';
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
                  let playerHand;
                  if (showdown && gameState.players[1]?.hand && Array.isArray(gameState.players[1].hand)) {
                    // Validate each card in the hand
                    playerHand = gameState.players[1].hand.map(cardData => {
                      if (!cardData || typeof cardData !== 'string' || cardData.length < 2) {
                        console.warn('Invalid card in opponent hand during showdown:', cardData);
                        return selectedCardback;
                      }
                      return cardData;
                    });
                  } else {
                    // Not showdown or invalid hand data - use cardbacks
                    playerHand = [selectedCardback, selectedCardback];
                  }
                  
                  console.log('Opponent hand being rendered:', playerHand, 'showdown:', showdown);
                  
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
                {(() => {
                  const playerHand = gameState.player_hand;
                  if (!playerHand || !Array.isArray(playerHand)) {
                    console.warn('Invalid or missing player_hand in gameState:', playerHand);
                    return null;
                  }
                  
                  return playerHand.map((playerCard, idx) => {
                    if (!playerCard || typeof playerCard !== 'string' || playerCard.length < 2) {
                      console.warn('Invalid card in player hand:', playerCard);
                      return (
                        <CardImage
                          key={idx}
                          card={selectedCardback}
                          isCardback={true}
                          className="card"
                          alt="invalid card"
                        />
                      );
                    }
                    
                    return (
                      <CardImage
                        key={idx}
                        card={playerCard}
                        className="card"
                        alt="your card"
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
};

export default PokerTable;
