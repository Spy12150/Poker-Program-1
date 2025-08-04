import React, { useState, useEffect, useCallback, useMemo } from 'react';
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

// WebSocket hook
import { useSocket } from '../hooks/useSocket';

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
  const [selectedAIType, setSelectedAIType] = useState('bladework_v2');
  const [previousCommunityLength, setPreviousCommunityLength] = useState(0);
  const [newCardIndices, setNewCardIndices] = useState([]);
  const [selectedCardback, setSelectedCardback] = useState('Cardback17');

  // WebSocket connection
  const socket = useSocket(import.meta.env.VITE_API_URL || 'https://poker-program-1-production.up.railway.app');

  // Memoize cardbacks array to prevent recreation on every render
  const cardbacks = useMemo(() => [
    'Cardback17', 'Cardback18', 'Cardback3', 'Cardback4', 'Cardback5',
    'Cardback6', 'Cardback7', 'Cardback8', 'Cardback9', 'Cardback10',
    'Cardback11', 'Cardback12', 'Cardback13', 'Cardback14', 
    'Cardback16', 'Cardback2', 'Cardback1', 'Cardback19'
  ], []);

  const cycleCardback = useCallback(() => {
    const currentIndex = cardbacks.indexOf(selectedCardback);
    const nextIndex = (currentIndex + 1) % cardbacks.length;
    setSelectedCardback(cardbacks[nextIndex]);
  }, [selectedCardback, cardbacks]);

  const handleSliderRaise = useCallback(() => {
    if (betSliderValue < minBet) {
      setMessage(`Minimum bet is $${minBet}`);
      return;
    }
    if (betSliderValue > maxBet) {
      setMessage(`Maximum bet is $${maxBet}`);
      return;
    }
    makeAction('raise', betSliderValue);
  }, [betSliderValue, minBet, maxBet, makeAction]);

  // Memoize function wrappers to prevent recreation on every render
  const gameUtils = useMemo(() => ({
    getCallAmount: () => getCallAmount(gameState),
    getActualCallAmount: () => getActualCallAmount(gameState),
    canCheck: () => canCheck(gameState),
    canCall: () => canCall(gameState),
    canRaise: () => canRaise(gameState),
    getPlayerPosition: (playerIndex) => getPlayerPosition(gameState, playerIndex),
    hasPlayerChecked: (playerIndex) => hasPlayerChecked(gameState, playerIndex)
  }), [gameState]);

  // Create memoized wrapper functions using gameUtils
  const getCallAmountWrapper = useCallback(() => gameUtils.getCallAmount(), [gameUtils]);
  const getActualCallAmountWrapper = useCallback(() => gameUtils.getActualCallAmount(), [gameUtils]);
  const canCheckWrapper = useCallback(() => gameUtils.canCheck(), [gameUtils]);
  const canCallWrapper = useCallback(() => gameUtils.canCall(), [gameUtils]);
  const canRaiseWrapper = useCallback(() => gameUtils.canRaise(), [gameUtils]);
  const getPlayerPositionWrapper = useCallback((playerIndex) => gameUtils.getPlayerPosition(playerIndex), [gameUtils]);
  const hasPlayerCheckedWrapper = useCallback((playerIndex) => gameUtils.hasPlayerChecked(playerIndex), [gameUtils]);

  const updateBetLimits = useCallback((state) => {
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
  }, []);

  // WebSocket event handlers
  useEffect(() => {
    if (!socket.isConnected) return;

    // Handle game start
    socket.on('game_start', (data) => {
      console.log('Game started via WebSocket');
      setGameId(data.game_id);
      setGameState(data);
      setHandOver(false);
      setShowdown(false);
      setWinners([]);
      setMessage('Game started! Good luck!');
      updateBetLimits(data);
      setLoading(false);
    });

    // Handle player action results
    socket.on('action_result', (data) => {
      console.log('Action result received');
      if (data.game_state) {
        setGameState(data.game_state);
        updateBetLimits(data.game_state);
      }

      if (data.winners) {
        setWinners(data.winners);
        setHandOver(true);
        if (data.showdown) {
          setShowdown(true);
        }
      }

      if (data.message) {
        setMessage(data.message);
      }

      setLoading(false);
    });

    // Handle AI actions
    socket.on('ai_action', (data) => {
      console.log('AI action received');
      if (data.game_state) {
        setGameState(data.game_state);
        updateBetLimits(data.game_state);
      }

      if (data.message) {
        setMessage(data.message);
      } else {
        // If no specific message, show AI action feedback
        setMessage('AI made their move');
      }

      if (data.winners) {
        setWinners(data.winners);
        setHandOver(true);
        if (data.showdown) {
          setShowdown(true);
        }
      }
      
      // Clear loading state when AI action completes
      setLoading(false);
    });

    // Handle hand over
    socket.on('hand_over', (data) => {
      console.log('Hand over received');
      if (data.winners) {
        setWinners(data.winners);
        setHandOver(true);
        if (data.showdown) {
          setShowdown(true);
        }
      }
      if (data.message) {
        setMessage(data.message);
      }
    });

    // Handle new hand
    socket.on('new_hand', (data) => {
      console.log('New hand started via WebSocket');
      setGameState(data);
      setHandOver(false);
      setShowdown(false);
      setWinners([]);
      setMessage('New hand started!');
      updateBetLimits(data);
      setLoading(false);
    });

    // Handle new round
    socket.on('new_round', (data) => {
      console.log('New round started via WebSocket');
      setGameState(data);
      setHandOver(false);
      setShowdown(false);
      setWinners([]);
      setMessage('New round started! Stacks reset.');
      updateBetLimits(data);
      setLoading(false);
    });

    // Handle errors
    socket.on('error', (data) => {
      console.error('WebSocket error:', data.message);
      setMessage(`Error: ${data.message}`);
      setLoading(false);
    });

    // Handle server messages
    socket.on('message', (data) => {
      setMessage(data.message);
    });

    // Handle connection status changes
    if (socket.connectionError) {
      setMessage(`Connection error: ${socket.connectionError}`);
    }

    // Cleanup function
    return () => {
      socket.off('game_start');
      socket.off('action_result');
      socket.off('ai_action');
      socket.off('hand_over');
      socket.off('new_hand');
      socket.off('new_round');
      socket.off('error');
      socket.off('message');
    };
  }, [socket.isConnected, socket.connectionError]);

  // Card dealing animation effect
  useEffect(() => {
    if (!gameState || !gameState.community) return;

    const currentLength = gameState.community.length;
    
    if (currentLength > previousCommunityLength) {
      setDealingCards(true);
      
      // Calculate which cards are new
      const newIndices = [];
      for (let i = previousCommunityLength; i < currentLength; i++) {
        newIndices.push(i);
      }
      
      // Special case for flop: if we're going from 0 to 3 cards, animate all 3
      if (previousCommunityLength === 0 && currentLength === 3) {
        setNewCardIndices([0, 1, 2]);
      } else {
        setNewCardIndices(newIndices);
      }
      
      // Check if it's an all-in showdown with multiple cards dealt at once
      const cardsDifference = currentLength - previousCommunityLength;
      const animationDuration = cardsDifference > 1 ? 1500 : 1000; // Longer for multiple cards
      
      // Remove dealing animation after animation completes
      setTimeout(() => {
        setDealingCards(false);
        setNewCardIndices([]);
      }, animationDuration);
    }
    
    setPreviousCommunityLength(currentLength);
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
  }, [gameState, handOver, loading, makeAction, canCheckWrapper, canCallWrapper, canRaiseWrapper, handleSliderRaise]);

  // Game action functions using WebSocket - memoized for performance
  const startGame = useCallback((selectedAI = 'bladework_v2') => {
    if (!socket.isConnected) {
      setMessage('Not connected to server. Please refresh the page.');
      return;
    }

    setLoading(true);
    setSelectedAIType(selectedAI);
    setMessage('Starting game...');
    
    console.log('Starting game with AI:', selectedAI);
    socket.startGame(selectedAI);
  }, [socket.isConnected, socket.startGame]);

  const makeAction = useCallback((action, amount = 0) => {
    if (!gameId || handOver || loading || !socket.isConnected) return;
    
    setLoading(true);
    setMessage(`Making ${action}...`);
    
    console.log(`Making action: ${action}`, { gameId, action, amount });
    socket.makeAction(gameId, action, amount);
  }, [gameId, handOver, loading, socket.isConnected, socket.makeAction]);

  const newHand = useCallback(() => {
    if (!gameId || loading || !socket.isConnected) return;
    
    setLoading(true);
    setMessage('Starting new hand...');
    
    console.log('Starting new hand for game:', gameId);
    socket.startNewHand(gameId);
  }, [gameId, loading, socket.isConnected, socket.startNewHand]);

  const newRound = useCallback(() => {
    if (!gameId || loading || !socket.isConnected) return;
    
    setLoading(true);
    setMessage('Starting new round...');
    
    console.log('Starting new round for game:', gameId);
    socket.startNewRound(gameId);
  }, [gameId, loading, socket.isConnected, socket.startNewRound]);

  // Action helper functions - memoized to prevent unnecessary re-renders
  const handleFold = useCallback(() => makeAction('fold'), [makeAction]);
  const handleCheck = useCallback(() => makeAction('check'), [makeAction]);
  const handleCall = useCallback(() => makeAction('call'), [makeAction]);
  const handleRaise = useCallback(() => {
    const amount = parseInt(raiseAmount) || minBet;
    makeAction('raise', amount);
  }, [makeAction, raiseAmount, minBet]);

  // Main menu handler - resets all game state
  const handleMenuClick = useCallback(() => {
    // Reset all game state to return to start menu
    setGameState(null);
    setGameId(null);
    setMessage('');
    setWinners([]);
    setHandOver(false);
    setShowdown(false);
    setRaiseAmount('');
    setLoading(false);
    setBetSliderValue(0);
    setMinBet(0);
    setMaxBet(0);
    setDealingCards(false);
    setPreviousCommunityLength(0);
    setNewCardIndices([]);
  }, []);

  // Bet slider functions - memoized for performance
  const handleSliderChange = useCallback((e) => {
    const position = parseInt(e.target.value);
    setBetSliderValue(position);
    const betValue = sliderPositionToBet(position, minBet, maxBet);
    setRaiseAmount(betValue.toString());
  }, [minBet, maxBet]);

  const updateSliderFromAmount = useCallback((amount) => {
    const numAmount = parseInt(amount) || minBet;
    const clampedAmount = Math.max(minBet, Math.min(maxBet, numAmount));
    const position = betToSliderPosition(clampedAmount, minBet, maxBet);
    setBetSliderValue(position);
    setRaiseAmount(clampedAmount.toString());
  }, [minBet, maxBet]);

  const handleBetPreset = useCallback((preset) => {
    let amount;
    const pot = gameState?.pot || 0;
    const playerStack = gameState?.players[0]?.stack || 0;
    const playerCurrentBet = gameState?.players[0]?.current_bet || 0;
    const maxAllIn = playerStack + playerCurrentBet;

    switch (preset) {
      case '1/3':
        amount = Math.ceil(pot / 3);
        break;
      case '1/2':
        amount = Math.ceil(pot / 2);
        break;
      case 'pot':
        amount = pot;
        break;
      case 'all-in':
        amount = maxAllIn;
        break;
      case '2.5x':
        const currentBet = gameState?.current_bet || 0;
        amount = Math.ceil(currentBet * 2.5);
        break;
      case '3x':
        const currentBet3x = gameState?.current_bet || 0;
        amount = Math.ceil(currentBet3x * 3);
        break;
      default:
        amount = minBet;
    }

    amount = Math.max(minBet, Math.min(maxAllIn, amount));
    updateSliderFromAmount(amount);
  }, [gameState, minBet, updateSliderFromAmount]);

  // Connection status display - only show when there's an issue or connecting - memoized
  const connectionStatus = useCallback(() => {
    if (socket.connectionError) {
      return <div className="connection-status error">Connection Error</div>;
    } else if (!socket.isConnected) {
      return <div className="connection-status connecting">Connecting...</div>;
    }
    // Return null when connected successfully - no status indicator needed
    return null;
  }, [socket.connectionError, socket.isConnected]);

  // Memoize complex prop objects to prevent unnecessary re-renders
  const pokerTableProps = useMemo(() => ({
    gameState,
    showdown,
    selectedCardback,
    dealingCards,
    newCardIndices,
    handOver,
    evaluateHand,
    translateCard,
    getPlayerPosition: getPlayerPositionWrapper,
    hasPlayerChecked: hasPlayerCheckedWrapper,
    isBackground: !gameState // New prop to indicate background mode
  }), [gameState, showdown, selectedCardback, dealingCards, newCardIndices, handOver, getPlayerPositionWrapper, hasPlayerCheckedWrapper]);

  const actionPanelProps = useMemo(() => ({
    gameState,
    handOver,
    loading,
    makeAction,
    isCheckAllowed: canCheckWrapper,
    isCallAllowed: canCallWrapper,
    isRaiseAllowed: canRaiseWrapper,
    getCallAmount: getCallAmountWrapper,
    getActualCallAmount: getActualCallAmountWrapper,
    betSliderValue,
    setBetSliderValue,
    setRaiseAmount,
    minBet,
    maxBet,
    betToSliderPosition,
    sliderPositionToBet
  }), [gameState, handOver, loading, makeAction, canCheckWrapper, canCallWrapper, canRaiseWrapper, 
       getCallAmountWrapper, getActualCallAmountWrapper, betSliderValue, 
       minBet, maxBet]);

  if (!gameState) {
    return (
      <div className="game-container">
        <GameHeader />
        {connectionStatus()}
        <StartGameButton 
          gameState={gameState}
          startGame={startGame}
          loading={loading}
        />
        {message && <GameMessage message={message} />}
      </div>
    );
  }

  return (
    <div className="game-container">
      <GameHeader gameState={gameState} />
      {connectionStatus()}
      
      {/* Main Menu Button - only show when game is active */}
      {gameState && <button className="menu-button" onClick={handleMenuClick}>MAIN MENU</button>}
      
      {message && <GameMessage message={message} />}
      
      {/* Always show poker table - active game or background for start screen */}
      <PokerTable {...pokerTableProps} />
      
      {gameState && (
        <>
          <ActionPanel {...actionPanelProps} />
          
          <DebugPanel 
            gameState={gameState}
            handOver={handOver}
            isCheckAllowed={canCheckWrapper}
            isCallAllowed={canCallWrapper}
            isRaiseAllowed={canRaiseWrapper}
            processAITurn={() => {}} // Not available in WebSocket version
            selectedAIType={selectedAIType}
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
          
          {handOver && (
            <HandOverPanel
              handOver={handOver}
              showdown={showdown}
              winners={winners}
              newHand={newHand}
              newRound={newRound}
              loading={loading}
              gameState={gameState}
            />
          )}
        </>
      )}
    </div>
  );
};

export default React.memo(GamePage);
