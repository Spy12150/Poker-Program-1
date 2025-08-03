import { useEffect, useRef, useState } from 'react';
import { io } from 'socket.io-client';

/**
 * Custom hook for managing WebSocket connection and poker game events
 */
export const useSocket = (serverUrl) => {
  const socketRef = useRef(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState(null);

  // Event listeners storage
  const eventListenersRef = useRef({});

  useEffect(() => {
    // Initialize socket connection
    socketRef.current = io(serverUrl, {
      transports: ['websocket', 'polling'],
      upgrade: true,
      forceNew: true
    });

    const socket = socketRef.current;

    // Connection event handlers
    socket.on('connect', () => {
      console.log('✅ Connected to poker server via WebSocket');
      setIsConnected(true);
      setConnectionError(null);
    });

    socket.on('disconnect', (reason) => {
      console.log('❌ Disconnected from poker server:', reason);
      setIsConnected(false);
    });

    socket.on('connect_error', (error) => {
      console.error('❌ Connection error:', error);
      setConnectionError(error.message);
      setIsConnected(false);
    });

    // Generic error handler
    socket.on('error', (data) => {
      console.error('❌ Server error:', data.message);
      // You can emit a custom event or update state here
      if (eventListenersRef.current.error) {
        eventListenersRef.current.error(data);
      }
    });

    // Cleanup on unmount
    return () => {
      if (socket) {
        socket.disconnect();
      }
    };
  }, [serverUrl]);

  // Function to emit events to server
  const emit = (eventName, data) => {
    if (socketRef.current && isConnected) {
      console.log(`📤 Emitting ${eventName}:`, data);
      socketRef.current.emit(eventName, data);
    } else {
      console.warn('⚠️ Socket not connected. Cannot emit:', eventName);
    }
  };

  // Function to listen for events from server
  const on = (eventName, callback) => {
    if (socketRef.current) {
      // Store the callback for cleanup
      eventListenersRef.current[eventName] = callback;
      
      console.log(`👂 Listening for ${eventName}`);
      socketRef.current.on(eventName, (data) => {
        console.log(`📥 Received ${eventName}:`, data);
        callback(data);
      });
    }
  };

  // Function to stop listening for events
  const off = (eventName) => {
    if (socketRef.current) {
      socketRef.current.off(eventName);
      delete eventListenersRef.current[eventName];
      console.log(`🔇 Stopped listening for ${eventName}`);
    }
  };

  // Poker-specific helper functions
  const joinGame = (gameId) => {
    emit('join_game', { game_id: gameId });
  };

  const startGame = (aiType = 'bladework_v2') => {
    emit('start_game', { ai_type: aiType });
  };

  const makeAction = (gameId, action, amount = 0) => {
    emit('player_action', { 
      game_id: gameId, 
      action: action, 
      amount: amount 
    });
  };

  const startNewHand = (gameId) => {
    emit('new_hand', { game_id: gameId });
  };

  const startNewRound = (gameId) => {
    emit('new_round', { game_id: gameId });
  };

  return {
    // Connection status
    isConnected,
    connectionError,
    
    // Raw socket functions
    emit,
    on,
    off,
    
    // Poker-specific functions
    joinGame,
    startGame,
    makeAction,
    startNewHand,
    startNewRound,
    
    // Direct socket reference (use sparingly)
    socket: socketRef.current
  };
};
