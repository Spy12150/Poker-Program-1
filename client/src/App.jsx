import React from 'react';
import GamePage from './pages/GamePage';
import { useImagePreloader } from './hooks/useImagePreloader';
// import GamePageWebSocket from './pages/GamePageWebSocket';  // Available for production/hosting

function App() {
  // Preload card images for better performance
  useImagePreloader();
  
  return <GamePage />;
  // For WebSocket version (production): return <GamePageWebSocket />;
}

export default App;
