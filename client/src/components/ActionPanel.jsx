import React from 'react';

const ActionPanel = ({
  gameState,
  handOver,
  loading,
  makeAction,
  isCheckAllowed,
  isCallAllowed,
  isRaiseAllowed,
  getActualCallAmount,
  betSliderValue,
  setBetSliderValue,
  setRaiseAmount,
  minBet,
  maxBet,
  getCallAmount,
  betToSliderPosition,
  sliderPositionToBet
}) => {
  if (!gameState || handOver || gameState.current_player !== 0) {
    return null;
  }

  return (
    <div className="modern-action-panel">
      {/* Main Action Buttons Row */}
      <div className="main-actions-row">
        {!isCheckAllowed() && (
          <button
            onClick={() => makeAction('fold')}
            disabled={loading}
            className="modern-action-button fold-button"
          >
            FOLD
          </button>
        )}
        
        <button
          onClick={() => makeAction(isCheckAllowed() ? 'check' : 'call')}
          disabled={loading || (!isCheckAllowed() && !isCallAllowed())}
          className="modern-action-button call-button"
        >
          {isCheckAllowed() ? 'CHECK' : `CALL ${getActualCallAmount() > 0 ? '$' + getActualCallAmount() : ''}`}
        </button>
        
        <button
          onClick={() => makeAction('raise', betSliderValue)}
          disabled={loading || !isRaiseAllowed() || betSliderValue === '' || betSliderValue < minBet || betSliderValue > maxBet}
          className="modern-action-button raise-button"
        >
          RAISE TO<br/>${betSliderValue || 0}
        </button>
      </div>

      {/* Betting Controls Row */}
      <div className="betting-controls-row">
        {/* Decrease/Increase Buttons */}
        <button 
          className="bet-adjust-button decrease"
          onClick={() => {
            const newValue = Math.max(minBet, betSliderValue - 20);
            setBetSliderValue(newValue);
            setRaiseAmount(newValue.toString());
          }}
          disabled={betSliderValue <= minBet}
        >
          −
        </button>
        
        <button 
          className="bet-adjust-button bars"
          onClick={() => {
            const callAmount = getCallAmount();
            const currentPot = gameState.pot;
            const opponentCurrentBet = gameState.players[1].current_bet || 0;
            const potBet = currentPot + callAmount + opponentCurrentBet;
            const finalBet = Math.min(maxBet, Math.max(minBet, potBet));
            setBetSliderValue(finalBet);
            setRaiseAmount(finalBet.toString());
          }}
        >
          |||
        </button>

        {/* Bet Slider */}
        <div className="slider-container">
          <input
            type="range"
            min={0}
            max={100}
            value={betToSliderPosition(betSliderValue, minBet, maxBet)}
            onChange={(e) => {
              const sliderPosition = Number(e.target.value);
              const betValue = sliderPositionToBet(sliderPosition, minBet, maxBet);
              setBetSliderValue(betValue);
              setRaiseAmount(betValue.toString());
            }}
            className="bet-slider"
          />
        </div>

        <button 
          className="bet-adjust-button increase"
          onClick={() => {
            const newValue = Math.min(maxBet, betSliderValue + 20);
            setBetSliderValue(newValue);
            setRaiseAmount(newValue.toString());
          }}
          disabled={betSliderValue >= maxBet}
        >
          +
        </button>

        {/* Bet Amount Display as Input */}
        <input
          type="number"
          value={betSliderValue}
          onChange={(e) => {
            const inputValue = e.target.value;
            // Allow empty string or any valid number input
            if (inputValue === '') {
              setBetSliderValue('');
              setRaiseAmount('');
            } else {
              const numValue = Number(inputValue);
              setBetSliderValue(numValue);
              setRaiseAmount(inputValue);
            }
          }}
          onBlur={(e) => {
            const inputValue = e.target.value;
            // If empty on blur, don't set to 0, keep it empty
            if (inputValue === '') {
              setBetSliderValue('');
              setRaiseAmount('');
            } else {
              const numValue = Number(inputValue) || 0;
              setBetSliderValue(numValue);
              setRaiseAmount(numValue.toString());
            }
          }}
          className="bet-amount-input"
        />
      </div>

      {/* Quick Bet Buttons - Conditional based on betting round */}
      <div className="quick-bet-row">
        {gameState.betting_round === 'preflop' ? (
          // Preflop buttons: 2.5x BB, 3x BB, Pot, All-in
          <>
            {(() => {
              const bigBlind = gameState.big_blind || 10;
              const bet25x = Math.round(bigBlind * 2.5);
              return minBet <= bet25x ? (
                <button 
                  className="quick-bet-button bet-2-5x"
                  onClick={() => {
                    setBetSliderValue(bet25x);
                    setRaiseAmount(bet25x.toString());
                  }}
                >
                  2.5x
                </button>
              ) : null;
            })()}
            {(() => {
              const bigBlind = gameState.big_blind || 10;
              const bet3x = bigBlind * 3;
              return minBet <= bet3x ? (
                <button 
                  className="quick-bet-button bet-3x"
                  onClick={() => {
                    setBetSliderValue(bet3x);
                    setRaiseAmount(bet3x.toString());
                  }}
                >
                  3x
                </button>
              ) : null;
            })()}
            {(() => {
              const callAmount = getCallAmount();
              const currentPot = gameState.pot;
              const opponentCurrentBet = gameState.players[1].current_bet || 0;
              const potBet = currentPot + callAmount + opponentCurrentBet;
              
              // Only show Pot button if calculated bet is greater than minimum bet
              return potBet > minBet ? (
                <button 
                  className="quick-bet-button bet-pot"
                  onClick={() => {
                    const finalBet = Math.min(maxBet, Math.max(minBet, potBet));
                    setBetSliderValue(finalBet);
                    setRaiseAmount(finalBet.toString());
                  }}
                >
                  Pot
                </button>
              ) : null;
            })()}
            <button 
              className="quick-bet-button bet-allin"
              onClick={() => {
                setBetSliderValue(maxBet);
                setRaiseAmount(maxBet.toString());
              }}
            >
              ALL-IN
            </button>
          </>
        ) : (
          // Post-flop buttons: 1/3, 1/2, Pot, All-in
          <>
            {(() => {
              const callAmount = getCallAmount();
              const currentPot = gameState.pot;
              const opponentCurrentBet = gameState.players[1].current_bet || 0;
              const totalPot = currentPot + opponentCurrentBet;
              const oneThirdPot = Math.ceil(totalPot / 3) + callAmount;
              
              // Only show 1/3 button if calculated bet is greater than minimum bet
              return oneThirdPot > minBet ? (
                <button 
                  className="quick-bet-button bet-third"
                  onClick={() => {
                    const finalBet = Math.min(maxBet, Math.max(minBet, oneThirdPot));
                    setBetSliderValue(finalBet);
                    setRaiseAmount(finalBet.toString());
                  }}
                >
                  1/3 Pot
                </button>
              ) : null;
            })()}
            
            {(() => {
              const callAmount = getCallAmount();
              const currentPot = gameState.pot;
              const opponentCurrentBet = gameState.players[1].current_bet || 0;
              const totalPot = currentPot + opponentCurrentBet;
              const halfPot = Math.ceil(totalPot / 2) + callAmount;
              
              // Only show 1/2 button if calculated bet is greater than minimum bet
              return halfPot > minBet ? (
                <button 
                  className="quick-bet-button bet-half"
                  onClick={() => {
                    const finalBet = Math.min(maxBet, Math.max(minBet, halfPot));
                    setBetSliderValue(finalBet);
                    setRaiseAmount(finalBet.toString());
                  }}
                >
                  1/2 Pot
                </button>
              ) : null;
            })()}
            
            {(() => {
              const callAmount = getCallAmount();
              const currentPot = gameState.pot;
              const opponentCurrentBet = gameState.players[1].current_bet || 0;
              const potBet = currentPot + callAmount + opponentCurrentBet;
              
              // Only show Pot button if calculated bet is greater than minimum bet
              return potBet > minBet ? (
                <button 
                  className="quick-bet-button bet-pot"
                  onClick={() => {
                    const finalBet = Math.min(maxBet, Math.max(minBet, potBet));
                    setBetSliderValue(finalBet);
                    setRaiseAmount(finalBet.toString());
                  }}
                >
                  Pot
                </button>
              ) : null;
            })()}
            
            <button 
              className="quick-bet-button bet-allin"
              onClick={() => {
                setBetSliderValue(maxBet);
                setRaiseAmount(maxBet.toString());
              }}
            >
              ALL-IN
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default ActionPanel;
