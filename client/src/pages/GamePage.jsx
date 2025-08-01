import React, { useState, useEffect } from 'react';
import './GamePage.css';

// Components
import GameHeader from '../components/GameHeader';
import GameMessage from '../components/GameMessage';
import StartGameButton from '../components/StartGameButton';
import PokerTable from '../components/PokerTable';
import ActionPanel from '../components/ActionPanel';
import HandOverPanel from '../components/HandOverPanel';
import HandHistory from '../components/HandHistory';
import DebugPanel from '../components/DebugPanel';

// Utilities
import { evaluateHand, translateCard } from '../utils/handEvaluation';
import { 
  betToSliderPosition, 
  sliderPositionToBet, 
  getCallAmount, 
  getActualCallAmount, 
  canCheck, 
  canCall, 
  canRaise, 
  getPlayerPosition, 
  hasPlayerChecked 
} from '../utils/gameUtils';

const GamePage = () => {
  const [gameState, setGameState] = useState(null);
  const [gameId, setGameId] = useState(null);
  const [message, setMessage] = useState('');
  const [winners, setWinners] = useState([]);
  const [handOver, setHandOver] = useState(false);
  const [showdown, setShowdown] = useState(false);
  const [raiseAmount, setRaiseAmount] = useState('');
  const [loading, setLoading] = useState(false);
  const [betSliderValue, setBetSliderValue] = useState(0);
  const [minBet, setMinBet] = useState(0);
  const [maxBet, setMaxBet] = useState(0);
  const [dealingCards, setDealingCards] = useState(false);
  const [previousCommunityLength, setPreviousCommunityLength] = useState(0);
  const [newCardIndices, setNewCardIndices] = useState([]);
  const [selectedCardback, setSelectedCardback] = useState('Cardback18');

  // Array of all available cardbacks from IvoryCards folder
  const cardbacks = [
    'Cardback18', 'Cardback17', 'Cardback3', 'Cardback4', 'Cardback5',
    'Cardback6', 'Cardback7', 'Cardback8', 'Cardback9', 'Cardback10',
    'Cardback11', 'Cardback12', 'Cardback13', 'Cardback14', 
    'Cardback16', 'Cardback2', 'Cardback1', 'Cardback19'
  ];

  const cycleCardback = () => {
    const currentIndex = cardbacks.indexOf(selectedCardback);
    const nextIndex = (currentIndex + 1) % cardbacks.length;
    setSelectedCardback(cardbacks[nextIndex]);
  };

  // Function definitions (moved above useEffect to avoid reference errors)
  const getCallAmountWrapper = () => getCallAmount(gameState);
  const getActualCallAmountWrapper = () => getActualCallAmount(gameState);
  const canCheckWrapper = () => canCheck(gameState);
  const canCallWrapper = () => canCall(gameState);
  const canRaiseWrapper = () => canRaise(gameState);
  const getPlayerPositionWrapper = (playerIndex) => getPlayerPosition(gameState, playerIndex);
  const hasPlayerCheckedWrapper = (playerIndex) => hasPlayerChecked(gameState, playerIndex);

  const updateBetLimits = (state) => {
    if (!state || !state.players || state.current_player !== 0) return;
    
    const player = state.players[0];
    const currentBet = state.current_bet || 0;
    const playerCurrentBet = player.current_bet || 0;
    const lastBetAmount = state.last_bet_amount || 0;
    
    // Minimum raise calculation (matches backend logic)
    const bigBlind = state.big_blind || 10;
    let minRaise;
    
    if (currentBet === 0) {
      // First bet of the round - minimum is big blind
      minRaise = bigBlind;
    } else {
      // Must raise by at least the size of the last bet/raise
      minRaise = currentBet + Math.max(lastBetAmount, bigBlind);
    }
    
    // Maximum bet: all-in
    const maxBetAmount = player.stack + playerCurrentBet;
    
    // Ensure min bet doesn't exceed max bet
    const finalMinBet = Math.min(minRaise, maxBetAmount);
    
    setMinBet(finalMinBet);
    setMaxBet(maxBetAmount);
    // Always default to minimum bet for new actions
    setBetSliderValue(finalMinBet);
    setRaiseAmount(finalMinBet.toString());
  };

  const handleSliderRaise = () => {
    if (betSliderValue < minBet) {
      setMessage(`Minimum bet is $${minBet}`);
      return;
    }
    if (betSliderValue > maxBet) {
      setMessage(`Maximum bet is $${maxBet}`);
      return;
    }
    makeAction('raise', betSliderValue);
  };

  // Update betting limits when game state changes
  useEffect(() => {
    if (gameState) {
      updateBetLimits(gameState);
    }
  }, [gameState]);

  // Handle card dealing animation
  useEffect(() => {
    if (gameState && gameState.community) {
      const currentCommunityLength = gameState.community.length;
      if (currentCommunityLength > previousCommunityLength) {
        setDealingCards(true);
        
        // Determine which cards are new
        const newIndices = [];
        for (let i = previousCommunityLength; i < currentCommunityLength; i++) {
          newIndices.push(i);
        }
        
        // Special case for flop: if we're going from 0 to 3 cards, animate all 3
        if (previousCommunityLength === 0 && currentCommunityLength === 3) {
          setNewCardIndices([0, 1, 2]);
        } else {
          setNewCardIndices(newIndices);
        }
        
        // Check if it's an all-in showdown with multiple cards dealt at once
        const cardsDifference = currentCommunityLength - previousCommunityLength;
        const animationDuration = cardsDifference > 1 ? 1500 : 1000; // Longer for multiple cards
        
        setTimeout(() => {
          setDealingCards(false);
          setNewCardIndices([]);
        }, animationDuration);
      }
      setPreviousCommunityLength(currentCommunityLength);
    }
  }, [gameState?.community?.length, previousCommunityLength]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (event) => {
      if (!gameState || handOver || gameState.current_player !== 0 || loading) return;

      switch (event.key.toLowerCase()) {
        case 'f':
          if (event.ctrlKey || event.metaKey) return; // Don't interfere with browser shortcuts
          makeAction('fold');
          break;
        case 'c':
          if (event.ctrlKey || event.metaKey) return;
          if (canCheckWrapper()) {
            makeAction('check');
          } else if (canCallWrapper()) {
            makeAction('call');
          }
          break;
        case 'r':
          if (event.ctrlKey || event.metaKey) return;
          if (canRaiseWrapper()) {
            handleSliderRaise();
          }
          break;
        default:
          break;
      }
    };

    document.addEventListener('keypress', handleKeyPress);
    return () => document.removeEventListener('keypress', handleKeyPress);
  }, [gameState, handOver, loading]);

  const startGame = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/start-game`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await res.json();

      if (data.error) {
        setMessage(`Error: ${data.error}`);
        return;
      }

      setGameId(data.game_id);
      setGameState(data);
      setHandOver(false);
      setShowdown(false);
      setWinners([]);
      updateBetLimits(data);
      
      // Debug logging for AI first move
      console.log('=== START GAME DEBUG ===');
      console.log('Current player after start:', data.current_player);
      console.log('Hand over:', data.hand_over);
      console.log('AI should act first:', data.current_player === 1 && !data.hand_over);
      console.log('========================');
      
      // Check if AI needs to act first
      if (data.current_player === 1 && !data.hand_over) {
        console.log('AI needs to act first - scheduling processAITurn()');
        setTimeout(() => {
          console.log('Executing processAITurn() now');
          processAITurn(data.game_id); // Pass game_id directly to avoid state timing issue
        }, 1000); // Give a moment for UI to update, then process AI turn
      }
    } catch (error) {
      setMessage('Failed to start game. Make sure the server is running.');
    } finally {
      setLoading(false);
    }
  };

  const processAITurn = async (gameIdParam = null) => {
    const currentGameId = gameIdParam || gameId;
    console.log('processAITurn() called - gameId:', currentGameId, '(param:', gameIdParam, ', state:', gameId, ')');
    if (!currentGameId) {
      console.log('No gameId, returning early');
      return;
    }
    
    console.log('Sending request to process-ai-turn endpoint');
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/process-ai-turn`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_id: currentGameId })
      });
      const data = await res.json();

      if (data.game_state) {
        setGameState(data.game_state);
        updateBetLimits(data.game_state);
      }

      // Log console messages from backend to browser console
      if (data.console_logs && Array.isArray(data.console_logs)) {
        console.log('=== AI DECISION DEBUG ===');
        data.console_logs.forEach(log => console.log(log));
        console.log('=========================');
      }

      // Additional debug logging for action display
      if (data.game_state) {
        console.log('Game state after AI turn:', data.game_state);
        console.log('Action history:', data.game_state.action_history);
        console.log('AI current bet:', data.game_state.players[1]?.current_bet);
        console.log('Current player after AI turn:', data.game_state.current_player);
        console.log('Hand over after AI turn:', data.hand_over);
        
        // Check if AI has checked in current round using the new game state
        const aiPlayerName = data.game_state.players[1]?.name;
        const currentRound = data.game_state.betting_round || 'preflop';
        const recentActions = data.game_state.action_history.slice().reverse();
        let aiHasChecked = false;
        for (const action of recentActions) {
          if (action.player === aiPlayerName && action.round === currentRound) {
            aiHasChecked = action.action === 'check';
            break;
          }
        }
        console.log(`AI has checked in ${currentRound}:`, aiHasChecked);
        
        // Log if it should be player's turn now
        if (data.game_state.current_player === 0 && !data.hand_over) {
          console.log('It should be player\'s turn now - UI should show action panel');
        } else if (data.game_state.current_player === 1) {
          console.log('Still AI\'s turn after AI action - this might be an issue');
        }
      }

      if (data.hand_over) {
        setHandOver(true);
        setWinners(data.winners || []);
        setShowdown(data.showdown || false);
      }

      // Handle all-in showdown
      if (data.all_in_showdown) {
        setShowdown(true);
        setWinners(data.winners || []);
        if (data.message) {
          setMessage(data.message);
        }
      }

      // Show AI action message for 2 seconds
      if (data.message && !data.all_in_showdown) {
        setMessage(data.message);
      }

      // Check if AI needs to act again (e.g., after advancing to a new round)
      if (data.game_state && data.game_state.current_player === 1 && !data.hand_over && !data.all_in_showdown) {
        console.log('AI needs to act again - scheduling another processAITurn()');
        setTimeout(() => {
          processAITurn();
        }, 1000); // Brief delay before next AI action
      }
    } catch (error) {
      console.error('Failed to process AI turn:', error);
    }
  };

  const makeAction = async (action, amount = 0) => {
    if (!gameId || handOver || loading) return;
    
    setLoading(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/player-action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: gameId,
          action: action,
          amount: amount
        })
      });
      const data = await res.json();

      if (data.error) {
        setMessage(`Error: ${data.error}`);
        return;
      }

      setGameState(data.game_state);
      setHandOver(data.hand_over || false);
      setShowdown(data.showdown || false);
      setWinners(data.winners || []);
      setMessage(data.message || `You ${action}${amount > 0 ? ` $${amount}` : ''}`);
      setRaiseAmount('');
      updateBetLimits(data.game_state);

      // Handle all-in showdown
      if (data.all_in_showdown) {
        setShowdown(true);
        setWinners(data.winners || []);
        if (data.message) {
          setMessage(data.message);
        }
        return; // Don't process AI turn if showdown occurred
      }

        // Clear player action message after 1 second, then check for AI turn
        setTimeout(() => {
          // If it's now AI's turn and game isn't over, process AI turn after a brief delay
          if (data.game_state && data.game_state.current_player === 1 && !data.hand_over) {
            setTimeout(() => {
              processAITurn();
            }, 500); // Short delay before AI acts
          }
        }, 1000);

      } catch (error) {
        setMessage('Failed to make action. Check your connection.');
      } finally {
        setLoading(false);
      }
    };  const newHand = async () => {
    if (!gameId || loading) return;
    
    setLoading(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/new-hand`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_id: gameId })
      });
      const data = await res.json();

      if (data.error) {
        setMessage(`Error: ${data.error}`);
        return;
      }

      setGameState(data);
      setHandOver(false);
      setShowdown(false);
      setWinners([]);
      setMessage('New hand started!');
      updateBetLimits(data);
      
      // Check if AI needs to act first in the new hand
      if (data.current_player === 1 && !data.hand_over) {
        setTimeout(() => {
          processAITurn();
        }, 1000); // Give a moment for UI to update, then process AI turn
      }
    } catch (error) {
      setMessage('Failed to start new hand.');
    } finally {
      setLoading(false);
    }
  };

  const newRound = async () => {
    if (!gameId || loading) return;
    
    setLoading(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/new-round`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_id: gameId })
      });
      const data = await res.json();

      if (data.error) {
        setMessage(`Error: ${data.error}`);
        return;
      }

      setGameState(data);
      setHandOver(false);
      setShowdown(false);
      setWinners([]);
      setMessage('New round started! Chip stacks reset.');
      updateBetLimits(data);
      
      // Check if AI needs to act first in the new round
      if (data.current_player === 1 && !data.hand_over) {
        setTimeout(() => {
          processAITurn();
        }, 1000); // Give a moment for UI to update, then process AI turn
      }
    } catch (error) {
      setMessage('Failed to start new round.');
    } finally {
      setLoading(false);
    }
  };

  const handleRaise = () => {
    const amount = parseInt(raiseAmount);
    if (isNaN(amount) || amount <= 0) {
      setMessage('Please enter a valid raise amount');
      return;
    }
    makeAction('raise', amount);
  };

  return (
    <div className="game-container">
      <GameHeader />
      
      <StartGameButton 
        gameState={gameState} 
        startGame={startGame} 
        loading={loading} 
      />

      <GameMessage message={message} />

      {gameState && (
        <>
          <PokerTable
            gameState={gameState}
            showdown={showdown}
            dealingCards={dealingCards}
            newCardIndices={newCardIndices}
            hasPlayerChecked={hasPlayerCheckedWrapper}
            getPlayerPosition={getPlayerPositionWrapper}
            handOver={handOver}
            evaluateHand={evaluateHand}
            translateCard={translateCard}
            selectedCardback={selectedCardback}
          />

          <ActionPanel
            gameState={gameState}
            handOver={handOver}
            loading={loading}
            makeAction={makeAction}
            canCheck={canCheckWrapper}
            canCall={canCallWrapper}
            canRaise={canRaiseWrapper}
            getActualCallAmount={getActualCallAmountWrapper}
            betSliderValue={betSliderValue}
            setBetSliderValue={setBetSliderValue}
            setRaiseAmount={setRaiseAmount}
            minBet={minBet}
            maxBet={maxBet}
            getCallAmount={getCallAmountWrapper}
            betToSliderPosition={betToSliderPosition}
            sliderPositionToBet={sliderPositionToBet}
          />

          <DebugPanel 
            gameState={gameState}
            handOver={handOver}
            canCheck={canCheckWrapper}
            canCall={canCallWrapper}
            canRaise={canRaiseWrapper}
            processAITurn={processAITurn}
          />

          <HandOverPanel 
            handOver={handOver}
            showdown={showdown}
            winners={winners}
            newHand={newHand}
            newRound={newRound}
            loading={loading}
            gameState={gameState}
          />

          <HandHistory gameState={gameState} />

          {/* Cardback Selector Button - only show during active game */}
          <button 
            className="cardback-selector-btn"
            onClick={cycleCardback}
            title={`Current: ${selectedCardback}`}
          >
            CB
          </button>
        </>
      )}
    </div>
  );
};

export default GamePage;
