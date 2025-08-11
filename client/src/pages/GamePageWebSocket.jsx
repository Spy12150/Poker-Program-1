import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
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
  
  // This is to protect card animation getting interrupted 
  const isAnimatingRef = useRef(false);

  // Local development connection
  const socket = useSocket(import.meta.env.VITE_API_URL || 'http://localhost:5001');

  // Memoize cardbacks array to prevent recreation on every render
  const cardbacks = useMemo(() => [
    'Cardback17', 'Cardback18', 'Cardback3', 'Cardback4', 'Cardback5',
    'Cardback6', 'Cardback7', 'Cardback8', 'Cardback9', 'Cardback10',
    'Cardback11', 'Cardback12', 'Cardback14', 
    'Cardback16', 'Cardback2', 'Cardback1', 'Cardback19'
  ], []);

  const cycleCardback = useCallback(() => {
    const currentIndex = cardbacks.indexOf(selectedCardback);
    const nextIndex = (currentIndex + 1) % cardbacks.length;
    setSelectedCardback(cardbacks[nextIndex]);
  }, [selectedCardback, cardbacks]);

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
      // first bet has to be at least bb for postflop
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

  // Reset animation state when game starts/resets
  useEffect(() => {
    if (!gameState) {
      setDealingCards(false);
      setNewCardIndices([]);
      setPreviousCommunityLength(0);
      window.lastCommunityHash = '';
      isAnimatingRef.current = false;
    }
  }, [gameState]);

  // WebSocket event handlers
  useEffect(() => {
    if (!socket.isConnected) return;

    // Handle game start
    socket.on('game_start', (data) => {

      
      // Clear any pending start game timeout
      if (window.startGameTimeoutId) {
        clearTimeout(window.startGameTimeoutId);
        window.startGameTimeoutId = null;
      }
      
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
      // Clear any pending action timeout
      if (window.actionTimeoutId) {
        clearTimeout(window.actionTimeoutId);
        window.actionTimeoutId = null;
      }
      
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

      
      // Clear any pending action timeout
      if (window.actionTimeoutId) {
        clearTimeout(window.actionTimeoutId);
        window.actionTimeoutId = null;
      }
      
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
      // Clear loading state if there's a persistent connection error
      setLoading(false);
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
  }, [socket.isConnected, socket.connectionError, updateBetLimits]);

  // Card dealing animation effect - improved to prevent double triggers
  useEffect(() => {
    if (!gameState || !gameState.community) {
      return;
    }

    const currentLength = gameState.community.length;
    
    // CRITICAL: Exit immediately if already animating (using ref for synchronous check)
    if (isAnimatingRef.current) {
      return;
    }
    
    // Create a unique identifier for this community state to prevent duplicates
    const communityHash = gameState.community.join(',');
    
    // Only animate if:
    // 1. Cards were actually added
    // 2. not currently dealing 
    // 3. This is a new community state 
    if (currentLength > previousCommunityLength && 
        currentLength > 0 &&
        window.lastCommunityHash !== communityHash) {
      
      // Store this community state to prevent re-animation
      window.lastCommunityHash = communityHash;
      
      // Set animation flag immediately (synchronous)
      isAnimatingRef.current = true;
      
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
      
      setDealingCards(true);
      
      // Match CSS animation duration exactly (0.8s = 800ms)
      const animationDuration = 800;
      
      // Remove dealing animation after animation completes
      setTimeout(() => {
        setDealingCards(false);
        setNewCardIndices([]);
        isAnimatingRef.current = false; // Clear animation flag
      }, animationDuration);
    }
    
    // Update previous length only after checking for animation
    setPreviousCommunityLength(currentLength);
  }, [gameState?.community?.length]);

  // Game action functions using WebSocket - memoized for performance
  const startGame = useCallback((selectedAI = 'bladework_v2') => {
    // Check for connection errors or if socket is not connected
    if (socket.connectionError) {
      setMessage('Connection error. Please refresh the page.');
      return;
    }

    if (!socket.isConnected) {
      setMessage('Not connected to server. Please wait and try again.');
      return;
    }

    setLoading(true);
    setSelectedAIType(selectedAI);
    setMessage('Starting game...');
    

    
    // Set a timeout to reset loading state if no response received
    const timeoutId = setTimeout(() => {

      setLoading(false);
      setMessage('Game start timed out. Please try again.');
    }, 10000); // 10 second timeout
    
    // Store timeout ID for cleanup
    window.startGameTimeoutId = timeoutId;
    
    socket.startGame(selectedAI);
  }, [socket.connectionError, socket.isConnected, socket.startGame]);

  const makeAction = useCallback((action, amount = 0) => {
    if (!gameId || handOver || loading) return;
    
    // Don't block actions for brief disconnections 
    if (socket.connectionError) {
      setMessage('Connection error. Please try again.');
      return;
    }
    
    setLoading(true);
    setMessage(`Making ${action}...`);
    
    // Safety timeout to prevent UI from getting stuck
    const timeoutId = setTimeout(() => {

      setLoading(false);
      setMessage('Action timed out. Please try again.');
    }, 15000); // 15 second timeout
    

    socket.makeAction(gameId, action, amount);
    
    // Store timeout ID for potential cleanup (though it will be cleared by response handlers)
    window.actionTimeoutId = timeoutId;
  }, [gameId, handOver, loading, socket.connectionError, socket.makeAction]);

  const newHand = useCallback(() => {
    if (!gameId || loading) return;
    
    if (socket.connectionError) {
      setMessage('Connection error. Please try again.');
      return;
    }
    
    setLoading(true);
    setMessage('Starting new hand...');
    

    socket.startNewHand(gameId);
  }, [gameId, loading, socket.connectionError, socket.startNewHand]);

  const newRound = useCallback(() => {
    if (!gameId || loading) return;
    
    if (socket.connectionError) {
      setMessage('Connection error. Please try again.');
      return;
    }
    
    setLoading(true);
    setMessage('Starting new round...');
    

    socket.startNewRound(gameId);
  }, [gameId, loading, socket.connectionError, socket.startNewRound]);

  const handleFold = useCallback(() => makeAction('fold'), [makeAction]);
  const handleCheck = useCallback(() => makeAction('check'), [makeAction]);
  const handleCall = useCallback(() => makeAction('call'), [makeAction]);
  const handleRaise = useCallback(() => {
    const amount = parseInt(raiseAmount) || minBet;
    makeAction('raise', amount);
  }, [makeAction, raiseAmount, minBet]);

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

  // Reset game states for main menu
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

  // Bet slider functions 
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

  // Connection status display 
  const connectionStatus = useCallback(() => {
    if (socket.connectionError) {
      // Show different messages based on connection state
      if (socket.connectionError.includes('Reconnecting')) {
        return <div className="connection-status reconnecting">🔄 Reconnecting to server...</div>;
      } else if (socket.connectionError.includes('Reconnection failed')) {
        return <div className="connection-status error">⚠️ Connection issues - Retrying...</div>;
      } else {
        return <div className="connection-status error">❌ Connection Error - Please refresh if issues persist</div>;
      }
    }
    
    // Show a subtle indicator if we're connected after having connection issues
    if (socket.isConnected && window.hadConnectionIssues) {
      setTimeout(() => {
        window.hadConnectionIssues = false;
      }, 3000);
      return <div className="connection-status success">✅ Connected</div>;
    }
    
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
      
      {/* Main Menu Button, only show when game is active */}
      {gameState && (
        <button
          className="menu-button"
          onClick={handleMenuClick}
          style={{ position: 'fixed', top: 20, left: 280 }}
        >
          MAIN MENU
        </button>
      )}
      
      {message && <GameMessage message={message} />}
      
      {/* Always show poker table, active game or background for start screen */}
      <PokerTable {...pokerTableProps} />
      
      {gameState && (
        <>
          <ActionPanel {...actionPanelProps} />
          
          <div className="debug-dock">
            <DebugPanel 
              gameState={gameState}
              handOver={handOver}
              isCheckAllowed={canCheckWrapper}
              isCallAllowed={canCallWrapper}
              isRaiseAllowed={canRaiseWrapper}
              processAITurn={() => {}} // Not available in WebSocket version
              selectedAIType={selectedAIType}
            />

            {/* Cardback Selector */}
            <button 
              className="cardback-selector-btn has-tooltip"
              onClick={cycleCardback}
              title={`Current: ${selectedCardback}`}
              data-tooltip="Switch to a different cardback"
              aria-label="Switch cardback"
            >
              CB
            </button>

            {/* GitHub */}
            <a
              href="https://github.com/Spy12150/riposte-poker"
              target="_blank"
              rel="noopener noreferrer"
              className="round-link-btn has-tooltip"
              data-tooltip="Check out the github repo"
              aria-label="GitHub Repository"
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
              </svg>
            </a>

            {/* IvoryLov */}
            <a
              href="https://www.ivorylov.com/projects"
              target="_blank"
              rel="noopener noreferrer"
              className="round-link-btn has-tooltip ivorylov-link"
              data-tooltip="Check out my other projects"
              aria-label="IvoryLov Projects"
            >
              <img src="/IVLlogo4.svg" alt="IvoryLov" style={{ width: 24, height: 24 }} />
            </a>
          </div>

          <HandHistory gameState={gameState} />
          
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

export default GamePage;
